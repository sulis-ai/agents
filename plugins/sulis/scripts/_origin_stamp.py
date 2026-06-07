"""WP-P12 — origin-stamp writer (ADR-013).

Stamps change-origin at commit time as a git commit **trailer** on the commit
the write path already makes — the same family as `Co-Authored-By:` /
`Signed-off-by:` (RFC-style trailers used by Git itself, GitHub, the kernel):

    Sulis-Origin: autonomous; run=<lifecyclerun-ulid>; confidence=<0..1>
    Sulis-Origin: assisted; conversation=<id>; turn=<n>

This is the write side that turns *inferred* origin (P09) into *recorded* fact
(P13). It lives OUTSIDE `apps/cockpit/` — the cockpit is provably read-only
(ADR-003); only the executor's and the chat-relay's existing commit step stamp
(ADR-013). The cockpit only ever READS the stamp (`RecordedOriginAttribution`).

Invariants (ADR-013):
  - Append-only metadata on a commit already being made — no NEW commit, no
    new process beyond the trailer rewrite, no network, nothing published.
  - A stamp **failure is non-fatal**: the commit stays intact, and origin
    falls back to inferred (graceful degradation). Where the trailer can't be
    written, a **sidecar** `.sulis/origin/<sha>.json` is the fallback; if that
    fails too, the outcome is `skipped` and the commit is left untouched.
  - One structured log line per stamp `{sha, origin, ref, outcome}` — NEVER the
    commit message text (TDD §3.4: ulid / id / confidence only, no PII).

The recommended entry point at commit time is the `prepare-commit-msg` git hook
(`hooks/prepare-commit-msg`), which reads the `SULIS_ORIGIN` env and appends the
trailer to the in-flight message BEFORE the commit object is written — the
cleanest, non-fatal interception for both write paths. `stamp_origin` is the
amend-in-place fallback for callers that commit first and stamp after.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional, Union

# The trailer key — the one token RecordedOriginAttribution greps for (CF-11).
TRAILER_KEY = "Sulis-Origin"

OriginDict = dict[str, Any]


# ─── origin constructors (the two write paths) ────────────────────────────


def autonomous_origin(*, run: str, confidence: Optional[float]) -> OriginDict:
    """Executor (autonomous) origin: a `lifecyclerun` ulid + optional confidence."""
    origin: OriginDict = {"kind": "autonomous", "run": run}
    if confidence is not None:
        origin["confidence"] = confidence
    return origin


def assisted_origin(*, conversation: str, turn: int) -> OriginDict:
    """Chat-relay (assisted) origin: a conversation id + 1-based turn index."""
    return {"kind": "assisted", "conversation": conversation, "turn": turn}


# ─── trailer formatting + env parsing (shape pinned to CF-11) ─────────────


def _has_control_char(value: str) -> bool:
    """True if `value` carries any control character (newline, carriage return,
    tab, NUL, etc.). A trailer is a single line; a control char in a field is
    either malformed input or a trailer-injection attempt (a smuggled `\\n` +
    `Forged-Trailer:` line). Both are rejected at the boundary."""
    return any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in value)


def _fmt_number(value: float) -> str:
    # 0.9 not 0.900000001; an int stays an int. Mirrors the reader's tolerant
    # parseFloat, but emit the tidiest form.
    if isinstance(value, bool):  # bool is a subclass of int — guard it.
        raise TypeError("confidence must be numeric, not bool")
    if isinstance(value, int) or float(value).is_integer():
        return str(int(value))
    return repr(round(float(value), 6)).rstrip("0").rstrip(".")


def format_trailer(origin: OriginDict) -> str:
    """Render an origin dict as the single `Sulis-Origin: …` trailer line.

    A trailer is ONE line. Any string field carrying a control character
    (notably a newline) would forge a second trailer line, so it is refused
    here as a last line of defence (the env-parse boundary rejects it first).
    """
    kind = origin.get("kind")
    for field in ("run", "conversation"):
        v = origin.get(field)
        if isinstance(v, str) and _has_control_char(v):
            raise ValueError(
                f"origin field {field!r} contains a control character; "
                "refusing to emit a forgeable trailer"
            )
    if kind == "autonomous":
        run = origin["run"]
        parts = [f"autonomous; run={run}"]
        if origin.get("confidence") is not None:
            parts.append(f"confidence={_fmt_number(origin['confidence'])}")
        return f"{TRAILER_KEY}: " + "; ".join(parts)
    if kind == "assisted":
        return (
            f"{TRAILER_KEY}: assisted; "
            f"conversation={origin['conversation']}; turn={int(origin['turn'])}"
        )
    raise ValueError(f"unknown origin kind: {kind!r}")


def parse_origin_env(value: Optional[str]) -> Optional[OriginDict]:
    """Parse a `SULIS_ORIGIN` env value (the trailer body, sans the key) into an
    origin dict, or None if absent / unparseable. The hook calls this.

    Accepts both the bare body (`autonomous; run=…`) and a full trailer line
    (`Sulis-Origin: autonomous; run=…`) so the env can carry either form.
    """
    if not value:
        return None
    # A trailer is a SINGLE line. A control character anywhere in the value
    # (an embedded `\n` + `Forged-Trailer:`, a `\r`, etc.) is either malformed
    # or a trailer-injection attempt — treat the whole value as malformed and
    # return None (the graceful "unstamped" path), so no forged second trailer
    # line can ever be smuggled through.
    if _has_control_char(value):
        return None
    body = value.strip()
    if body.lower().startswith(f"{TRAILER_KEY.lower()}:"):
        body = body.split(":", 1)[1].strip()
    if not body:
        return None

    kind = ""
    fields: dict[str, str] = {}
    for seg in body.split(";"):
        seg = seg.strip()
        if not seg:
            continue
        if "=" not in seg:
            if not kind:
                kind = seg
            continue
        key, val = seg.split("=", 1)
        fields[key.strip()] = val.strip()

    if kind == "autonomous":
        run = fields.get("run", "")
        if not run:
            return None
        origin: OriginDict = {"kind": "autonomous", "run": run}
        conf = fields.get("confidence")
        if conf is not None:
            try:
                origin["confidence"] = float(conf)
            except ValueError:
                pass
        return origin
    if kind == "assisted":
        conversation = fields.get("conversation", "")
        if not conversation:
            return None
        try:
            turn = int(fields.get("turn", ""))
        except ValueError:
            turn = 0
        return {"kind": "assisted", "conversation": conversation, "turn": turn}
    return None


def append_trailer_to_message(message: str, origin: OriginDict) -> str:
    """Return `message` with the `Sulis-Origin:` trailer appended to the trailer
    block, idempotently (never a second copy). Used by the `prepare-commit-msg`
    hook (on the raw message file) and by `stamp_origin` (on an existing commit).
    """
    trailer = format_trailer(origin)
    # Already stamped → leave it (idempotent; a rebase/amend re-run is harmless).
    for line in message.splitlines():
        if line.strip().lower().startswith(f"{TRAILER_KEY.lower()}:"):
            return message

    body = message.rstrip("\n")
    # A trailer block is separated from the body by a blank line. If the message
    # already ends in trailers (e.g. Co-Authored-By:), append within that block;
    # otherwise open a new trailer block with a blank line.
    lines = body.splitlines()
    last_nonblank = next((l for l in reversed(lines) if l.strip()), "")
    looks_like_trailer = ":" in last_nonblank and " " not in last_nonblank.split(":", 1)[0]
    sep = "\n" if looks_like_trailer else "\n\n"
    return f"{body}{sep}{trailer}\n"


# ─── sidecar fallback ─────────────────────────────────────────────────────


def write_sidecar(repo: Union[str, Path], sha: str, origin: OriginDict) -> Path:
    """Write `.sulis/origin/<sha>.json` — the fallback where a trailer can't be
    written (ADR-013). Returns the path. Raises on I/O error (the caller
    swallows it to keep the stamp non-fatal)."""
    out_dir = Path(repo) / ".sulis" / "origin"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{sha}.json"
    path.write_text(json.dumps(origin, separators=(",", ":")) + "\n")
    return path


# ─── the amend-in-place writer ────────────────────────────────────────────


def _git(repo: Union[str, Path], *args: str, timeout: int = 30) -> str:
    out = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True, capture_output=True, text=True, timeout=timeout,
    )
    return out.stdout


def _rewrite_commit_message(repo: Union[str, Path], message: str) -> None:
    """Amend HEAD's message in place (no tree change). Isolated so the
    stamp-failure-is-non-fatal test can force it to raise."""
    subprocess.run(
        ["git", "-C", str(repo), "commit", "--amend", "--only", "--no-edit",
         "-m", message],
        check=True, capture_output=True, text=True, timeout=30,
    )


def _log(record: dict[str, Any]) -> None:
    """One structured log line per stamp — sha/origin/ref/outcome only, NEVER
    the commit message text (TDD §3.4)."""
    sys.stderr.write(json.dumps(record, separators=(",", ":")) + "\n")


def stamp_origin(
    repo: Union[str, Path],
    origin: OriginDict,
    *,
    ref: str = "HEAD",
) -> dict[str, Any]:
    """Stamp `origin` onto the commit at `ref` (default HEAD) by amending its
    message to carry the `Sulis-Origin:` trailer. The amend-in-place path used
    when a path commits FIRST and stamps AFTER (the hook is the commit-time
    path).

    NON-FATAL: never raises. On a trailer-write failure it falls back to a
    `.sulis/origin/<sha>.json` sidecar; if that fails too, the outcome is
    `skipped` and the commit is left intact (origin falls back to inferred).

    Returns the structured log record `{sha, origin: kind, ref, outcome}`.
    """
    repo = Path(repo)
    sha = ""
    try:
        sha = _git(repo, "rev-parse", ref).strip()
    except Exception:
        # Can't even identify the commit → nothing to stamp; skip silently.
        record = {"sha": "", "origin": origin.get("kind"), "ref": ref,
                  "outcome": "skipped"}
        _log(record)
        return record

    # 1. Preferred: the commit trailer (travels with the commit, greppable).
    try:
        message = _git(repo, "log", "-1", "--format=%B", sha).rstrip("\n")
        stamped = append_trailer_to_message(message, origin)
        if stamped.rstrip("\n") != message.rstrip("\n"):
            _rewrite_commit_message(repo, stamped)
            new_sha = _git(repo, "rev-parse", "HEAD").strip()
        else:
            new_sha = sha  # already stamped (idempotent)
        record = {"sha": new_sha, "origin": origin.get("kind"), "ref": ref,
                  "outcome": "stamped"}
        _log(record)
        return record
    except Exception:
        pass  # fall through to the sidecar — stamping is best-effort.

    # 2. Fallback: the sidecar. Keyed by the (unchanged) commit sha.
    try:
        write_sidecar(repo, sha, origin)
        record = {"sha": sha, "origin": origin.get("kind"), "ref": ref,
                  "outcome": "sidecar"}
        _log(record)
        return record
    except Exception:
        pass

    # 3. Total failure is still non-fatal — the commit is the source of truth.
    record = {"sha": sha, "origin": origin.get("kind"), "ref": ref,
              "outcome": "skipped"}
    _log(record)
    return record
