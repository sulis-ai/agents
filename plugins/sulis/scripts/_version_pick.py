"""Portable, numeric SemVer max — the shared core of version-aware tool
resolution (#49).

Why this exists
---------------
Every sulis skill used to resolve its scripts directory by globbing the
plugin cache and `sort -r | head -1`. `sort -r` is a TEXT sort: with
``0.98.0`` and ``0.126.0`` both cached, text-descending ranks ``0.98.0``
ABOVE ``0.126.0`` (char ``'9'`` > ``'1'``), binding tools to a stale copy.

The durable fix anchors agent preambles to the active plugin version (its
``bin/`` is on ``$PATH``) and self-locates real scripts via ``realpath``.
This module backs the two places that still must compare versions:

  - the LAST-RESORT cache fallback (PATH anchor + dev fallback both miss);
  - the ``sulis-prune-cache`` maintenance tool.

It compares versions as integer tuples — never lexically, and deliberately
NOT via ``sort -V`` (BSD ``sort`` on macOS lacks ``-V``). The shell
fallbacks mirror this with a portable numeric ``sort -t. -kN,Nn``; this
module is the Python sibling and the unit-tested source of truth.

Pure stdlib leaf module — imports nothing from the rest of the toolchain.
"""

from __future__ import annotations

from collections.abc import Iterable

# A SemVer here is a strict dotted triple of non-negative integers, matching
# the plugin-cache directory names (`sulis-ai-agents/sulis/<version>/`).
Version = tuple[int, int, int]


def parse_semver(text: str) -> Version | None:
    """Parse a strict dotted-triple version string into an int tuple.

    Returns ``None`` for anything that is not exactly three dot-separated
    non-negative integers (e.g. ``"latest"``, ``"1.2"``, ``"1.2.3.4"``).
    Returning ``None`` rather than raising lets callers tolerate stray
    non-version directory names that can sit alongside real versions in a
    cache.
    """
    parts = text.split(".")
    if len(parts) != 3:
        return None
    try:
        major, minor, patch = (int(p) for p in parts)
    except ValueError:
        return None
    if major < 0 or minor < 0 or patch < 0:
        return None
    return (major, minor, patch)


def sorted_versions_desc(versions: Iterable[str]) -> list[str]:
    """Return the parseable versions, newest first, by NUMERIC order.

    Non-version entries are dropped. Ordering is by the integer-tuple key,
    so ``0.126.0`` correctly outranks ``0.98.0`` and ``0.100.0`` outranks
    ``0.99.0`` — the rollover boundaries that defeat a lexical sort.
    """
    parsed = [(parse_semver(v), v) for v in versions]
    valid = [(key, raw) for key, raw in parsed if key is not None]
    valid.sort(key=lambda pair: pair[0], reverse=True)
    return [raw for _key, raw in valid]


def max_version(versions: Iterable[str]) -> str | None:
    """Return the single newest version string, or ``None`` if none parse.

    Behaviour is identical to ``sorted_versions_desc(...)[0]`` but expresses
    the common "pick the active version" intent directly. With exactly one
    valid version present it returns that version unchanged.
    """
    ordered = sorted_versions_desc(versions)
    return ordered[0] if ordered else None


def version_skew(loaded: str | None, cached_names: Iterable[str]) -> dict:
    """Compare the LOADED plugin version against the NEWEST version cached (#125).

    A long-running session loads the plugin at one version, then a newer one
    can land in the cache while the session keeps running — so it silently
    serves stale code. This is the pure compare behind the session-start
    version-skew nudge; the CLI supplies ``loaded`` (the running script's own
    ``plugin.json`` version) and ``cached_names`` (the cache dir entries).

    Returns ``{loaded, newest, behind, determinable}``:

    - ``determinable`` is ``False`` — and ``behind`` always ``False`` — when we
      cannot make an honest comparison: ``loaded`` is ``None`` (dev / non-cache
      layout, mirrors ``_version_ok``'s conservative None handling), ``loaded``
      doesn't parse, or no cached name parses to a version. Never nudge on a
      guess.
    - ``behind`` is ``True`` only when both parse AND ``newest`` is strictly
      greater than ``loaded`` (numeric tuple compare — never lexical). Loaded
      equal-to or ahead-of the newest cached (the dev tree, a freshly-built
      version) is ``behind: False``.
    """
    newest = max_version(cached_names)
    loaded_v = parse_semver(loaded) if loaded else None
    if loaded_v is None or newest is None:
        return {"loaded": loaded, "newest": newest,
                "behind": False, "determinable": False}
    behind = parse_semver(newest) > loaded_v  # both parse here (newest from max_version)
    return {"loaded": loaded, "newest": newest,
            "behind": behind, "determinable": True}
