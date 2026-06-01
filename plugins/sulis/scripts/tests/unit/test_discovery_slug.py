"""Tests for ``_discovery.slug`` — slug derivation helpers.

Covers TDD §Form §Slug derivation (project_name + monorepo_path).
Slugs are deterministic and the building block on which Mint's
collision-detection logic (TDD §Armor; MUC-007) rests.
"""

from __future__ import annotations

from _discovery.slug import slug_from_monorepo_path, slug_from_project_name


class TestSlugFromProjectName:
    def test_slug_from_project_name_lowercases(self) -> None:
        """``Payments App`` → ``payments-app`` — basic lowercase + space."""
        assert slug_from_project_name("Payments App") == "payments-app"

    def test_slug_from_project_name_replaces_special_chars(self) -> None:
        """Non-[a-z0-9-] is replaced by ``-``."""
        assert slug_from_project_name("My/Repo.v2") == "my-repo-v2"

    def test_slug_from_project_name_collapses_runs(self) -> None:
        """Runs of separator chars collapse to a single ``-``."""
        assert slug_from_project_name("Acme   //  App") == "acme-app"

    def test_slug_from_project_name_strips_leading_trailing_hyphens(self) -> None:
        """Leading/trailing hyphens are stripped after replacement."""
        # `.foo.` → all dots → hyphens → `-foo-` → stripped → `foo`
        assert slug_from_project_name(".foo.") == "foo"


class TestSlugFromMonorepoPath:
    def test_slug_from_monorepo_path_basename(self) -> None:
        """``apps/cli`` → ``cli`` — basename only, lowercased."""
        assert slug_from_monorepo_path("apps/cli") == "cli"

    def test_slug_from_monorepo_path_strips_scope(self) -> None:
        """``packages/@scoped/foo`` → ``foo`` — basename strips ``@`` scope dir."""
        assert slug_from_monorepo_path("packages/@scoped/foo") == "foo"

    def test_slug_from_monorepo_path_lowercases(self) -> None:
        """Basename is lowercased."""
        assert slug_from_monorepo_path("apps/CLI") == "cli"


class TestSlugDeterminism:
    def test_slug_is_deterministic(self) -> None:
        """100 invocations of the same input return byte-identical output."""
        results_name = {slug_from_project_name("Payments App") for _ in range(100)}
        results_path = {slug_from_monorepo_path("apps/cli") for _ in range(100)}
        assert results_name == {"payments-app"}
        assert results_path == {"cli"}
