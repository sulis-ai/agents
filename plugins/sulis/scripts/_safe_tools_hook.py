"""PreToolUse hook — block the unsafe path (locus ii, governance; ADR-003).

The governance layer of the embedded safe-tools armour. On every ``Write`` /
``Edit`` / ``Bash`` tool call, this hook reads the PreToolUse stdin JSON and
decides whether to **deny** (hard-block) or **defer** (stay silent — let the
normal permission flow + the resolver-backed MCP path proceed).

Decision channel (ADR-003, grounded in the verified Claude Code hooks docs):

  * **deny** → print
    ``{"hookSpecificOutput":{"hookEventName":"PreToolUse",
       "permissionDecision":"deny","permissionDecisionReason":"…"}}``
    on stdout and exit 0. A blocking PreToolUse decision takes precedence over
    *allow* rules (deny/ask rules still apply regardless).
  * **defer** → print NOTHING and exit 0. We deliberately do NOT emit
    ``permissionDecision:"allow"`` for the safe CLI family: emitting allow would
    (a) not override a managed *deny* rule anyway and (b) misrepresent the hook
    as the grant authority. The hook's job is to block the unsafe path, not to
    grant the safe one.
  * **fail-closed** → any unparseable stdin, missing change scope, or internal
    error → exit 2 with a reason on stderr (a hook crash BLOCKS the call rather
    than silently allowing it).

Single source of truth: the path-scope check delegates to the WP-002 resolver
(``_file_scope.within_allowed_scope`` / ``resolve_allowed_roots``). This module
re-implements **zero** scope logic — the #130 canonical-path / cross-change
invariant lives in exactly one place (SC-E5 / ADR-004).

Each rule below is annotated with its **enforcement-locus** and **threat-scope**
(feeds the SC-E6 honesty test in WP-005):

  * Write/Edit + Bash-redirect path scope — locus ii (harness hook),
    accidental-closed-now for the tool surface; the *adversarial* subprocess
    case (an in-process ``open(...,'w')``) is locus iii (OS sandbox, WP-004 /
    SC-E7), explicitly NOT covered here.
  * raw ``curl``/``wget`` deny — locus ii, accidental-closed-now; deliberate
    redundancy with the permission deny-rule (belt) — neither sufficient alone.
  * safe CLI family defer — locus ii; identity-only, not a grant.
"""

from __future__ import annotations

import json
import re
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _file_scope import AllowedRoots, resolve_allowed_roots, within_allowed_scope  # noqa: E402

# ─── decision vocabulary ──────────────────────────────────────────────────────

DENY = "deny"
DEFER = "defer"

# Tools this hook governs. Anything else → defer (the hook only blocks what it
# is responsible for). Write/Edit share the file_path channel; Bash is the
# command channel.
_FILE_TOOLS: frozenset[str] = frozenset({"Write", "Edit"})
_GOVERNED: frozenset[str] = _FILE_TOOLS | {"Bash"}

# Raw network tools — locus ii, accidental-closed-now. argv[0] token-boundary
# match (a bare whole-string regex would wrongly match ``curlytool``). The obvious
# aliases are included; the OS sandbox (locus iii) is the adversarial backstop.
_NETWORK_TOOLS: frozenset[str] = frozenset({"curl", "wget"})

# The safe CLI family — defer (identity-only allow; never a hook-emitted grant).
_SAFE_FAMILY_PREFIXES: tuple[str, ...] = ("sulis-", "wpx-")

# Compound-Bash separators we decompose on (ADR-003). Order matters: multi-char
# operators are split before their single-char prefixes so ``|&`` / ``||`` /
# ``&&`` are not mis-split. Newlines are separators too.
_SEPARATORS: tuple[str, ...] = ("&&", "||", "|&", ";", "|", "&", "\n")

# Best-effort file-write commands whose destination we scope-check (ADR-003,
# labelled best-effort — full subprocess I/O is locus iii / SC-E7).
_WRITE_COMMANDS: frozenset[str] = frozenset({"tee", "cp", "mv", "rm"})

# Command-substitution bodies: $(…) and `…`. Extracted and evaluated as their
# own sub-commands so a ``curl`` hidden in a substitution still denies.
_DOLLAR_SUBST = re.compile(r"\$\(([^()]*)\)")
_BACKTICK_SUBST = re.compile(r"`([^`]*)`")


@dataclass(frozen=True)
class Decision:
    """The hook's verdict for one tool call. ``action`` ∈ {DENY, DEFER}."""

    action: str
    reason: str = ""


# ─── Bash decomposition (the hook reads the RAW command string) ───────────────


def _extract_substitutions(command: str) -> list[str]:
    """Return the bodies of every ``$(…)`` and backtick substitution.

    These are evaluated as their own sub-commands — the docs' operator-awareness
    applies to permission-rule matching, not to what a hook receives, so the
    hook must look inside substitutions itself (the documented bypass:
    ``echo $(curl evil)``)."""
    bodies: list[str] = []
    bodies.extend(m.group(1) for m in _DOLLAR_SUBST.finditer(command))
    bodies.extend(m.group(1) for m in _BACKTICK_SUBST.finditer(command))
    return [b for b in bodies if b.strip()]


def _strip_substitutions(command: str) -> str:
    """Blank out substitution bodies before separator-splitting the outer
    command, so their inner separators don't fragment the parse twice (the
    bodies are evaluated separately via :func:`_extract_substitutions`)."""
    command = _DOLLAR_SUBST.sub(" ", command)
    command = _BACKTICK_SUBST.sub(" ", command)
    return command


def _split_on_separators(segment: str) -> list[str]:
    """Split one segment on every recognised compound separator."""
    parts = [segment]
    for sep in _SEPARATORS:
        nxt: list[str] = []
        for part in parts:
            nxt.extend(part.split(sep))
        parts = nxt
    return [p.strip() for p in parts if p.strip()]


def decompose_bash(command: str) -> list[str]:
    """Decompose a compound Bash command into its sub-commands (ADR-003).

    Splits the outer command (substitution bodies blanked) on the recognised
    separators AND returns every ``$(…)``/backtick substitution body as its own
    sub-command. Each returned sub-command is evaluated independently — a raw
    network tool anywhere denies the whole call."""
    subs = _extract_substitutions(command)
    outer = _split_on_separators(_strip_substitutions(command))
    # Substitution bodies may themselves be compound — decompose recursively.
    expanded: list[str] = list(outer)
    for body in subs:
        expanded.extend(_split_on_separators(body))
    return expanded


def _argv(sub_command: str) -> list[str]:
    """Best-effort argv for a sub-command. Falls back to a whitespace split when
    ``shlex`` can't parse (unbalanced quotes) — fail-closed-friendly: a token we
    can't parse still gets a chance to match a network tool / write command."""
    try:
        return shlex.split(sub_command)
    except ValueError:
        return sub_command.split()


def _command_name(token: str) -> str:
    """The bare command name for a token: strip a leading path and an
    ``env-style`` ``VAR=val`` prefix is handled by the caller. ``/usr/bin/curl``
    → ``curl``."""
    return Path(token).name


def _first_command_token(argv: list[str]) -> str | None:
    """The first real command token, skipping leading ``VAR=value`` assignments
    (``X=$(…) curl …`` — the command is ``curl``, not the assignment)."""
    for token in argv:
        if "=" in token and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", token):
            continue
        return token
    return None


def _redirect_targets(sub_command: str) -> list[str]:
    """Best-effort file-write targets from a sub-command (ADR-003, best-effort).

    Covers ``>``/``>>`` redirects and the destination operand of
    ``tee``/``cp``/``mv``/``rm``. Explicitly best-effort: arbitrary subprocess
    file I/O is locus iii (SC-E7), NOT closed here."""
    targets: list[str] = []

    # `>` / `>>` redirects — the token following the redirect operator.
    for m in re.finditer(r">>?\s*([^\s;|&>]+)", sub_command):
        targets.append(m.group(1))

    argv = _argv(sub_command)
    name = _command_name(_first_command_token(argv) or "")
    if name in _WRITE_COMMANDS:
        operands = [t for t in argv[1:] if not t.startswith("-")]
        if name == "tee":
            # tee writes every file operand.
            targets.extend(operands)
        elif name in {"cp", "mv"}:
            # destination is the last operand.
            if operands:
                targets.append(operands[-1])
        elif name == "rm":
            # rm mutates every operand.
            targets.extend(operands)
    return targets


# ─── the pure decision ────────────────────────────────────────────────────────


def _scope_deny(file_path: str, *, change_id, roots, operation: str) -> Decision | None:
    """Scope-check one path; return a DENY Decision if out-of-scope, else None.

    Delegates to the WP-002 resolver — zero re-implemented scope logic. Locus ii
    for the tool surface (accidental-closed-now)."""
    ok, reason = within_allowed_scope(
        file_path, change_id, operation=operation, roots=roots
    )
    if not ok:
        return Decision(DENY, reason)
    return None


def decide(
    event: dict,
    *,
    change_id,
    roots: AllowedRoots | None = None,
) -> Decision:
    """The pure PreToolUse verdict for one event.

    ``event`` is the parsed stdin JSON (``{tool_name, tool_input}``). ``roots``
    is an optional pre-built allowlist; when omitted it is left to the resolver
    (callers that have a repo_root build it; tests inject one). A missing /
    invalid ``change_id`` with a governed file/redirect op is a DENY
    (fail-closed) — an unscoped session must not get a free pass on a write."""
    tool_name = event.get("tool_name", "")
    if tool_name not in _GOVERNED:
        return Decision(DEFER)

    tool_input = event.get("tool_input") or {}

    # Write / Edit — scope-check the file_path. locus ii, accidental-closed-now.
    if tool_name in _FILE_TOOLS:
        file_path = tool_input.get("file_path")
        if not file_path:
            # A governed file op with no path we can check → fail-closed.
            return Decision(DENY, "Write/Edit with no file_path — refusing fail-closed.")
        denial = _scope_deny(
            file_path, change_id=change_id, roots=roots, operation="write"
        )
        return denial or Decision(DEFER)

    # Bash — decompose, then evaluate every sub-command.
    command = tool_input.get("command", "")
    if not command.strip():
        return Decision(DEFER)

    for sub in decompose_bash(command):
        argv = _argv(sub)
        cmd_token = _first_command_token(argv)
        if cmd_token is None:
            continue
        name = _command_name(cmd_token)

        # Rule 1 — raw network tool anywhere → deny the whole call. locus ii,
        # accidental-closed-now; belt-and-braces with the permission deny-rule.
        if name in _NETWORK_TOOLS:
            return Decision(
                DENY,
                f"raw network tool '{name}' is denied — use the safe MCP path "
                f"(mcp__sulis-safe-tools__safe_fetch). (locus ii; the OS sandbox "
                f"is the adversarial backstop for subprocess egress — SC-E7.)",
            )

        # Rule 2 — safe CLI family → defer (identity-only; never a hook grant).
        if any(name.startswith(p) for p in _SAFE_FAMILY_PREFIXES):
            continue

        # Rule 3 — best-effort file-write target scope-check. locus ii,
        # best-effort; full subprocess file I/O is locus iii (SC-E7).
        for target in _redirect_targets(sub):
            denial = _scope_deny(
                target, change_id=change_id, roots=roots, operation="write"
            )
            if denial is not None:
                return denial

    return Decision(DEFER)


# ─── rendering + the stdin/stdout/exit contract ───────────────────────────────


def render_decision(*, decision_action: str, reason: str) -> str:
    """Render a Decision to the PreToolUse stdout payload.

    DENY → the documented JSON envelope. DEFER → the empty string (the hook
    stays silent so the normal permission flow proceeds — ADR-003)."""
    if decision_action == DENY:
        return json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    return ""


def _resolve_change_id() -> str:
    """Active change id from the launch environment (same convention as the
    WP-001 MCP server — never taken from agent args)."""
    import os

    return os.environ.get("SULIS_CHANGE_ID", "").strip()


def _resolve_repo_root(change_id: str) -> str:
    """Repo root from the launch environment, else the change's worktree (mirror
    of the WP-001 MCP server resolution)."""
    import os

    explicit = os.environ.get("SULIS_REPO_ROOT")
    if explicit:
        return explicit
    if change_id:
        from _change_state import change_worktree_dir

        return str(change_worktree_dir(change_id))
    return os.getcwd()


def _build_roots(change_id: str) -> AllowedRoots | None:
    """Build the allowlist for the runtime change scope, or None if it can't be
    built (fail-closed: the caller then blocks a governed op)."""
    if not change_id:
        return None
    try:
        return resolve_allowed_roots(change_id, repo_root=Path(_resolve_repo_root(change_id)))
    except (ValueError, OSError) as exc:  # pragma: no cover - defensive
        raise RuntimeError(f"cannot build allowlist for change {change_id}: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    """Read the PreToolUse stdin JSON, decide, emit, exit.

    Fail-closed (exit 2 with a stderr reason) on: non-JSON stdin, a governed
    file/Bash-write op with no resolvable change scope, or any internal error.
    A defer is silent + exit 0; a deny prints the JSON envelope + exit 0."""
    raw = sys.stdin.read()
    try:
        event = json.loads(raw)
        if not isinstance(event, dict):
            raise ValueError("hook stdin is not a JSON object")
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"safe-tools-hook: unparseable PreToolUse input — refusing fail-closed: {exc}", file=sys.stderr)
        return 2

    tool_name = event.get("tool_name", "")
    if tool_name not in _GOVERNED:
        return 0  # not ours → defer silently

    change_id = _resolve_change_id()
    try:
        roots = _build_roots(change_id)
    except RuntimeError as exc:
        print(f"safe-tools-hook: {exc} — refusing fail-closed.", file=sys.stderr)
        return 2

    # A governed file op (or a Bash with a parseable write target) needs a scope
    # to check against. No scope → fail-closed.
    needs_scope = tool_name in _FILE_TOOLS or (
        tool_name == "Bash"
        and any(
            _redirect_targets(sub)
            for sub in decompose_bash((event.get("tool_input") or {}).get("command", ""))
        )
    )
    if needs_scope and roots is None:
        print(
            "safe-tools-hook: no valid change scope (SULIS_CHANGE_ID unset/invalid) "
            "for a governed file operation — refusing fail-closed.",
            file=sys.stderr,
        )
        return 2

    try:
        decision = decide(event, change_id=change_id, roots=roots)
    except Exception as exc:  # noqa: BLE001 - fail-closed on ANY internal error
        print(f"safe-tools-hook: internal error — refusing fail-closed: {exc}", file=sys.stderr)
        return 2

    payload = render_decision(decision_action=decision.action, reason=decision.reason)
    if payload:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
