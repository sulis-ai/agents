"""Cache-pruning core — defence-in-depth against stale-version pileup (#49).

The version-resolution fix (PATH anchor + self-location) stops tools binding
to a stale cached copy. This is the belt-and-braces companion: keep only the
newest N cached ``sulis-ai-agents/sulis/<version>`` directories so old
versions cannot accumulate to bite a mis-resolution in the first place.

Pure logic lives here so it can be unit-tested against a fake cache under
``tmp_path``; the thin ``sulis-prune-cache`` CLI wraps it. Version ordering
reuses ``_version_pick`` — the SAME portable numeric comparison the
resolution fallbacks use (never lexical, never ``sort -V``).
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

import _version_pick as vp

# Default number of versions to retain. The active version plus a small margin
# for in-flight rollbacks — boring and conservative.
DEFAULT_KEEP = 3

# The cache subpath that holds versioned plugin installs.
_SULIS_SUBPATH = ("sulis-ai-agents", "sulis")


@dataclass(frozen=True)
class PrunePlan:
    """What a prune WOULD do. ``keep``/``remove`` are version strings,
    newest-first within ``keep``. ``sulis_dir`` is the parent holding the
    version directories (may not exist)."""

    sulis_dir: Path
    keep: list[str]
    remove: list[str]


def default_cache_root() -> Path:
    """The real Claude Code plugin cache root (``~/.claude/plugins/cache``)."""
    return Path.home() / ".claude" / "plugins" / "cache"


def plan_prune(cache_root: Path, keep: int = DEFAULT_KEEP) -> PrunePlan:
    """Compute which cached sulis versions to keep vs remove.

    Versions are ranked NUMERICALLY (via ``_version_pick``); the newest
    ``keep`` are retained, the rest are marked for removal. Non-version
    directory names are ignored entirely. A missing cache yields an empty
    plan (nothing to do).
    """
    sulis_dir = cache_root.joinpath(*_SULIS_SUBPATH)
    if not sulis_dir.is_dir():
        return PrunePlan(sulis_dir=sulis_dir, keep=[], remove=[])

    names = [p.name for p in sulis_dir.iterdir() if p.is_dir()]
    ordered = vp.sorted_versions_desc(names)  # newest-first, non-versions dropped
    keep_n = max(keep, 0)
    return PrunePlan(
        sulis_dir=sulis_dir,
        keep=ordered[:keep_n],
        remove=ordered[keep_n:],
    )


def apply_prune(plan: PrunePlan, force: bool = False) -> list[str]:
    """Return the versions removed (or, in dry-run, that WOULD be removed).

    Dry-run is the default (``force=False``): the function reports
    ``plan.remove`` and leaves disk untouched. With ``force=True`` it deletes
    each removable version directory before returning the same list.
    """
    if not force:
        return list(plan.remove)
    for version in plan.remove:
        shutil.rmtree(plan.sulis_dir / version, ignore_errors=True)
    return list(plan.remove)
