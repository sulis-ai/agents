"""Unit tests for the LOCAL ``ThreadStore`` adapter's redaction helper +
edge-case IO branches (CH-GJ9KQR WP-002).

The durability / append-only / redaction-on-write *behaviour* is pinned by the
shared contract test and the integration test. These unit tests pin the pure
``_scrub`` helper's edge cases (empty input, overlapping secret spans, secret-
free text) and the log reader's blank-line resilience — fast branches that
belong in the unit gate (branch-ci runs ``tests/unit/`` only).
"""

from __future__ import annotations

from pathlib import Path

from _session_manager import thread_contract as tc
from _session_manager.thread_store_local import (
    LocalThreadStore,
    _scrub,
    _scrub_value,
)

# Token-shaped fixtures are ASSEMBLED at runtime from parts so the contiguous
# provider-prefix signature never appears verbatim in committed source — this
# keeps GitHub secret-scanning push protection from flagging a synthetic test
# string as a real key, while ``find_secrets`` still detects the assembled
# value (it reports both the catalogue long-token and the provider match), so
# the redaction behaviour under test is unchanged.
_SECRET = "sk" + "_live_" + "ABCDEFGHIJKLMNOPQRSTUVWX" + "0123456789"


def test_scrub_empty_string_is_noop() -> None:
    """Empty content short-circuits — no scan, returns the empty string."""
    assert _scrub("") == ""


def test_scrub_secret_free_text_is_unchanged() -> None:
    """Text with no detected secret is returned identically (the surrounding
    content is never mangled)."""
    text = "a perfectly ordinary observation with no secrets in it"
    assert _scrub(text) == text


def test_scrub_replaces_secret_and_keeps_surrounding_text() -> None:
    out = _scrub(f"before {_SECRET} after")
    assert _SECRET not in out
    assert out.startswith("before ")
    assert out.endswith(" after")
    assert "[redacted-secret]" in out


def test_scrub_handles_overlapping_spans() -> None:
    """A bare long-token is caught by multiple overlapping detectors
    (long-token + the detect-secrets provider plugin). The coalescing walk
    redacts the widest span once; the secret never survives in a sub-span."""
    out = _scrub(_SECRET)
    assert _SECRET not in out
    assert out == "[redacted-secret]"


def test_scrub_multiple_distinct_secrets(tmp_path: Path) -> None:
    # Assembled at runtime (see _SECRET note) to dodge push-protection.
    a = "sk" + "_live_" + "A" * 24 + "1111"
    b = "ghp" + "_" + "B" * 30 + "2222"
    out = _scrub(f"{a} and {b}")
    assert a not in out and b not in out
    assert out.count("[redacted-secret]") == 2


def _msg(mid: str, order: int, content: str) -> tc.ThreadMessage:
    return tc.ThreadMessage(
        id=mid,
        participant_id="studio_agent_1",
        participant_type="studio_agent",
        content=content,
        role=None,
        created_at="2026-06-24T00:00:00Z",
        order=order,
    )


def test_append_empty_content_message_roundtrips(tmp_path: Path) -> None:
    """An empty-content message takes the ``_scrub`` empty-string fast path and
    round-trips (the empty case is not an error)."""
    store = LocalThreadStore(change_id="CH-GJ9KQR", root=tmp_path / "threads")
    store.append_message("t1", _msg("m0", 0, ""))
    assert store.get_messages("t1")[0].content == ""


def test_read_messages_tolerates_blank_lines(tmp_path: Path) -> None:
    """A stray blank line in the ``.jsonl`` log is skipped, not parsed — the
    reader is resilient to a trailing newline / hand-edit."""
    root = tmp_path / "threads"
    store = LocalThreadStore(change_id="CH-GJ9KQR", root=root)
    store.append_message("t1", _msg("m0", 0, "hello"))
    log_path = root / tc.messages_record_filename("t1")
    # Inject a blank line (the kind a trailing newline or hand-edit leaves).
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write("\n   \n")
    msgs = store.get_messages("t1")
    assert [m.id for m in msgs] == ["m0"]


# ── Finding 3 fold-in: value-pass robustness against advisory offsets ──────


# Assembled at runtime (see _SECRET note); detect-secrets matches the AKIA +
# 16-char shape, so the assembled value is still a detected secret under test.
_AWS_KEY = "AKIA" + "A" * 16


def test_scrub_redacts_detect_secrets_only_secret() -> None:
    """A detect-secrets-only secret (AWS key, not in the in-house catalogue)
    is redacted — the secret value never survives."""
    out = _scrub(f"my key is {_AWS_KEY} ok")
    assert _AWS_KEY not in out
    assert "[redacted-secret]" in out
    assert out.startswith("my key is ") and out.endswith(" ok")


def test_scrub_redacts_all_occurrences_when_offset_is_advisory() -> None:
    """When a secret appears twice, detect-secrets reports a single advisory
    offset (the first occurrence). The span pass alone would leave the second
    on disk; the exact-value pass catches every occurrence (Finding 3)."""
    out = _scrub(f"first {_AWS_KEY} then {_AWS_KEY} done")
    assert _AWS_KEY not in out, "a secret tail survived the advisory-offset span"
    assert out.count("[redacted-secret]") == 2


def test_scrub_value_recurses_dicts_and_lists() -> None:
    """``_scrub_value`` walks nested dict/list structures, scrubbing string
    leaves and leaving non-string scalars untouched (participant_context /
    metadata path)."""
    value = {
        "id": "CH-GJ9KQR",
        "count": 3,
        "flag": True,
        "none": None,
        "token": _SECRET,
        "items": [f"leak {_SECRET}", "clean", 42],
        "nested": {"deep": f"{_AWS_KEY} buried"},
    }
    out = _scrub_value(value)
    assert out["id"] == "CH-GJ9KQR"
    assert out["count"] == 3 and out["flag"] is True and out["none"] is None
    assert _SECRET not in out["token"]
    assert _SECRET not in out["items"][0] and out["items"][1] == "clean"
    assert out["items"][2] == 42
    assert _AWS_KEY not in out["nested"]["deep"]


def test_scrub_value_passes_through_scalars() -> None:
    assert _scrub_value(42) == 42
    assert _scrub_value(None) is None
    assert _scrub_value(True) is True


def test_scrub_value_scrubs_dict_keys() -> None:
    """Defense-in-depth: a secret-shaped string used as a dict KEY is scrubbed
    too (the open-ended dicts are agent-populated)."""
    out = _scrub_value({_AWS_KEY: "x", "normal": "y"})
    assert _AWS_KEY not in "".join(out.keys())
    assert "[redacted-secret]" in out
    assert out["normal"] == "y"
