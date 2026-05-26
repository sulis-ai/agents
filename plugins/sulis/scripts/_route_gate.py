"""The routing coverage gate — no-orphan / no-duplicate / no-parse-failure.

WP-007 / TDD §7 / ADR-004. This is the routing spine's referential-integrity
check, modelled on REFERENTIAL_INTEGRITY_STANDARD (RI-01 dangling reference,
RI-02 registry drift) rather than a new validation vocabulary (CP-01). It is
**pure** — it takes already-built data structures (the inventory, the
parse_failures surfaced by WP-002, the parsed `RubricData` from WP-003) and
returns a `GateResult`. No file I/O, no ``print``, no ``sys.exit``: the
`sulis-route` CLI is the sole I/O boundary (TDD §2.2 dependency direction).

`GateResult.passed` is the AND of three clean conditions:

  * **RT-01 no orphan** (TDD §7.1): every discovered *skill* is either in the
    route-set or in `rubric.exclusions`. By construction
    `route_set = inventory − exclusions`, so a non-excluded skill is always
    routable — the orphan rule primarily catches a future break of that
    derivation invariant (closed-world, ADR-004: silence is never consent).
  * **RT-02 no duplicate** (TDD §7.2): no two inventory entries share an
    explicit invocation token.
  * **no parse_failures**: a `SKILL.md` / agent file whose frontmatter can't be
    read (surfaced by WP-002, never swallowed) forces a gate failure —
    "frontmatter is the contract" landing in Armor (§9).

It consumes WP-002's `InventoryEntry` and WP-003's `RubricData` verbatim; it
reimplements neither discovery nor rubric parsing.
"""

from __future__ import annotations

from dataclasses import dataclass

from _route_inventory import InventoryEntry
from _route_rubric import RubricData


@dataclass(frozen=True)
class GateResult:
    """The coverage-gate verdict (TDD §7.3). Immutable, hashable, explicit.

    `passed` is True iff there are no orphans AND no duplicates AND no
    parse_failures. Each failing dimension is reported with enough provenance
    to act on: orphan skill names, duplicate ``(invocation, path_a, path_b)``
    triples, and parse-failure ``(source_path, reason)`` pairs.
    """

    passed: bool
    orphans: tuple[str, ...]
    duplicates: tuple[tuple[str, str, str], ...]
    parse_failures: tuple[tuple[str, str], ...]


def _find_orphans(
    entries: list[InventoryEntry],
    route_set_names: set[str],
    exclusions: frozenset[str],
) -> tuple[str, ...]:
    """RT-01 (TDD §7.1): every discovered *skill* must be routable or excluded.

    Scoped to ``kind == "skill"`` — agents are not founder-route targets in the
    closed-world sense the orphan rule enforces. A skill that is neither in the
    route-set nor in the exclusion list is an orphan (closed-world, ADR-004).
    """
    return tuple(
        e.name
        for e in entries
        if e.kind == "skill"
        and e.name not in route_set_names
        and e.name not in exclusions
    )


def _find_duplicates(
    entries: list[InventoryEntry],
) -> tuple[tuple[str, str, str], ...]:
    """RT-02 (TDD §7.2): no two entries share an explicit invocation token.

    Reports each collision as ``(invocation, first_seen_path, colliding_path)``
    in first-seen order — deterministic, so a CI gate's output is stable
    (Armor §9).
    """
    seen: dict[str, str] = {}
    duplicates: list[tuple[str, str, str]] = []
    for e in entries:
        if e.invocation in seen:
            duplicates.append((e.invocation, seen[e.invocation], e.source_path))
        else:
            seen[e.invocation] = e.source_path
    return tuple(duplicates)


def check(
    entries: list[InventoryEntry],
    parse_failures: list[tuple[str, str]],
    rubric: RubricData,
    route_set_names: set[str] | None = None,
) -> GateResult:
    """Run RT-01 + RT-02 + the parse-failure surface; return a `GateResult`.

    Pure. ``passed = no orphans AND no duplicates AND no parse_failures``.

    ``route_set_names`` is the set of names in the derived route-set. When not
    supplied it is derived here as ``inventory − exclusions`` (the §3.4
    invariant), so the common caller (the CLI) need not pre-compute it; passing
    it explicitly lets a test drive a deliberately-broken derivation to prove
    the orphan rule fires (closed-world defence).
    """
    if route_set_names is None:
        route_set_names = {
            e.name for e in entries if e.name not in rubric.exclusions
        }

    orphans = _find_orphans(entries, route_set_names, rubric.exclusions)
    duplicates = _find_duplicates(entries)
    failures = tuple((path, reason) for path, reason in parse_failures)

    passed = not orphans and not duplicates and not failures

    return GateResult(
        passed=passed,
        orphans=orphans,
        duplicates=duplicates,
        parse_failures=failures,
    )
