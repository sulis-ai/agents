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

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _wpxlib import _run  # noqa: E402


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


# ─── Rendering ─────────────────────────────────────────────────────────────


def _render_context_md(change_id: str, metadata: dict, git_state: dict) -> str:
    """Render the CONTEXT.md markdown body (human-readable, cat-able)."""
    primitive = metadata.get("primitive", "")
    hint = _PRIMITIVE_NEXT_STEP_HINTS.get(primitive, _DEFAULT_HINT)
    return (
        f"# Change context — {metadata.get('handle', change_id)}\n"
        f"\n"
        f"> Pre-spawn recon written by sulis-change. Pure-read snapshot; "
        f"safe to `cat` for debugging.\n"
        f"\n"
        f"## Change identity\n"
        f"\n"
        f"- **change_id:** `{change_id}`\n"
        f"- **handle:** {metadata.get('handle', '(none)')}\n"
        f"- **slug:** {metadata.get('slug', '(none)')}\n"
        f"- **primitive:** {primitive or '(none)'}\n"
        f"- **branch:** `{metadata.get('branch', '(none)')}`\n"
        f"\n"
        f"## Git state at spawn\n"
        f"\n"
        f"- **HEAD:** `{git_state['head_sha']}`\n"
        f"- **base ({git_state['base_ref']}):** `{git_state['base_sha']}`\n"
        f"- **ahead of {git_state['base_ref']}:** {git_state['ahead']} commit(s)\n"
        f"- **behind {git_state['base_ref']}:** {git_state['behind']} commit(s)\n"
        f"\n"
        f"## Suggested next step\n"
        f"\n"
        f"{hint}\n"
    )


def write_change_context(
    change_id: str,
    metadata: dict,
    repo_root: Path,
) -> Path:
    """Gather pre-spawn context and write ~/.sulis/changes/{change_id}/CONTEXT.md.

    Sections: change identity, git state at spawn, suggested next step
    (looked up from _PRIMITIVE_NEXT_STEP_HINTS).

    Pure-read: never modifies the repo. Subprocess calls are git-rev-parse
    and git-rev-list only. Returns the absolute path to the written file.
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

    body = _render_context_md(change_id, metadata, git_state)

    change_dir = Path.home() / ".sulis" / "changes" / change_id
    change_dir.mkdir(parents=True, exist_ok=True)
    context_path = change_dir / "CONTEXT.md"
    context_path.write_text(body, encoding="utf-8")
    return context_path.resolve()
