"""Characterisation test for the latent /sulis:status duplicate (WP-004).

Both `skills/status/SKILL.md` and `skills/wp-status/SKILL.md` historically
declared `name: status`, so both derived the invocation `/sulis:status` — a
real duplicate (TDD §7.5#1). The routing coverage gate's no-duplicate rule
(RT-02, WP-007) cannot pass against the live tree while that holds.

Per the EP-07 / Fowler refactoring discipline, this test pins the *current*
behaviour of the two live frontmatter `name` fields before the one-line
metadata correction (`wp-status`'s `name: status` -> `name: wp-status`). After
the fix the two skills derive distinct invocations and the test stays green —
it is the auditable characterisation of "this repo's status invocation is
unique", independent of WP-007's generic gate assembly.

Stdlib only, Python 3.11-safe. Reads the live `SKILL.md` files directly via
the established `_wpxlib.read_frontmatter` reader (the scalar `name:` field is
unaffected by the folded-scalar limitation that motivated WP-001).
"""

from __future__ import annotations

from pathlib import Path

from _wpxlib import read_frontmatter

# Resolve the marketplace skills root relative to this test file.
# tests/unit/ -> tests/ -> scripts/ -> sulis/ -> plugins/sulis/
_SKILLS_ROOT = Path(__file__).resolve().parents[3] / "skills"

_STATUS_SKILL = _SKILLS_ROOT / "status" / "SKILL.md"
_WP_STATUS_SKILL = _SKILLS_ROOT / "wp-status" / "SKILL.md"


def _invocation_for(skill_md: Path) -> str:
    """Derive the `/sulis:<name>` invocation from a skill's frontmatter name.

    The invocation-derivation rule (TDD §3.1) keys off the frontmatter `name`,
    never the directory name — which is precisely why a `wp-status/` directory
    carrying `name: status` produced a true duplicate, not a coincidence.
    """
    fm = read_frontmatter(skill_md)
    name = fm.get("name")
    assert name, f"{skill_md} has no parseable frontmatter `name`"
    return f"/sulis:{name}"


def test_both_live_skill_files_exist():
    """Guard: the two skills under test are present in the live tree."""
    assert _STATUS_SKILL.is_file(), f"missing {_STATUS_SKILL}"
    assert _WP_STATUS_SKILL.is_file(), f"missing {_WP_STATUS_SKILL}"


def test_status_invocation_is_unique_in_live_tree():
    """The two status-family skills must derive DISTINCT invocations.

    Fails against the pre-fix tree (both derive `/sulis:status`); passes once
    `wp-status`'s frontmatter `name` is corrected to `wp-status`.
    """
    status_invocation = _invocation_for(_STATUS_SKILL)
    wp_status_invocation = _invocation_for(_WP_STATUS_SKILL)

    assert status_invocation != wp_status_invocation, (
        "status and wp-status derive the same invocation "
        f"({status_invocation!r}); the wp-status frontmatter `name` must be "
        "`wp-status`, not `status` (TDD §7.5#1)."
    )


def test_wp_status_name_matches_its_directory():
    """The corrected `wp-status` skill keys its invocation off `wp-status`.

    Pins the post-fix target explicitly so a future regression that reverts
    the `name` field is caught by name, not just by the uniqueness invariant.
    """
    assert _invocation_for(_WP_STATUS_SKILL) == "/sulis:wp-status"


def test_status_skill_keeps_its_invocation():
    """The founder-journey `status` skill retains `/sulis:status`.

    The founder decision is explicit: only `wp-status`'s metadata changes; the
    `status` skill is untouched and keeps the `/sulis:status` invocation.
    """
    assert _invocation_for(_STATUS_SKILL) == "/sulis:status"
