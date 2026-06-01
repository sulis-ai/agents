"""``_discovery.slug`` — deterministic slug derivation for the Mint phase.

Two recipes per TDD §Form §Slug derivation:

    slug(project_name)  = lowercase(replace(non-[a-z0-9-], "-"));
                          collapse runs of "-"; strip leading/trailing "-"
    slug(monorepo_path) = lowercase(basename(path));
                          strip a leading "@" if present (scope packages)

Slugs are the filename stem under ``.sulis/projects/<slug>.jsonld``.
Collision detection sits in the composition root (WP-008 SKILL prose);
this module exposes the pure building blocks.
"""

from __future__ import annotations

import re

# Anything outside the Crockford-friendly alnum-plus-dash set becomes "-".
_NON_SLUG_CHARS = re.compile(r"[^a-z0-9-]+")
# Collapse runs of "-" to a single "-".
_DASH_RUN = re.compile(r"-+")


# canonical:step:01KT1WDSST08WR1TEPR0JEC000  (slug derivation is part of
# the write-project-entity Step's preconditions; see TDD §Canonical
# Identifiers and §Form §Slug derivation)
def slug_from_project_name(project_name: str) -> str:
    """Derive a filesystem-safe slug from a Project's ``name`` field.

    Lowercases, replaces anything outside ``[a-z0-9-]`` with ``-``,
    collapses runs of ``-``, and strips leading/trailing ``-``.

    Examples:
        ``"Payments App"`` → ``"payments-app"``
        ``"My/Repo.v2"``   → ``"my-repo-v2"``
        ``"Acme   //  App"`` → ``"acme-app"``
    """
    lowered = project_name.lower()
    replaced = _NON_SLUG_CHARS.sub("-", lowered)
    collapsed = _DASH_RUN.sub("-", replaced)
    return collapsed.strip("-")


# canonical:step:01KT1WDSST08WR1TEPR0JEC000
def slug_from_monorepo_path(monorepo_path: str) -> str:
    """Derive a slug from a monorepo path.

    Takes the basename, lowercases, strips a leading ``@`` (which can
    appear when the path component is itself a scope-prefixed segment
    pulled from a package manager convention).

    Examples:
        ``"apps/cli"``              → ``"cli"``
        ``"packages/@scoped/foo"``  → ``"foo"``
        ``"apps/CLI"``              → ``"cli"``
    """
    basename = monorepo_path.rstrip("/").rsplit("/", 1)[-1]
    return basename.lower().lstrip("@")
