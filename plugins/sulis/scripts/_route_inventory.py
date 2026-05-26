"""Value objects + auto-discovered inventory for the routing spine.

The domain core (TDD §3, §4.1; ADR-001). Auto-discovery means a skill or agent
lands in the inventory simply by existing on disk with parseable frontmatter —
there is no hand-maintained list to drift (ADR-001).

Dependency direction (hexagonal-lite, TDD §2.2): the domain functions
(`build_inventory`, `derive_invocation`, `route_set`) are **pure** — they take
already-parsed data and return data structures, with no file I/O, no ``print``,
no ``sys.exit``. The single filesystem adapter is ``discover``, a thin glob +
read. This split is what lets the domain be unit-tested without a fixture
filesystem (via the source-tuple form) while ``discover`` is proven against a
real fixture tree.

The reader is WP-001's ``_route_frontmatter.parse_frontmatter`` (folded scalars
+ nested ``routes_to`` mappings). This module never reimplements frontmatter
parsing — it consumes that contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from _route_frontmatter import FrontmatterError, parse_frontmatter

# The marketplace invocation convention: a skill named ``X`` is invoked as
# ``/sulis:X``. Centralised so the prefix has exactly one definition.
_SKILL_INVOCATION_PREFIX = "/sulis:"

# The orchestrator agent is the only place ``routes_to:`` lives (TDD §3.1).
# Its frontmatter ``name`` identifies it; nothing else carries routes.
_ORCHESTRATOR_NAME = "sulis"


@dataclass(frozen=True)
class Route:
    """One declared ``routes_to`` entry (orchestrator agent only)."""

    slug: str
    description: str
    triggers: tuple[str, ...]


@dataclass(frozen=True)
class InventoryEntry:
    """One discovered skill or agent."""

    name: str
    kind: str  # "skill" | "agent"
    invocation: str  # "/sulis:<name>" (skill) | "<name>" (agent)
    description: str
    source_path: str  # repo-relative provenance for errors
    # Populated only for the orchestrator agent; () for every other entry.
    routes: tuple[Route, ...] = field(default=())


def derive_invocation(name: str, kind: str) -> str:
    """Compute the explicit invocation token for a discovered entry.

    Skill ``foo`` -> ``/sulis:foo``; agent ``bar`` -> ``bar``. This is the
    single authority for invocation derivation (TDD §3.1) — it keys off the
    frontmatter ``name``, never a directory name (TDD §7.5#2). Nothing else in
    the codebase computes invocations.
    """
    if kind == "skill":
        return f"{_SKILL_INVOCATION_PREFIX}{name}"
    return name


def discover(repo_root: Path) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Thin filesystem adapter — the ONLY file I/O in this module.

    Walks ``plugins/sulis/skills/*/SKILL.md`` and ``plugins/sulis/agents/*.md``
    under a resolved ``repo_root`` (path safety, Armor §9: globs are scoped
    under the resolved root, no traversal outside the repo). Returns
    ``(skill_sources, agent_sources)`` where each is ``[(source_path, raw_text),
    ...]`` and ``source_path`` is repo-relative. Output is sorted for
    deterministic ordering (a CI gate must be deterministic, Armor §9).
    """
    root = Path(repo_root).resolve()
    base = root / "plugins" / "sulis"

    skill_sources = _read_sorted(root, base.glob("skills/*/SKILL.md"))
    agent_sources = _read_sorted(root, base.glob("agents/*.md"))
    return skill_sources, agent_sources


def _read_sorted(root: Path, paths) -> list[tuple[str, str]]:
    """Read each file, returning ``[(repo_relative_path, text), ...]`` sorted by
    path. Reading is the I/O boundary; parse failures surface later in the pure
    layer, so a read here is a plain text read.
    """
    out: list[tuple[str, str]] = []
    for p in paths:
        rel = p.resolve().relative_to(root).as_posix()
        out.append((rel, p.read_text(encoding="utf-8")))
    out.sort(key=lambda pair: pair[0])
    return out


def build_inventory(
    skill_sources: list[tuple[str, str]],
    agent_sources: list[tuple[str, str]],
) -> tuple[list[InventoryEntry], list[tuple[str, str]]]:
    """Build the inventory from already-read sources. Pure (no I/O).

    Returns ``(entries, parse_failures)``. A source whose frontmatter cannot be
    parsed, or has no ``name`` key, becomes a ``parse_failure`` tuple
    ``(source_path, reason)`` — surfaced, never swallowed ("frontmatter is the
    contract", TDD §4.1 / Armor §9). No bare ``except``.
    """
    entries: list[InventoryEntry] = []
    parse_failures: list[tuple[str, str]] = []

    for source_path, raw_text in skill_sources:
        _build_one(source_path, raw_text, "skill", entries, parse_failures)
    for source_path, raw_text in agent_sources:
        _build_one(source_path, raw_text, "agent", entries, parse_failures)

    return entries, parse_failures


def _build_one(
    source_path: str,
    raw_text: str,
    kind: str,
    entries: list[InventoryEntry],
    parse_failures: list[tuple[str, str]],
) -> None:
    """Parse one source into an entry, or record a structured parse_failure."""
    try:
        mapping, _body = parse_frontmatter(raw_text)
    except FrontmatterError as exc:
        parse_failures.append((source_path, f"frontmatter error: {exc}"))
        return

    name = mapping.get("name")
    if not name or not isinstance(name, str):
        # "frontmatter is the contract" — a missing/unreadable name is a
        # surfaced failure, not a silent skip (TDD R5).
        parse_failures.append((source_path, "frontmatter has no parseable 'name'"))
        return

    description = mapping.get("description", "")
    if not isinstance(description, str):
        description = ""

    # routes_to lives ONLY on the orchestrator agent (TDD §3.1). Every other
    # entry gets an empty routes tuple. Keeping the special-case explicit and
    # narrow is deliberate (WP Notes): one entry, one place routes_to is read.
    routes: tuple[Route, ...] = ()
    if kind == "agent" and name == _ORCHESTRATOR_NAME:
        routes = _build_routes(mapping.get("routes_to"))

    entries.append(
        InventoryEntry(
            name=name,
            kind=kind,
            invocation=derive_invocation(name, kind),
            description=description,
            source_path=source_path,
            routes=routes,
        )
    )


def _build_routes(routes_to: object) -> tuple[Route, ...]:
    """Turn the parsed ``routes_to`` list-of-mappings into a ``Route`` tuple.

    The WP-001 reader yields ``routes_to`` as ``list[dict]`` with ``slug`` /
    ``description`` / ``triggers`` keys. A malformed or absent block yields an
    empty tuple — routes are optional enrichment, never required (TDD §3.1).
    """
    if not isinstance(routes_to, list):
        return ()

    routes: list[Route] = []
    for item in routes_to:
        if not isinstance(item, dict):
            continue
        slug = item.get("slug", "")
        description = item.get("description", "")
        triggers = item.get("triggers", [])
        triggers_tuple = tuple(triggers) if isinstance(triggers, list) else ()
        routes.append(
            Route(slug=slug, description=description, triggers=triggers_tuple)
        )
    return tuple(routes)


def route_set(
    entries: list[InventoryEntry], exclusions: frozenset[str]
) -> list[InventoryEntry]:
    """The derived closed route-set: ``inventory − exclusions`` (TDD §3.4).

    Pure, stateless. Single source, no drift: the route-set is always computed
    from the inventory minus the explicitly-excluded names, never hand-listed.
    """
    return [e for e in entries if e.name not in exclusions]
