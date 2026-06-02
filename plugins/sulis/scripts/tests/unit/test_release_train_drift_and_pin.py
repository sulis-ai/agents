"""Structural + parity assertions for the /sulis:release-train SKILL.md wiring.

WP-006 extends ``plugins/sulis/skills/release-train/SKILL.md`` in two
related ways, both binding to artifacts shipped by upstream WPs:

  * **Step 1 — drift-check preflight (FR-009, ADR-003, TDD §5.5 L2).**
    Before computing anything, the skill invokes WP-001's shared helper
    ``plugins/sulis/scripts/drift_check.sh``. On a non-zero exit (dev is
    behind main) the skill STOPS with a non-zero exit and points the
    operator at the recovery procedure (GIT-12). The shipped helper is
    exit 0/1 only (no ``--quiet``/``--json`` flags — WP-001 consolidated
    to those two codes), so the skill calls it bare and checks the exit
    code.

  * **Step 5 — dev-sha-at-open pin writer (FR-001, ADR-005, TDD §3).**
    Immediately *before* ``gh pr create --body-file``, the skill captures
    ``git rev-parse origin/dev`` and appends the canonical HTML-comment
    pin ``<!-- dev-sha-at-open: <40-hex-SHA> -->`` to the PR body file.

The canonical pin format is owned by TDD §3 + ADR-005 (write) / ADR-006
(read). The reusable workflow's pin-READER (WP-003) extracts it with the
anchored regex ``<!-- dev-sha-at-open: [a-f0-9]{40} -->``. The parity
test below proves the writer prose in this SKILL.md produces a body line
that the canonical reader regex recovers byte-for-byte — the producer/
consumer seam test (TDD §6.1 ``test_pin_read_parity``).

The SKILL.md is methodology prose, not executable Python, so these are
structural assertions over the prose text (grep-shaped) plus one
behavioural parity check that exercises the documented writer snippet
against the canonical reader regex.

Stdlib + pytest, Python 3.11-safe.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

# tests/unit/ -> tests/ -> scripts/ -> sulis/ -> plugins/ -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[5]
_SKILL = _REPO_ROOT / "plugins" / "sulis" / "skills" / "release-train" / "SKILL.md"
_DRIFT_HELPER = _REPO_ROOT / "plugins" / "sulis" / "scripts" / "drift_check.sh"

# The canonical pin-read regex. Source of truth: TDD §3 (Canonical
# Identifiers) + ADR-006 (pin-read mechanism, the back-merge step's
# grep -oE pattern). WP-003's reusable-workflow pin-read step uses this
# exact anchored form. The writer prose in this SKILL.md (WP-006) MUST
# produce a line this pattern captures. Asserting parity against the
# canonical source — NOT reinventing the format — is the WP Contract's
# "cite the canonical source" requirement.
CANONICAL_PIN_READ_REGEX = r"<!-- dev-sha-at-open: [a-f0-9]{40} -->"


def _skill_text() -> str:
    """Read the release-train SKILL.md. Reused by every assertion below."""
    return _SKILL.read_text(encoding="utf-8")


def test_skill_file_exists():
    """Guard: the release-train SKILL.md resolves to a real file."""
    assert _SKILL.is_file(), f"missing skill {_SKILL}"


def test_drift_helper_exists_at_canonical_path():
    """Guard: WP-001's shared helper exists at the path the skill cites.

    If this fails, the Step 1 dependency (WP-001) is not satisfied in
    this worktree — escalate rather than wiring a dangling reference.
    """
    assert _DRIFT_HELPER.is_file(), (
        f"drift_check.sh missing at {_DRIFT_HELPER}; WP-001 dependency unmet"
    )


# ---------------------------------------------------------------------
# Test 1 — Step 1 references drift_check.sh + the dev-behind-main STOP.
# ---------------------------------------------------------------------
def test_step1_invokes_drift_check_helper():
    """Step 1's preflight invokes the shared drift helper by its
    canonical path, and STOPS (exit 1) when the helper reports drift.

    ADR-003 single-source-of-truth: the skill must REFERENCE the helper
    at ``plugins/sulis/scripts/drift_check.sh`` — never copy-paste the
    ancestor-check logic into the prose. So we assert both the path and
    a non-zero exit on helper failure, and we assert the prose does NOT
    inline the helper's own ``git merge-base --is-ancestor`` command.
    """
    text = _skill_text()

    assert "plugins/sulis/scripts/drift_check.sh" in text, (
        "Step 1 preflight must reference the shared helper at its "
        "canonical path 'plugins/sulis/scripts/drift_check.sh' (ADR-003)"
    )

    # The shipped helper is exit 0/1 only — the skill calls it bare and
    # branches on the exit code, stopping with a non-zero exit on drift.
    # Match the documented guard shape: `if ! bash .../drift_check.sh; then exit 1`.
    drift_guard = re.search(
        r"if\s*!\s*bash\s+plugins/sulis/scripts/drift_check\.sh.*?\n.*?exit\s+1",
        text,
        re.DOTALL,
    )
    assert drift_guard is not None, (
        "Step 1 must call drift_check.sh bare and STOP with `exit 1` when "
        "it returns non-zero (dev behind main). Expected a guard of the "
        "shape `if ! bash plugins/sulis/scripts/drift_check.sh; then exit 1`"
    )

    # Single-source-of-truth: the helper's ancestor-check logic must NOT
    # be re-implemented inline in the skill prose (ADR-003 alternative B
    # rejected). The skill delegates; it does not duplicate.
    assert "merge-base --is-ancestor" not in text, (
        "Step 1 must DELEGATE to drift_check.sh, not inline the helper's "
        "`git merge-base --is-ancestor` logic (ADR-003 single source of truth)"
    )


def test_step1_drift_appears_before_changeset_discovery():
    """The drift preflight is the FIRST safety action — it must appear
    before Step 2 (Discover / read the changesets).

    FR-009: on drift, "do not proceed to changeset detection". Ordering
    is the guarantee — a drift check that ran *after* computing the
    manifest would have already read stale state.
    """
    text = _skill_text()
    drift_pos = text.find("plugins/sulis/scripts/drift_check.sh")
    discover_pos = text.find("## 2.")
    if discover_pos == -1:
        discover_pos = text.find("### 2.")
    assert drift_pos != -1, "drift_check.sh reference not found"
    assert discover_pos != -1, "Step 2 (Discover) heading not found"
    assert drift_pos < discover_pos, (
        "drift-check preflight must appear BEFORE Step 2 (Discover) — "
        "FR-009 forbids proceeding to changeset detection on drift"
    )


# ---------------------------------------------------------------------
# Test 2 — Step 5 writes the dev-sha-at-open pin in the canonical format.
# ---------------------------------------------------------------------
def test_step5_writes_pin_in_canonical_format():
    """Step 5 captures `git rev-parse origin/dev` and appends the
    canonical HTML-comment pin to the PR body file (ADR-005, TDD §3).
    """
    text = _skill_text()

    assert "git rev-parse origin/dev" in text, (
        "Step 5 must capture the dev SHA via `git rev-parse origin/dev` "
        "(ADR-005 — the SHA as-of PR-open, not HEAD on the release branch)"
    )

    # The literal canonical wrapper must appear in the prose, with the
    # %s / ${...} placeholder where the SHA goes. Accept either the
    # printf %s form or the shell ${VAR} interpolation form.
    pin_literal_present = (
        "<!-- dev-sha-at-open: %s -->" in text
        or re.search(r"<!-- dev-sha-at-open: \$\{?\w+\}? -->", text) is not None
    )
    assert pin_literal_present, (
        "Step 5 must append the canonical pin "
        "`<!-- dev-sha-at-open: <SHA> -->` to the PR body file (ADR-005). "
        "Expected the literal wrapper with a %s or ${VAR} SHA placeholder."
    )


def test_step5_pin_write_precedes_pr_create():
    """The pin-write prose appears BEFORE the `gh pr create --body-file`
    invocation (textual ordering).

    Reversing the order would open an unpinned PR — the workflow's
    pin-read (WP-003) would see no pin and fall to the raced path even
    on a clean release (WP-006 Notes: "eliminates the window").
    """
    text = _skill_text()

    # The pin-write site: the line that appends the canonical wrapper.
    pin_write_pos = text.find("dev-sha-at-open: %s")
    if pin_write_pos == -1:
        m = re.search(r"<!-- dev-sha-at-open: \$\{?\w+\}? -->", text)
        pin_write_pos = m.start() if m else -1
    assert pin_write_pos != -1, "pin-write prose not found in Step 5"

    # The open-for-real `gh pr create` call (the one inside the
    # without-dry-run code block, with --body-file). Find the LAST
    # occurrence of `gh pr create` that carries --body-file — that's the
    # real open call (the dry-run block shows it as an example too).
    create_positions = [m.start() for m in re.finditer(r"gh pr create", text)]
    assert create_positions, "`gh pr create` not found in SKILL.md"

    # The pin must be written before the real open call. Require that
    # there EXISTS a `gh pr create` after the pin-write (the open call)
    # and that the pin-write is before it.
    create_after_pin = [p for p in create_positions if p > pin_write_pos]
    assert create_after_pin, (
        "pin-write prose must appear BEFORE the `gh pr create --body-file` "
        "invocation — writing the pin after PR-open leaves an unpinned "
        "window (WP-006 Notes)"
    )


# ---------------------------------------------------------------------
# Test 3 — Pin-format parity against the canonical reader regex (WP-003).
# ---------------------------------------------------------------------
def test_pin_format_round_trips_through_canonical_reader_regex():
    """A SHA written through the SKILL.md writer format is recovered
    byte-for-byte by the canonical pin-read regex (ADR-006 / TDD §3 —
    the same pattern WP-003's reusable-workflow back-merge step uses).

    This is the producer/consumer seam test: WP-006 writes, WP-003
    reads, and the recovered SHA must equal the written SHA. Parity is
    asserted against the canonical source, not a reinvented format.
    """
    # A realistic 40-hex SHA (the change-branch tip, lower-cased).
    written_sha = "3a0b3175f0ff4bf5afc00569fac24bdf77f4bc9d"

    # Reconstruct the writer's body line exactly as the SKILL.md prose
    # produces it: `printf '\n\n<!-- dev-sha-at-open: %s -->\n' "$DEV_SHA"`
    # appended to an otherwise-drafted body.
    body = "Release notes here.\n"
    body += "\n\n<!-- dev-sha-at-open: %s -->\n" % written_sha

    # Read it back through the canonical reader regex (ADR-006).
    match = re.search(CANONICAL_PIN_READ_REGEX, body)
    assert match is not None, (
        "writer output did not match the canonical reader regex "
        f"{CANONICAL_PIN_READ_REGEX!r} — producer/consumer seam is broken"
    )
    recovered_sha = re.search(r"[a-f0-9]{40}", match.group(0)).group(0)
    assert recovered_sha == written_sha, (
        f"round-trip mismatch: wrote {written_sha!r}, "
        f"reader recovered {recovered_sha!r}"
    )


def test_skill_pin_literal_matches_canonical_reader_regex():
    """The exact wrapper text in the SKILL.md prose is the one the
    canonical reader regex expects — character-for-character (the space
    after the colon, the spaces inside the comment delimiters).

    Substitute a concrete SHA into the prose's `%s` placeholder and
    confirm the canonical regex matches. Catches a stray-whitespace or
    delimiter drift that the round-trip test (which builds the line from
    a Python f-string) would miss.
    """
    text = _skill_text()
    sha = "0123456789abcdef0123456789abcdef01234567"

    # Pull the literal wrapper out of the prose and substitute the SHA.
    if "<!-- dev-sha-at-open: %s -->" in text:
        rendered = "<!-- dev-sha-at-open: %s -->" % sha
    else:
        m = re.search(r"<!-- dev-sha-at-open: \$\{?(\w+)\}? -->", text)
        assert m is not None, "no recognisable pin wrapper in SKILL.md prose"
        rendered = re.sub(r"\$\{?\w+\}?", sha, m.group(0))

    assert re.fullmatch(CANONICAL_PIN_READ_REGEX, rendered), (
        f"the SKILL.md pin wrapper rendered as {rendered!r} does NOT match "
        f"the canonical reader regex {CANONICAL_PIN_READ_REGEX!r}; the space "
        "after the colon and inside the comment delimiters is part of the "
        "canonical format (TDD §3 / ADR-005 / ADR-006)"
    )


# ---------------------------------------------------------------------
# Test 4 — Cross-references to GIT-12 + ADR-005 are present.
# ---------------------------------------------------------------------
def test_skill_cross_references_git12_and_adr005():
    """The new sub-steps cite their canonical sources by anchor: GIT-12
    (the auto-back-merge invariant + manual recovery the drift STOP
    points at) and ADR-005 (the append-only pin-write discipline).
    """
    text = _skill_text()
    assert "GIT-12" in text, (
        "Step 1 drift STOP must point the operator at GIT-12's recovery "
        "procedure (the auto-back-merge invariant + manual recovery)"
    )
    assert "ADR-005" in text, (
        "Step 5 pin-write must cite ADR-005 (the append-only HTML-comment "
        "pin-write discipline)"
    )
