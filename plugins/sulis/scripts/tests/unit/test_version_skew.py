"""Unit tests for the version-skew detector (#125).

A long-running session can load the Sulis plugin at version X, then a newer
version Y gets installed into the cache while the session keeps running — the
session silently serves stale code (the CH-Y09VFN carry didn't fire purely
because the session ran a pre-#123 plugin). `version_skew` is the pure compare:
the version the session LOADED vs the NEWEST version present in the cache.

The function is FS-free + deterministic (the CLI does the gathering); these
tests pin the comparison exhaustively. Mirrors the #102 daemon version-skew
test discipline (`test_daemon_version_guard.py`), but for plugin-vs-cache.
"""

from __future__ import annotations

from _version_pick import version_skew


# ─── behind: the case the nudge exists to catch ───────────────────────────


def test_behind_when_a_newer_version_is_cached():
    s = version_skew("0.141.0", ["0.141.0", "0.143.0", "0.144.0"])
    assert s["loaded"] == "0.141.0"
    assert s["newest"] == "0.144.0"
    assert s["behind"] is True
    assert s["determinable"] is True


def test_behind_across_a_minor_jump():
    s = version_skew("0.98.0", ["0.98.0", "0.114.0"])  # the #49 lexical trap, numerically correct
    assert s["newest"] == "0.114.0"
    assert s["behind"] is True


# ─── current / ahead: stay silent ─────────────────────────────────────────


def test_current_when_loaded_is_the_newest():
    s = version_skew("0.144.0", ["0.141.0", "0.144.0"])
    assert s["newest"] == "0.144.0"
    assert s["behind"] is False
    assert s["determinable"] is True


def test_not_behind_when_loaded_is_ahead_of_cache():
    # Dev tree / a freshly-built version not yet pruned into the ranked set.
    s = version_skew("0.145.0", ["0.144.0", "0.143.0"])
    assert s["behind"] is False
    assert s["determinable"] is True


def test_equal_single_version_is_current():
    s = version_skew("0.144.0", ["0.144.0"])
    assert s["behind"] is False
    assert s["determinable"] is True


# ─── undeterminable: never nudge on a guess ───────────────────────────────


def test_undeterminable_when_loaded_unknown():
    # Dev / non-cache layout: plugin_version() returned None → can't compare,
    # never spuriously nudge (mirrors _version_ok's conservative None handling).
    s = version_skew(None, ["0.144.0"])
    assert s["determinable"] is False
    assert s["behind"] is False


def test_undeterminable_when_no_valid_cached_versions():
    s = version_skew("0.141.0", [])
    assert s["determinable"] is False
    assert s["behind"] is False


def test_undeterminable_when_loaded_unparseable():
    s = version_skew("not-a-version", ["0.144.0"])
    assert s["determinable"] is False
    assert s["behind"] is False


# ─── robustness: junk names in the cache dir are ignored ───────────────────


def test_ignores_non_version_cache_entries():
    s = version_skew("0.141.0", ["README", ".DS_Store", "0.144.0", "backup"])
    assert s["newest"] == "0.144.0"
    assert s["behind"] is True


def test_all_junk_cache_is_undeterminable():
    s = version_skew("0.141.0", ["README", "tmp"])
    assert s["determinable"] is False
    assert s["behind"] is False
