"""Tests for `_version_pick` — the portable, numeric SemVer max helper (#49).

This helper is the shared core behind BOTH the last-resort cache-resolution
fallback (in the skill preambles + `wpx`) and the `sulis-prune-cache`
maintenance tool. It MUST rank versions numerically, never lexically, and
never via `sort -V` (BSD `sort` on macOS lacks `-V`).

The keystone regression case is the live bug from #49: with 0.98.0 and
0.126.0 both cached, a TEXT-descending sort ranks "0.98.0" above "0.126.0"
(char '9' > '1'), binding tools to a 28-versions-stale copy. `max_version`
MUST return 0.126.0.
"""

from __future__ import annotations

import _version_pick as vp


class TestMaxVersion:
    def test_regression_98_ranks_below_126(self):
        # The #49 live bug: lexical sort picks 0.98.0; numeric picks 0.126.0.
        versions = ["0.98.0", "0.122.2", "0.126.0", "0.45.0"]
        assert vp.max_version(versions) == "0.126.0"

    def test_minor_rollover_9_to_10(self):
        # 0.9.0 vs 0.10.0 — lexical ranks "0.9.0" above "0.10.0".
        assert vp.max_version(["0.9.0", "0.10.0"]) == "0.10.0"

    def test_minor_rollover_99_to_100(self):
        # 0.99.0 vs 0.100.0 — lexical ranks "0.99.0" above "0.100.0".
        assert vp.max_version(["0.99.0", "0.100.0"]) == "0.100.0"

    def test_patch_rollover(self):
        assert vp.max_version(["0.1.9", "0.1.10", "0.1.2"]) == "0.1.10"

    def test_major_dominates(self):
        assert vp.max_version(["0.999.999", "1.0.0"]) == "1.0.0"

    def test_single_version_identity(self):
        # Behaviour MUST be identical when only one version is present.
        assert vp.max_version(["0.126.0"]) == "0.126.0"

    def test_empty_returns_none(self):
        assert vp.max_version([]) is None

    def test_non_version_entries_ignored(self):
        # A cache dir may contain stray non-version names; tolerate them.
        assert vp.max_version(["latest", "0.126.0", "tmp", "0.98.0"]) == "0.126.0"

    def test_all_non_version_returns_none(self):
        assert vp.max_version(["latest", "tmp", "garbage"]) is None

    def test_duplicate_versions(self):
        assert vp.max_version(["0.126.0", "0.126.0"]) == "0.126.0"


class TestParseSemver:
    def test_parses_dotted_triple(self):
        assert vp.parse_semver("0.126.0") == (0, 126, 0)

    def test_rejects_non_numeric(self):
        assert vp.parse_semver("latest") is None

    def test_rejects_wrong_arity(self):
        assert vp.parse_semver("1.2") is None
        assert vp.parse_semver("1.2.3.4") is None

    def test_tuple_ordering_proves_numeric_compare(self):
        # The whole point: tuple compare is numeric, not lexical.
        assert vp.parse_semver("0.126.0") > vp.parse_semver("0.98.0")


class TestSortedVersionsDescending:
    def test_returns_newest_first(self):
        out = vp.sorted_versions_desc(["0.98.0", "0.126.0", "0.45.0"])
        assert out == ["0.126.0", "0.98.0", "0.45.0"]

    def test_drops_non_versions(self):
        out = vp.sorted_versions_desc(["latest", "0.10.0", "0.9.0"])
        assert out == ["0.10.0", "0.9.0"]
