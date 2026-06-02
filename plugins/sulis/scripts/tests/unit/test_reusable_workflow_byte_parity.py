"""Reusable-workflow structural test (WP-002 move, WP-003 extend, WP-005 shim).

History: this file began as the WP-002 (REORGANISE-Move) byte-parity
characterisation — it asserted the plugin-side reusable workflow at
`plugins/sulis/templates/workflows/release-on-merge.yml` carried the
marketplace's `.github/workflows/release-on-merge.yml` content byte-
identical as a prefix (the move was content-preserving).

WP-005 (SUBSTITUTE-Replace) retires that parity relationship by design:
the marketplace file is no longer the 280-line workflow — it is a thin
shim that *calls* the reusable workflow via a local `uses:` reference. A
shim is not a byte-prefix of the body it delegates to, so the parity
assertion no longer applies. The move-was-content-preserving guarantee is
now carried by the methodology-tier shell characterisation test at
`plugins/sulis/scripts/tests/methodology/test_release_on_merge_yaml_unchanged_behaviour.sh`
(which captured the pre-move steps snapshot at WP-002 time and diffs the
reusable workflow against it — independent of the now-replaced marketplace
file). What remains load-bearing here, and is retained below, are the
reusable workflow's own structural invariants:

  * it exists;
  * it uses the `workflow_call:` trigger (not `push:`);
  * it declares `contents: write` + `pull-requests: write` at job level
    (TDD §5.8 — GitHub does not inherit caller permissions into reusable
    workflows, so the moved permissions must be re-declared at job level);

plus a new post-WP-005 assertion that the marketplace file is a shim that
delegates to the reusable workflow (a local `uses:` reference, no inline
step body).

The reusable workflow differs from the pre-move marketplace body in three
structural adjustments (kept for context): (1) `on:` becomes
`workflow_call:`; (2) job-level `permissions:` re-declares `contents:
write` and adds `pull-requests: write`; (3) `name:` carries "(reusable)".
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
MARKETPLACE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "release-on-merge.yml"
REUSABLE_WORKFLOW = (
    REPO_ROOT
    / "plugins"
    / "sulis"
    / "templates"
    / "workflows"
    / "release-on-merge.yml"
)

# The local `uses:` reference the marketplace shim delegates through. The
# OWNING repo references its workflow by local path (always tracks the
# current commit); external consumers pin the cross-repo @tag form instead.
_LOCAL_USES = "./plugins/sulis/templates/workflows/release-on-merge.yml"


@pytest.fixture
def marketplace_content() -> str:
    return MARKETPLACE_WORKFLOW.read_text(encoding="utf-8")


@pytest.fixture
def reusable_content() -> str:
    return REUSABLE_WORKFLOW.read_text(encoding="utf-8")


def test_reusable_workflow_exists() -> None:
    assert REUSABLE_WORKFLOW.exists(), (
        f"plugin-side reusable workflow not found at {REUSABLE_WORKFLOW}"
    )


def test_marketplace_workflow_exists() -> None:
    # Post-WP-005 the marketplace file is a thin shim (not the full body),
    # but it must still exist — it is the entrypoint that fires on push to
    # main and delegates to the reusable workflow.
    assert MARKETPLACE_WORKFLOW.exists(), (
        f"marketplace workflow not found at {MARKETPLACE_WORKFLOW} "
        "(WP-005 replaced its body with a shim, but the file must remain "
        "as the push-to-main entrypoint)"
    )


def test_marketplace_workflow_is_shim_delegating_to_reusable(
    marketplace_content: str,
) -> None:
    """Post-WP-005: the marketplace file delegates to the reusable workflow.

    Replaces the retired byte-parity assertion. The marketplace file is no
    longer a prefix of the reusable workflow — it is a thin shim whose job
    `uses:` the reusable workflow via the local path. The inline bump/tag
    step bodies that lived in the pre-move 280-line workflow must be GONE
    (they now live only in the reusable workflow).
    """
    assert re.search(
        rf"^\s*uses:\s*{re.escape(_LOCAL_USES)}\s*$",
        marketplace_content,
        flags=re.MULTILINE,
    ), (
        f"marketplace shim must delegate via `uses: {_LOCAL_USES}`; "
        "not found in .github/workflows/release-on-merge.yml"
    )
    # The shim must not inline the moved step bodies.
    assert "Apply the version bump" not in marketplace_content, (
        "marketplace file still contains the inline bump step — WP-005 "
        "should have replaced the body with a delegating shim"
    )
    # The owning repo uses the LOCAL ref, never the cross-repo @tag consumer
    # form (that form is for external consumer shims only).
    assert "sulis-ai/agents/plugins/sulis/templates/workflows" not in marketplace_content, (
        "marketplace shim uses the cross-repo @tag consumer form; the "
        "owning repo must reference its workflow by local path"
    )


def test_reusable_workflow_uses_workflow_call_trigger(
    reusable_content: str,
) -> None:
    """The structural adjustment: `on: workflow_call:` replaces
    `on: push: branches: [main]`. Per TDD §4.2 the reusable workflow
    accepts zero inputs at WP-002 time (inputs come in WP-003 if at all).
    """
    assert re.search(
        r"^on:\s*\n\s+workflow_call:\s*\n",
        reusable_content,
        flags=re.MULTILINE,
    ), "reusable workflow must use `on: workflow_call:` trigger"

    # And must NOT use the push-to-main trigger that the marketplace
    # shim carries.
    assert not re.search(
        r"^on:\s*\n\s+push:",
        reusable_content,
        flags=re.MULTILINE,
    ), "reusable workflow must not use `on: push:` trigger"


def test_reusable_workflow_declares_pull_requests_permission(
    reusable_content: str,
) -> None:
    """Per TDD §5.8: reusable workflow re-declares permissions at the
    job level and adds `pull-requests: write` (forward-looking for
    WP-003's gh pr create / gh pr merge --auto). The bare
    `contents: write` that the marketplace file carries is not
    sufficient — GitHub does not inherit caller permissions into
    reusable workflows.
    """
    # Trailing comments after the write keyword are permitted (the
    # source workflow's commenting style carries inline annotations
    # after value tokens on permission lines). [^\n]* explicitly
    # excludes newlines from the trailing-content match so we don't
    # accidentally span lines.
    assert re.search(
        r"^    permissions:\n"
        r"(?:      .*\n)*"
        r"      pull-requests:[ \t]+write[ \t]*(?:#[^\n]*)?\n",
        reusable_content,
        flags=re.MULTILINE,
    ), "reusable workflow must declare `pull-requests: write` at job level"

    assert re.search(
        r"^    permissions:\n"
        r"(?:      .*\n)*"
        r"      contents:[ \t]+write[ \t]*(?:#[^\n]*)?\n",
        reusable_content,
        flags=re.MULTILINE,
    ), "reusable workflow must declare `contents: write` at job level"
