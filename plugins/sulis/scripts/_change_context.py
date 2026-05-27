"""Pre-spawn recon writer for the change-as-primitive flow (WP-005).

Gathers a lightweight, pure-read snapshot of a change's identity + git
state and renders it to ~/.sulis/changes/{change_id}/CONTEXT.md. The
spawned Sulis session reads this brief at session start (via the WP-006
pre-prompt reference and the WP-007 agent body) to greet the founder in
change-context mode.

See plugins/sulis/docs/change-as-primitive-design.md § "Session binding"
(step 2 — recon runs synchronously before the terminal is spawned).

Kept separate from _wpxlib.py (3679 LOC and growing) — recon is a
logically distinct concern (see ADR-002 note about a future lib/ split).
Stdlib only; git access via _wpxlib._run (subprocess wrapper).
"""

from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _change_state import change_dir  # noqa: E402
from _wpxlib import _run  # noqa: E402

logger = logging.getLogger("sulis.change_context")


# Opinionated next-step hint per primitive. Covers all 22 change primitives
# (change-primitives.md) plus the 3 Conventional Commits fallbacks. Unknown
# primitives fall back to the defensive default — never silent, never wrong.
_PRIMITIVE_NEXT_STEP_HINTS: dict[str, str] = {
    # EXPAND
    "create": "start with `/sulis:specify` to capture what you want to build",
    "extend": "start with `/sulis:analyse-codebase` to locate the seam you're extending",
    "reuse": "start with `/sulis:analyse-codebase` to find the component to reuse",
    "compose": "start with `/sulis:draft-architecture` to design the composition",
    "generate": "start with `/sulis:specify` to capture what's being generated",
    # REORGANISE
    "move": "start with `/sulis:analyse-codebase` to scope what moves where",
    "refactor": "start with `/sulis:analyse-codebase` to scope the structural change",
    "inline": "start with `/sulis:analyse-codebase` to find the indirection to inline",
    "merge": "start with `/sulis:analyse-codebase` to locate the units to merge",
    "decompose": "start with `/sulis:analyse-codebase` to find the seams to split on",
    "abstract": "start with `/sulis:analyse-codebase` to find the duplication to abstract",
    # SUBSTITUTE
    "replace": "start with `/sulis:analyse-codebase` to map the surface being replaced",
    "strangle": "start with `/sulis:draft-architecture` to plan the strangler-fig boundary",
    "wrap": "start with `/sulis:analyse-codebase` to map the subject you're wrapping",
    # CONTRACT
    "deprecate": "start with `/sulis:analyse-codebase` to find every caller of the surface",
    "delete": "start with `/sulis:analyse-codebase` to confirm the surface is dead",
    # REINFORCE
    "test": "start with `/sulis:check-tests` to see current coverage",
    "instrument": "start with `/sulis:analyse-codebase` to find where to add observability",
    "secure": "start with `/sulis:check-security` to find the exposure",
    "harden": "start with `/sulis:harden-codebase` to scope the hardening",
    "gate": "start with `/sulis:analyse-codebase` to find where the gate belongs",
    "document": "start with `/sulis:analyse-codebase` to see what needs documenting",
    # Conventional Commits fallbacks
    "feat": "start with `/sulis:specify` to capture the feature",
    "fix": "start with `/sulis:analyse-codebase` to locate the bug",
    "chore": "start with `/sulis:status` to see where this fits",
}

_DEFAULT_HINT = "start with `/sulis:status`"


# ─── Git state helpers (private, pure-read) ────────────────────────────────


def _head_sha(repo_root: Path) -> str:
    """Return the short HEAD SHA, or '(unknown)' if not resolvable."""
    rc, out, _ = _run(["git", "rev-parse", "--short", "HEAD"], cwd=repo_root, timeout=10)
    return out.strip() if rc == 0 and out.strip() else "(unknown)"


def _base_sha(repo_root: Path, base_ref: str = "dev") -> str:
    """Return the short SHA of the base ref, or '(unknown)'."""
    rc, out, _ = _run(["git", "rev-parse", "--short", base_ref], cwd=repo_root, timeout=10)
    return out.strip() if rc == 0 and out.strip() else "(unknown)"


def _ahead_behind(repo_root: Path, base_ref: str = "dev") -> tuple[int, int]:
    """Return (ahead, behind) commit counts of HEAD relative to base_ref."""
    rc, out, _ = _run(
        ["git", "rev-list", "--left-right", "--count", f"{base_ref}...HEAD"],
        cwd=repo_root, timeout=10,
    )
    if rc != 0 or not out.strip():
        return (0, 0)
    parts = out.split()
    if len(parts) != 2:
        return (0, 0)
    try:
        behind, ahead = int(parts[0]), int(parts[1])
    except ValueError:
        return (0, 0)
    return (ahead, behind)


# ─── Intent grounding helpers (#26) ────────────────────────────────────────
#
# The recon stub was previously identity + git-state only — the spawned Sulis
# greeted the founder blind on what the change is FOR. These helpers pull the
# founder's intent text, any linked GitHub issue body, and a small set of
# code-area file pointers into CONTEXT.md so the spawn starts grounded.
# All best-effort: any failure (no `gh`, no network, no matches) silently
# omits the section rather than failing the recon write.

# Match `#NN` only as a standalone token — not inside an alphanumeric word
# (so `abc#123` and `#notanumber` don't match). The lookbehind/lookahead are
# intentionally word-boundary-ish.
_ISSUE_REF_RE = re.compile(r"(?:^|[^A-Za-z0-9_])#(\d+)\b")

# Backtick-quoted code tokens: `cmd_nuke`, `_change_state.py`, `gh issue`, …
_CODE_TOKEN_RE = re.compile(r"`([^`\n]+)`")

# Tokens shorter than this are dropped from code-area scanning — single letters
# and 2-char abbreviations produce far too many false matches.
_CODE_TOKEN_MIN_LEN = 3


def _extract_issue_refs(text: str) -> list[int]:
    """Pull every `#NN` integer reference from ``text``. Deduped; preserves
    first-seen order. Pure; no I/O."""
    out: list[int] = []
    seen: set[int] = set()
    for match in _ISSUE_REF_RE.finditer(text or ""):
        n = int(match.group(1))
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def _extract_code_tokens(text: str) -> list[str]:
    """Pull every backtick-quoted token of length >= 3 from ``text``. Deduped;
    preserves first-seen order. Pure; no I/O."""
    out: list[str] = []
    seen: set[str] = set()
    for match in _CODE_TOKEN_RE.finditer(text or ""):
        tok = match.group(1).strip()
        if len(tok) < _CODE_TOKEN_MIN_LEN:
            continue
        if tok in seen:
            continue
        seen.add(tok)
        out.append(tok)
    return out


def _resolve_linked_issues(intent: str, repo_root: Path) -> list[dict]:
    """For every `#NN` in ``intent``, shell out `gh issue view N --json …`
    and return the parsed results. Empty list on any failure (best-effort —
    no `gh`, no auth, no remote, network error, issue not found, malformed
    JSON). Capped at 5 issues to keep CONTEXT.md scannable."""
    refs = _extract_issue_refs(intent)[:5]
    if not refs:
        return []
    out: list[dict] = []
    for n in refs:
        rc, stdout, stderr = _run(
            ["gh", "issue", "view", str(n),
             "--json", "number,title,labels,body,url,state"],
            cwd=repo_root, timeout=15,
        )
        if rc != 0:
            logger.debug("gh issue view %s failed: %s", n, stderr.strip())
            continue
        try:
            data = json.loads(stdout)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.debug("gh issue %s returned non-JSON: %s", n, exc)
            continue
        # Normalise labels: gh returns [{"name": "...", ...}, …]
        raw_labels = data.get("labels") or []
        if raw_labels and isinstance(raw_labels[0], dict):
            data["labels"] = [str(lbl.get("name", "")) for lbl in raw_labels]
        out.append(data)
    return out


def _locate_code_areas(intent: str, repo_root: Path) -> list[str]:
    """For each backtick-quoted token of length >= 3 in ``intent``, run
    `git grep -l -- <token>` and collect up to 5 unique matching files.
    Empty list on any failure. Best-effort; ordered by first-seen token."""
    tokens = _extract_code_tokens(intent)
    if not tokens:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for tok in tokens:
        rc, stdout, _ = _run(
            # `-l` lists files only; `-F` treats the pattern as a fixed string
            # so `.` etc. are not regex metacharacters. `--` separates the
            # pattern from any flag-like values.
            ["git", "grep", "-l", "-F", "--", tok],
            cwd=repo_root, timeout=10,
        )
        if rc != 0:
            continue
        for path in stdout.splitlines():
            path = path.strip()
            if not path or path in seen:
                continue
            seen.add(path)
            out.append(path)
            if len(out) >= 5:
                return out
    return out


# ─── Rendering ─────────────────────────────────────────────────────────────


def _render_context_md(
    change_id: str,
    metadata: dict,
    git_state: dict,
    *,
    intent: str = "",
    linked_issues: list[dict] | None = None,
    code_areas: list[str] | None = None,
) -> str:
    """Render the CONTEXT.md markdown body (human-readable, cat-able).

    Section order is fixed and must not change (the spawned Sulis treats the
    last section as the actionable hint):
      1. Change identity
      2. Git state at spawn
      3. Intent              (#26 — present iff metadata has intent)
      4. Linked issue        (#26 — present iff `#NN` resolved via gh)
      5. Code-area pointers  (#26 — present iff backtick tokens matched files)
      6. Suggested next step (always last)
    """
    primitive = metadata.get("primitive", "")
    hint = _PRIMITIVE_NEXT_STEP_HINTS.get(primitive, _DEFAULT_HINT)
    linked_issues = linked_issues or []
    code_areas = code_areas or []

    parts = [
        f"# Change context — {metadata.get('handle', change_id)}",
        "",
        "> Pre-spawn recon written by sulis-change. Pure-read snapshot; "
        "safe to `cat` for debugging.",
        "",
        "## Change identity",
        "",
        f"- **change_id:** `{change_id}`",
        f"- **handle:** {metadata.get('handle', '(none)')}",
        f"- **slug:** {metadata.get('slug', '(none)')}",
        f"- **primitive:** {primitive or '(none)'}",
        f"- **branch:** `{metadata.get('branch', '(none)')}`",
        "",
        "## Git state at spawn",
        "",
        f"- **HEAD:** `{git_state['head_sha']}`",
        f"- **base ({git_state['base_ref']}):** `{git_state['base_sha']}`",
        f"- **ahead of {git_state['base_ref']}:** {git_state['ahead']} commit(s)",
        f"- **behind {git_state['base_ref']}:** {git_state['behind']} commit(s)",
        "",
    ]

    # 3. Intent (omitted if empty — spec)
    if intent.strip():
        parts += ["## Intent", "", intent.strip(), ""]

    # 4. Linked issue(s) — omitted if zero
    if linked_issues:
        parts += ["## Linked issue", ""]
        for issue in linked_issues:
            number = issue.get("number", "?")
            title = str(issue.get("title", "")).strip() or "(no title)"
            url = str(issue.get("url", "")).strip()
            state = str(issue.get("state", "")).strip().upper() or "OPEN"
            labels = ", ".join(issue.get("labels") or []) or "(no labels)"
            parts += [
                f"### #{number} — {title}",
                "",
                f"- **state:** {state}",
                f"- **labels:** {labels}",
            ]
            if url:
                parts.append(f"- **url:** {url}")
            body = str(issue.get("body", "")).strip()
            if body:
                parts += ["", body]
            parts.append("")

    # 5. Code-area pointers — omitted if zero
    if code_areas:
        parts += [
            "## Code-area pointers",
            "",
            "Files matching tokens from the intent (`git grep -l`):",
            "",
        ]
        parts += [f"- `{path}`" for path in code_areas]
        parts.append("")

    # 6. Suggested next step — always last
    parts += ["## Suggested next step", "", hint, ""]

    return "\n".join(parts)


def write_change_context(
    change_id: str,
    metadata: dict,
    repo_root: Path,
) -> Path | None:
    """Gather pre-spawn context and write ~/.sulis/changes/{change_id}/CONTEXT.md.

    Sections: change identity, git state at spawn, suggested next step
    (looked up from _PRIMITIVE_NEXT_STEP_HINTS).

    Pure-read: never modifies the repo. Subprocess calls are git-rev-parse
    and git-rev-list only. Returns the absolute path to the written file.

    Recon is best-effort: if the change dir / CONTEXT.md cannot be written
    (permission denied, read-only FS, disk full), this returns ``None`` and
    logs a warning rather than raising — a recon-write failure must not crash
    the caller's ``sulis-change start`` spawn path.
    """
    base_ref = metadata.get("base_branch") or "dev"
    git_state = {
        "head_sha": _head_sha(repo_root),
        "base_sha": _base_sha(repo_root, base_ref),
        "base_ref": base_ref,
    }
    ahead, behind = _ahead_behind(repo_root, base_ref)
    git_state["ahead"] = ahead
    git_state["behind"] = behind

    # #26 — enrich the recon with the founder's intent text, any linked GitHub
    # issue body, and a small file-pointer scan. All three are best-effort:
    # a failed resolution (no `gh`, no remote, no grep matches) silently omits
    # the section rather than blocking the recon write.
    intent = str(metadata.get("intent") or "")
    linked_issues = _resolve_linked_issues(intent, repo_root) if intent else []
    code_areas = _locate_code_areas(intent, repo_root) if intent else []

    body = _render_context_md(
        change_id, metadata, git_state,
        intent=intent,
        linked_issues=linked_issues,
        code_areas=code_areas,
    )

    dest_dir = change_dir(change_id)
    context_path = dest_dir / "CONTEXT.md"
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        context_path.write_text(body, encoding="utf-8")
    except OSError as exc:
        logger.warning(
            "could not write recon CONTEXT.md at %s: %s (recon is best-effort; "
            "spawn proceeds without it)",
            context_path, exc,
        )
        return None
    return context_path.resolve()
