"""Unit tests for the single WP status vocabulary (L-03).

Before L-03 there were four spellings of "ready to start": WP-07 said `todo`,
the plan-work template + wpx-index + orchestrator said `pending`, and
`_lib.wp_index` defaulted to `todo` AND bucketed any UNKNOWN status as "ready".
That last fallback is the bug: a WP with a drifted status (`ready`) looked
fine in the INDEX but was invisible to `list-ready` (which counts only
`pending`).

L-03 splits the concern into two sets with two different jobs:

  * WRITE path (strict) — `_wpxlib.CANONICAL_WP_STATUSES` + `validate_wp_status`.
    A WP being added/decomposed MUST use the canonical word `pending`; `ready`
    and `todo` are rejected loudly so drift fails surgically at add time
    instead of vanishing silently.
  * READ path (lenient) — `_lib.wp_index.STATUS_BUCKETS` tolerates
    `pending`/`todo`/`ready` in the ready bucket so any pre-existing legacy
    file still surfaces correctly rather than via the silent UNKNOWN fallback.
"""

from __future__ import annotations

import sys
from pathlib import Path

# _wpxlib is on sys.path via conftest; _lib.wp_index lives under plugins/sulis,
# so add that dir too (the scripts/ dir is .../plugins/sulis/scripts).
_PLUGIN_ROOT = Path(__file__).resolve().parents[3]  # .../plugins/sulis
if str(_PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_ROOT))

from _wpxlib import (  # noqa: E402
    CANONICAL_WP_STATUSES,
    WP_STATUS_READY,
    validate_wp_status,
)

from _lib.wp_index import STATUS_BUCKETS, WPSummary, bucket_wps  # noqa: E402


# ─── WRITE path: validate_wp_status (strict canonical vocabulary) ───────────


def test_canonical_ready_word_is_pending():
    assert WP_STATUS_READY == "pending"
    assert "pending" in CANONICAL_WP_STATUSES


def test_validator_accepts_pending():
    assert validate_wp_status("pending") is None


def test_validator_rejects_ready():
    # `ready` was never a canonical word anywhere; accepting it is what let a
    # WP slip past list-ready unnoticed.
    msg = validate_wp_status("ready")
    assert msg is not None
    assert "ready" in msg
    assert "pending" in msg  # the message names the canonical word


def test_validator_rejects_todo():
    # `todo` is tolerated on the READ path (buckets) but not on the WRITE path:
    # new WPs must use `pending`.
    assert validate_wp_status("todo") is not None


def test_validator_rejects_typo():
    assert validate_wp_status("pendign") is not None
    assert validate_wp_status("") is not None


def test_validator_accepts_full_lifecycle_and_train_states():
    for status in [
        "in_progress", "blocked", "dependency_blocked", "sleeping",
        "step-7-complete", "step-7-held", "step-7-blocked",
        "done", "closed", "regressed", "abandoned", "cancelled", "auto-draft",
    ]:
        assert validate_wp_status(status) is None, f"{status} should be valid"


def test_validator_is_case_and_whitespace_insensitive():
    assert validate_wp_status("  PENDING ") is None


def test_canonical_set_excludes_read_path_aliases():
    # The strict write vocabulary must NOT contain the lenient aliases — that
    # separation is the whole point of L-03.
    assert "todo" not in CANONICAL_WP_STATUSES
    assert "ready" not in CANONICAL_WP_STATUSES


# ─── READ path: _lib.wp_index buckets tolerate the aliases ──────────────────


def _ready_bucket_statuses() -> list[str]:
    for key, _label, statuses in STATUS_BUCKETS:
        if key == "ready":
            return statuses
    raise AssertionError("no 'ready' bucket in STATUS_BUCKETS")


def test_ready_bucket_tolerates_pending_todo_ready():
    statuses = _ready_bucket_statuses()
    assert "pending" in statuses
    assert "todo" in statuses
    assert "ready" in statuses


def _wp(status: str) -> WPSummary:
    return WPSummary(wp_id="WP-001", title="t", kind="backend",
                     source="manual", status=status)


def test_pending_wp_buckets_as_ready_not_via_unknown_fallback():
    # The L-03 regression: a `pending` WP must land in ready by MATCH, so a
    # genuinely-unknown status can still be distinguished. We assert all three
    # aliases land in ready.
    for status in ("pending", "todo", "ready"):
        buckets = bucket_wps([_wp(status)])
        assert len(buckets["ready"]) == 1, f"{status} should bucket as ready"
