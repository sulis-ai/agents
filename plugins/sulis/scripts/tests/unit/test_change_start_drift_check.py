"""Structural assertion: /sulis:change `start` runs the drift gate first.

Per FR-010 + ADR-003 + TDD §4.2 (comp-drift-check-cs) + §5.5 (L3),
`/sulis:change start` must invoke the shared drift detector
(`plugins/sulis/scripts/drift_check.sh`, built in WP-001) as the
FIRST preflight action in the `start` subcommand — before any branch
is cut. A new change branch cut off a `dev` that's behind `main`
re-introduces stale content into the next release; this gate stops
that at the developer entry point (the L3 defence-in-depth layer; L2
is the release-train gate, WP-006).

What this test pins (the WP-007 contract):

  1. The `start` subcommand's prose references `drift_check.sh` by
     its canonical path (no inlined `git merge-base` logic).
  2. The drift sub-step is positioned BEFORE the branch-creating
     side effect (`sulis-change start ... --spawn`) — the gate must
     run before any change record or branch exists.
  3. The dev-behind-main STOP behaviour is documented: on a
     definitive drift the skill refuses to start (no branch cut).
  4. Graceful degradation is documented: a tooling / fresh-repo
     error (git unavailable, not a repo, fetch failed — all of which
     the WP-001 helper folds into exit 1) does NOT block change-start.
     Only a definitive "dev is behind main" stops it. The
     discriminator is the helper's stderr message, since the helper's
     consolidated contract exposes only exit 0 / 1.
  5. The sub-step cross-references GIT-12 (the recovery procedure
     lives there).

SKILL.md prose is not unit-testable the way Python is, so this is a
structural assertion over the skill text. Stdlib + pytest,
Python 3.11-safe — mirrors test_branch_ci_has_drift_check.py.
"""

from __future__ import annotations

from pathlib import Path

# tests/unit/ -> tests/ -> scripts/ -> sulis/ -> plugins/ -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[5]
_SKILL = _REPO_ROOT / "plugins" / "sulis" / "skills" / "change" / "SKILL.md"

# Canonical path the sub-step must reference (no inlined helper logic).
_HELPER_PATH = "plugins/sulis/scripts/drift_check.sh"

# The branch-creating side effect in the `start` subcommand. The drift
# gate must appear before this in document order.
_BRANCH_CREATE_MARKER = '"$SCRIPTS_DIR/sulis-change" start'

# The helper's definitive-drift stderr discriminator (WP-001). The
# skill keys its STOP decision on this string, not on the exit code
# (which is 1 for both drift and tooling errors).
_DRIFT_DISCRIMINATOR = "dev is behind main"


def _skill_text() -> str:
    assert _SKILL.is_file(), f"change SKILL.md not found at {_SKILL}"
    return _SKILL.read_text(encoding="utf-8")


def _start_section(text: str) -> str:
    """Return the body of the `start` subcommand section.

    The `start` subcommand begins at its "### start ..." heading and
    runs until the next "###" heading (the next subcommand). The
    drift gate belongs inside this slice.
    """
    start_idx = text.find("### `start")
    assert start_idx != -1, "no `### `start`` subcommand heading found"
    rest = text[start_idx + len("### `start") :]
    next_idx = rest.find("\n### ")
    end = len(text) if next_idx == -1 else start_idx + len("### `start") + next_idx
    return text[start_idx:end]


def test_start_section_references_drift_helper() -> None:
    """1. The `start` subcommand references drift_check.sh by path."""
    section = _start_section(_skill_text())
    assert _HELPER_PATH in section, (
        "the `start` subcommand must reference the shared drift helper "
        f"by its canonical path {_HELPER_PATH!r}; found none in the section"
    )


def test_no_inlined_helper_logic() -> None:
    """1b. The sub-step calls the helper; it never inlines the check."""
    section = _start_section(_skill_text())
    assert "git merge-base --is-ancestor" not in section, (
        "the `start` subcommand must NOT inline the ancestor check; the "
        "helper at drift_check.sh owns that logic (ADR-003, single source "
        "of truth)"
    )


def test_drift_gate_runs_before_branch_creation() -> None:
    """2. The drift gate precedes the branch-creating side effect."""
    text = _skill_text()
    section = _start_section(text)
    helper_pos = section.find(_HELPER_PATH)
    branch_pos = section.find(_BRANCH_CREATE_MARKER)
    assert helper_pos != -1, "drift helper reference missing from `start`"
    assert branch_pos != -1, (
        f"branch-creating marker {_BRANCH_CREATE_MARKER!r} missing from "
        "`start` — test fixture assumptions broken"
    )
    assert helper_pos < branch_pos, (
        "the drift gate must run BEFORE the branch is cut "
        f"(drift_check.sh at offset {helper_pos}, "
        f"branch creation at offset {branch_pos}); a gate that runs after "
        "the branch exists has already lost"
    )


def test_dev_behind_main_stop_documented() -> None:
    """3. The dev-behind-main STOP (no branch cut) is documented."""
    section = _start_section(_skill_text()).lower()
    assert _DRIFT_DISCRIMINATOR in section, (
        "the `start` subcommand must document the definitive-drift "
        f"condition ({_DRIFT_DISCRIMINATOR!r}) on which it STOPS"
    )
    # On definitive drift the skill stops without cutting a branch.
    assert "stop" in section or "refuse" in section, (
        "the prose must state that the skill STOPS / refuses on "
        "definitive drift"
    )
    assert "no branch" in section or "no change record" in section or (
        "before" in section and "branch" in section
    ), "the prose must make clear no branch is cut when drift is detected"


def test_graceful_degradation_documented() -> None:
    """4. Tooling / fresh-repo errors degrade gracefully, do not block.

    The WP-001 helper folds git-unavailable, not-a-repo, and
    fetch-failed into exit 1 alongside definitive drift. The skill
    must NOT treat those tooling errors as a blocking gate — only a
    definitive "dev is behind main" stops change-start. This is the
    fresh-clone / no-origin-main case in particular.
    """
    section = _start_section(_skill_text()).lower()
    # Some signal that a non-drift error is handled distinctly from
    # definitive drift (the prose discriminates rather than treating
    # every non-zero exit as a hard stop).
    degraded = any(
        token in section
        for token in (
            "fresh",
            "tooling",
            "not block",
            "doesn't block",
            "does not block",
            "degrade",
            "no origin/main",
            "no `origin/main`",
            "cannot verify",
        )
    )
    assert degraded, (
        "the `start` subcommand must document graceful degradation: a "
        "tooling / fresh-repo error (git unavailable, not a repo, no "
        "origin/main, fetch failed) must NOT block change-start; only a "
        "definitive dev-behind-main stops it"
    )


def test_cross_references_git12() -> None:
    """5. The drift sub-step cross-references GIT-12 (recovery)."""
    section = _start_section(_skill_text())
    assert "GIT-12" in section, (
        "the drift sub-step must cross-reference GIT-12, where the "
        "recovery procedure (wait for the back-integrate PR, or run the "
        "manual recovery) is documented"
    )
