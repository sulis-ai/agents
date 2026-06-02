"""Byte-parity test for WP-002 (REORGANISE-Move), as extended by WP-003.

Asserts that the plugin-side reusable workflow at
`plugins/sulis/templates/workflows/release-on-merge.yml` carries the
marketplace's `.github/workflows/release-on-merge.yml` content
byte-identical *as a prefix* — i.e. WP-002's move was content-preserving
for the shared portion — EXCEPT for:

  1. The top-level `on:` block — changes from `push: branches: [main]`
     to `workflow_call:` (TDD §4.2).
  2. The job-level `permissions:` block — the move re-declares the
     existing `contents: write` permission and adds `pull-requests:
     write` (TDD §5.8; pull-requests:write is forward-looking for
     WP-003's gh pr create/merge --auto).
  3. The top-level `name:` — the reusable variant carries "(reusable)"
     in its name for clarity.
  4. The reusable-variant header comment block — a leading comment
     block immediately after `name:` that names the file as a
     reusable workflow, names the caller mechanism (`uses:` from a
     shim), and points at the canonical shim template path. WP-002
     DoD Blue mandates this header; it is delimited by the lead
     marker `# REUSABLE WORKFLOW` on its first line and ends at the
     first blank line preceding the marketplace workflow's own
     header comment (which begins with `# WP-003 — the ONE bump
     authority`).

Every byte the two files SHARE (job structure, the move-preserved step
bodies, env vars, `if:` guards, concurrency, comments) MUST match the
marketplace workflow character-for-character. That is the "byte parity
modulo trigger" load-bearing characterisation for the REORGANISE-Move.

WP-003 (EXPAND-Extend) appends a three-step auto-back-merge block
(pin-read, decide+act, post-condition) to the END of the reusable
workflow only — it edits none of the moved steps. The marketplace file
is therefore a byte-for-byte PREFIX of the reusable file (after masking
the three structural adjustments). The byte-parity assertion is relaxed
to prefix-parity to admit this documented extension while still proving
WP-002's move preserved every shared line. The appended block is
delimited by the lead marker `# WP-003 — Auto-back-merge block`; the
parity test asserts the marketplace content matches everything above
that marker exactly, and that the marker introduces the only divergence.

This test is the WP-002-specific cousin of the methodology-tier shell
characterisation test at
`plugins/sulis/scripts/tests/methodology/test_release_on_merge_yaml_unchanged_behaviour.sh`.
The shell test uses PyYAML to compare the loaded steps structure; this
test does a literal text comparison after masking the three structural
adjustments.
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


def _mask_trigger(content: str) -> str:
    """Drop the top-level `on:` block. The marketplace file uses
    `on: push: branches: [main]` (3 lines); the reusable workflow uses
    `on: workflow_call:` (2 lines). Both shapes are valid GitHub
    Actions triggers; the difference is exactly the trigger remap.
    """
    # The `on:` block ends at the next top-level key (a line starting
    # with a letter at column 0, not preceded by an indent). In both
    # files the next top-level key is `concurrency:`.
    return re.sub(
        r"^on:\n(?:[ \t].*\n)+",
        "ON_BLOCK_MASKED\n",
        content,
        count=1,
        flags=re.MULTILINE,
    )


def _mask_name(content: str) -> str:
    """Mask the top-level `name:` line. The marketplace name is
    `release-on-merge`; the reusable variant adds ` (reusable)` for
    clarity in the GitHub UI. Either form is acceptable as long as
    the rest of the file is byte-identical.
    """
    return re.sub(
        r"^name:.*\n",
        "NAME_MASKED\n",
        content,
        count=1,
        flags=re.MULTILINE,
    )


def _mask_permissions(content: str) -> str:
    """Mask the job-level `permissions:` block. The marketplace file
    declares `permissions: contents: write` (2 lines, indented 4
    spaces under `release:`). The reusable workflow re-declares the
    same `contents: write`, adds `pull-requests: write`, and may
    carry inline comments (3+ lines, same indent) per TDD §5.8.
    """
    # Match a 4-space-indented `permissions:` line followed by one or
    # more 6-space-indented child lines. (`release` is 2-space indent;
    # its children are 4; the `permissions:` map's children are 6.)
    return re.sub(
        r"^    permissions:\n(?:      .*\n)+",
        "    PERMISSIONS_MASKED\n",
        content,
        count=1,
        flags=re.MULTILINE,
    )


def _mask_reusable_header_comment(content: str) -> str:
    """Strip the reusable-variant header comment block. WP-002 DoD Blue
    mandates a header comment naming the file as the reusable variant
    and pointing at the canonical shim template path — content the
    marketplace workflow does not carry. The block starts at a line
    beginning with `# REUSABLE WORKFLOW` and ends at the first blank
    line that precedes the marketplace workflow's own header comment.
    The marketplace input is unchanged (the regex doesn't match);
    the reusable input has the block removed entirely so the two
    align byte-for-byte from line 2 onward.
    """
    return re.sub(
        r"^# REUSABLE WORKFLOW.*?\n\n",
        "",
        content,
        count=1,
        flags=re.MULTILINE | re.DOTALL,
    )


def _normalise(content: str) -> str:
    return _mask_permissions(
        _mask_reusable_header_comment(_mask_name(_mask_trigger(content)))
    )


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
    # This test is a guardrail: if the marketplace file is ever moved
    # before WP-005's shim replaces it, this test will catch it.
    assert MARKETPLACE_WORKFLOW.exists(), (
        f"marketplace workflow not found at {MARKETPLACE_WORKFLOW} "
        "(it should remain in place until WP-005)"
    )


# Lead marker of the WP-003 (EXPAND-Extend) back-merge block. Everything
# above this marker in the reusable workflow is move-preserved content
# shared with the marketplace file; everything from this marker down is
# WP-003's documented extension.
_WP003_BLOCK_MARKER = "# WP-003 — Auto-back-merge block"


def _truncate_at_extension(masked_reusable: str) -> str:
    """Return the reusable workflow's masked content up to (not
    including) the WP-003 back-merge block, with any trailing blank
    separator line trimmed. This is the portion that must byte-match
    the marketplace workflow."""
    lines = masked_reusable.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.strip().startswith(_WP003_BLOCK_MARKER):
            head = lines[:i]
            # The marker sits inside a comment header (a box-rule
            # `# ────…` divider line precedes it). Back up over the
            # block's leading comment/divider lines and any blank
            # separator — they all belong to the WP-003 extension, not
            # the move-preserved prefix.
            while head and (
                head[-1].strip() == ""
                or head[-1].lstrip().startswith("#")
            ):
                head.pop()
            return "".join(head)
    # Marker absent → no extension present; the whole file is the prefix.
    return masked_reusable


def test_reusable_workflow_byte_parity_modulo_trigger_name_permissions(
    marketplace_content: str, reusable_content: str
) -> None:
    """The marketplace workflow is a byte-for-byte PREFIX of the reusable
    workflow after masking the three structural adjustments (on:, name:,
    permissions:). WP-003 appends the back-merge block below the shared
    prefix; everything above it must match the marketplace file exactly.
    """
    marketplace_masked = _normalise(marketplace_content).rstrip("\n")
    reusable_prefix = _truncate_at_extension(_normalise(reusable_content)).rstrip("\n")

    assert _WP003_BLOCK_MARKER in reusable_content, (
        "reusable workflow is missing the WP-003 back-merge block marker "
        f"{_WP003_BLOCK_MARKER!r}; the extension must be clearly delimited "
        "so the shared move-preserved prefix can be parity-checked."
    )

    if marketplace_masked != reusable_prefix:
        m_lines = marketplace_masked.splitlines()
        r_lines = reusable_prefix.splitlines()
        for i, (m, r) in enumerate(zip(m_lines, r_lines)):
            if m != r:
                pytest.fail(
                    f"prefix byte-parity differs at line {i + 1}:\n"
                    f"  marketplace: {m!r}\n"
                    f"  reusable:    {r!r}"
                )
        pytest.fail(
            "prefix byte-parity differs in line count (shared prefix): "
            f"marketplace={len(m_lines)} reusable-prefix={len(r_lines)} "
            f"(first {min(len(m_lines), len(r_lines))} lines matched). "
            "WP-003 must only APPEND below the marker, never edit moved steps."
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
    # variant carries.
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
