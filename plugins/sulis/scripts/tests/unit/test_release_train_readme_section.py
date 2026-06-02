"""Docs-prose verification for WP-011 (release-train-as-entities change).

WP-011 adds a new section to ``plugins/sulis/README.md`` titled
"Customising the release-train for your own marketplace fork" that
cross-references the SRD's Configuration Vocabulary section. This module
is the RED-phase verification: the WP has no runtime tests (docs prose),
so the failing-first cycle pins the documented invariants on the live
README as structural assertions.

Per the WP Contract (`Definition of Done > Green`), the section MUST:

  1. Exist as a top-level ``##`` heading whose text contains
     "Customising the release-train" (so fork-consumers find it via the
     GitHub TOC).
  2. Cross-reference the SRD's Configuration Vocabulary section via a
     relative link that resolves both on GitHub and on local disk.
  3. Name the worked-example Project entities (``sulis``,
     ``sulis-brain``, ``plugin-builder``, ``investor-coach``) so
     fork-consumers see a typical fill pattern.
  4. Reference the future ``project-discovery`` Workflow sibling so
     fork-consumers understand the v1 manual path is the documented
     fallback (reduces anxiety per the WP Context).

Stdlib + pytest only, Python 3.11-safe. Resolves paths relative to this
test file so the suite is location-stable inside any worktree.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# tests/unit/ -> tests/ -> scripts/ -> sulis/ -> plugins/sulis/
_README = (
    Path(__file__).resolve().parents[3] / "README.md"
)

# plugins/sulis/ -> plugins/ -> repo-root -> .specifications/...
_REPO_ROOT = Path(__file__).resolve().parents[5]
_SRD = _REPO_ROOT / ".specifications" / "release-train-as-entities" / "SRD.md"

# The relative link the README uses to point at the SRD's Configuration
# Vocabulary section. README lives at plugins/sulis/README.md, so the
# relative path is "../../.specifications/...". The link MUST appear in
# the README verbatim (the cross-reference is the WP's core deliverable).
_EXPECTED_LINK_PATH = (
    "../../.specifications/release-train-as-entities/SRD.md"
    "#configuration-vocabulary"
)

_WORKED_EXAMPLES = ("sulis", "sulis-brain", "plugin-builder", "investor-coach")


@pytest.fixture(scope="module")
def readme_text() -> str:
    """The live README content as a single string."""
    assert _README.is_file(), f"missing marketplace README at {_README}"
    return _README.read_text(encoding="utf-8")


def test_section_heading_present(readme_text: str) -> None:
    """A top-level ``##`` heading mentioning customising the release-train.

    Fork-consumers navigate GitHub TOC by ``##`` headings; the section
    being inline prose under another heading wouldn't surface.
    """
    lines = readme_text.splitlines()
    matches = [
        line for line in lines
        if line.startswith("## ") and "Customising the release-train" in line
    ]
    assert matches, (
        "README is missing the WP-011 section heading. Expected a "
        "top-level '## Customising the release-train ...' so the "
        "GitHub TOC surfaces it for fork-consumers."
    )


def test_cross_reference_link_present(readme_text: str) -> None:
    """The SRD Configuration Vocabulary cross-reference link is verbatim.

    The link is the WP's core deliverable — fork-consumers click through
    from the marketplace README to the authoritative Project-entity
    field list.
    """
    assert _EXPECTED_LINK_PATH in readme_text, (
        f"README is missing the cross-reference to {_EXPECTED_LINK_PATH}. "
        "Fork-consumers need this link to reach the authoritative "
        "Project-entity field reference."
    )


def test_cross_reference_link_resolves(readme_text: str) -> None:
    """The link target file exists AND has the expected anchor heading.

    GitHub auto-generates the ``#configuration-vocabulary`` anchor from a
    ``## Configuration Vocabulary`` heading; we assert both halves so a
    future SRD rename surfaces here, not only when a fork-consumer
    clicks a dead link.
    """
    assert _SRD.is_file(), f"SRD target missing at {_SRD}"
    srd_text = _SRD.read_text(encoding="utf-8")
    assert "## Configuration Vocabulary" in srd_text, (
        f"SRD at {_SRD} is missing the '## Configuration Vocabulary' "
        "heading the README link anchors to."
    )


def test_worked_examples_named(readme_text: str) -> None:
    """All four worked-example Project entities named in the section.

    The WP Contract names ``sulis``, ``sulis-brain``, ``plugin-builder``,
    ``investor-coach`` so fork-consumers see a typical fill pattern.
    """
    missing = [ex for ex in _WORKED_EXAMPLES if ex not in readme_text]
    assert not missing, (
        "README is missing worked-example Project name(s): "
        f"{missing}. The WP Contract names all four "
        f"({list(_WORKED_EXAMPLES)}) as the typical-fill reference set."
    )


def test_future_discovery_sibling_referenced(readme_text: str) -> None:
    """The future ``project-discovery`` Workflow is mentioned.

    Per WP Context: setting the expectation that v1 manual authoring is
    the documented fallback (not a permanent state) reduces fork-consumer
    anxiety. The sibling is referenced by name.
    """
    assert "project-discovery" in readme_text, (
        "README is missing the reference to the future "
        "'project-discovery' Workflow sibling. Per WP Context this "
        "reference sets fork-consumer expectations that the manual "
        "v1 path is the documented fallback, not a permanent state."
    )
