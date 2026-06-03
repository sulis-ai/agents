"""Structural (shape) verification for WP-010 — the /sulis:backlog skill.

WP-010 creates ``plugins/sulis/skills/backlog/SKILL.md`` — the founder-facing
**Traverse** command (FR-07). It answers, *off the brain graph*, what is
**open**, what is on the **Roadmap**, and what is **done** — by invoking the
``sulis-brain-query`` modes WP-008 added (``--open`` / ``--roadmap`` /
``--done``, plus ``--by-type`` / ``--by-state`` for narrower asks).

These are *shape* tests (the skill body's structure + contract statements),
not *behavioural* tests. The behavioural coverage — that asking the backlog
returns open ideas + roadmap + done sourced from brain entities, and an empty
store reads as "nothing yet" not an error — is the **traverse scenario
journey** authored in WP-013 (run-from-graph), per the WP Contract's
"Behavioural coverage" note.

Per the WP Contract (``Definition of Done > Red``), the skill body MUST:

  1. Read the **brain graph** via ``sulis-brain-query`` and explicitly note it
     is **distinct** from ``/sulis:dashboard`` / ``/sulis:inbox`` (which read
     the change-store) — so future maintainers don't conflate them. It must
     NOT read ``.changes/`` or the change-store.
  2. Carry frontmatter (``name: backlog`` + a founder-English ``description:``)
     and be free of jargon leaked to the founder: no ``dna:`` ids, no raw
     state names presented as the output, no schema vocabulary
     (``for_product`` etc.). Names/titles, not ids.
  3. Cover all three founder-facing views — **open**, **roadmap**, **done**.

Stdlib + pytest only, Python 3.11-safe. Resolves paths relative to this test
file so the suite is location-stable inside any worktree.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# tests/methodology/ -> tests/ -> scripts/ -> sulis/ -> plugins/ -> repo-root
_REPO_ROOT = Path(__file__).resolve().parents[5]
_SKILL = _REPO_ROOT / "plugins" / "sulis" / "skills" / "backlog" / "SKILL.md"

# The brain read seam WP-008 exposes; the skill body must invoke it by name
# rather than reach into the on-disk layout (FR-07 / ADR-006).
_QUERY_SEAM = "sulis-brain-query"

# The change-store skills the backlog must hold itself APART from — they read
# a different source (the change-store) and answer a different question.
_CHANGE_STORE_SKILLS = ("/sulis:dashboard", "/sulis:inbox")

# Jargon that must NEVER reach the founder (NFR-02): entity ids, schema fields.
_JARGON_IDS = ("dna:opportunity:", "dna:requirement:", "dna:")
_JARGON_SCHEMA_FIELDS = ("for_product", "backs", "verifies")


@pytest.fixture(scope="module")
def skill_text() -> str:
    """Read the skill body once per test module."""
    if not _SKILL.exists():
        pytest.fail(
            f"backlog skill missing at {_SKILL}. WP-010 creates this file; "
            "the shape assertions cannot run until it exists."
        )
    return _SKILL.read_text(encoding="utf-8")


def _frontmatter(text: str) -> str:
    """Return the YAML frontmatter block (between the first two ``---``)."""
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    return m.group(1) if m else ""


def _body(text: str) -> str:
    """Return everything AFTER the frontmatter block (the founder-facing prose)."""
    m = re.match(r"^---\n.*?\n---\n(.*)$", text, re.DOTALL)
    return m.group(1) if m else text


def test_skill_reads_brain_not_change_store(skill_text: str) -> None:
    """The body invokes ``sulis-brain-query`` (the brain seam) and explicitly
    notes it is DISTINCT from ``/sulis:dashboard`` / ``/sulis:inbox``; it does
    not read ``.changes/`` or the change-store."""
    assert _SKILL.exists(), f"backlog skill missing at {_SKILL}."

    # Reads the brain via the WP-008 query seam — by name, not by reaching into
    # the on-disk layout.
    assert _QUERY_SEAM in skill_text, (
        f"Expected the body to invoke the brain read seam `{_QUERY_SEAM}` "
        "(the WP-008 CLI), not reach into `.brain/instances/` directly."
    )
    assert re.search(r"\bbrain\b", skill_text, re.IGNORECASE), (
        "Expected the body to state it reads the brain graph."
    )

    # Explicitly distinct from the change-store skills, so maintainers don't
    # conflate the two read surfaces.
    for skill in _CHANGE_STORE_SKILLS:
        assert skill in skill_text, (
            f"Expected the body to name `{skill}` and hold the backlog apart "
            "from it (it reads the change-store; backlog reads the brain)."
        )
    assert re.search(
        r"(distinct|different|not)[\s\S]{0,120}(dashboard|inbox|change[\s-]?store)"
        r"|(dashboard|inbox|change[\s-]?store)[\s\S]{0,120}(distinct|different|not\b)",
        skill_text,
        re.IGNORECASE,
    ), (
        "Expected the body to state EXPLICITLY that the backlog is distinct "
        "from dashboard/inbox (which read the change-store) — so future "
        "maintainers don't conflate them."
    )

    # Does NOT read the change-store / `.changes/` manifest. The only mentions
    # of dashboard/inbox/change-store allowed are the contrast statement above;
    # the body must not instruct reading `.changes/` itself.
    assert not re.search(r"read[\s\S]{0,40}\.changes/", skill_text, re.IGNORECASE), (
        "The backlog must NOT read the change-store (`.changes/`); that is the "
        "dashboard/inbox source. It reads the brain graph via the query seam."
    )


def test_skill_frontmatter_and_no_jargon(skill_text: str) -> None:
    """Frontmatter present (``name: backlog`` + founder-English description);
    the founder-facing body is free of `dna:` ids, raw schema fields, and other
    jargon (NFR-02)."""
    fm = _frontmatter(skill_text)
    assert fm, (
        "Expected YAML frontmatter delimited by `---` at the top of the skill "
        "(mirroring the dashboard skill)."
    )
    assert re.search(r"^name:\s*backlog\s*$", fm, re.MULTILINE), (
        "Expected frontmatter `name: backlog`."
    )
    assert re.search(r"^description:\s*\S", fm, re.MULTILINE), (
        "Expected a non-empty frontmatter `description:` (founder-English)."
    )

    # No entity-id jargon anywhere the founder sees it. The whole point of
    # NFR-02 is the founder never sees `dna:*` ids — they get names/titles.
    for token in _JARGON_IDS:
        assert token not in skill_text, (
            f"Found jargon `{token}` in the skill — the founder must never see "
            "entity ids (NFR-02). Present names/titles instead."
        )

    # No raw schema field names leaked into the founder-facing body.
    for token in _JARGON_SCHEMA_FIELDS:
        assert token not in skill_text, (
            f"Found schema field `{token}` in the skill — schema vocabulary "
            "must not reach the founder (NFR-02)."
        )

    # The body presents names/titles, and explicitly commits to NOT showing
    # ids / raw states to the founder.
    assert re.search(r"\b(name|title)s?\b", skill_text, re.IGNORECASE), (
        "Expected the body to present entity names/titles to the founder "
        "(not ids) — NFR-02."
    )

    # Cites the founder-English / AAF standards BY PATH (not restating them).
    assert re.search(
        r"founder-english\.md|audience-adapted-framing-standard\.md"
        r"|founder-facing-conventions\.md",
        skill_text,
    ), (
        "Expected the body to cite the founder-English / AAF standards by path "
        "(NFR-02 voice), rather than restating them."
    )


def test_skill_covers_open_roadmap_done(skill_text: str) -> None:
    """All three founder-facing views are present in the body: open ideas, the
    roadmap, and done — each backed by the corresponding query-seam mode."""
    body = _body(skill_text)

    # The three founder-facing group labels (plain English — open / roadmap /
    # done), not entity-type / state vocabulary.
    assert re.search(r"open\s+ideas", body, re.IGNORECASE), (
        "Expected the founder-facing group 'Open ideas'."
    )
    assert re.search(r"roadmap", body, re.IGNORECASE), (
        "Expected the founder-facing group for the Roadmap."
    )
    assert re.search(r"\bdone\b", body, re.IGNORECASE), (
        "Expected the founder-facing group 'Done'."
    )

    # Each view is backed by the corresponding query-seam mode (the WP-008 CLI
    # verbs), so the skill composes the seam rather than re-deriving the
    # open/done mapping in prose (ADR-006 single-source).
    for mode in ("--open", "--roadmap", "--done"):
        assert mode in skill_text, (
            f"Expected the body to invoke `{_QUERY_SEAM} {mode}` — the WP-008 "
            "mode backing this view (ADR-006: the open/done mapping lives in "
            "the seam, not restated in prose)."
        )

    # Empty result reads as "nothing open yet" / "nothing yet", never an error
    # (NFR-01).
    assert re.search(
        r"nothing[\s\S]{0,20}(open\s+)?yet|nothing\s+yet",
        body,
        re.IGNORECASE,
    ), (
        "Expected an empty result to read as 'nothing open yet' / 'nothing "
        "yet' (NFR-01), never surfaced as an error."
    )
