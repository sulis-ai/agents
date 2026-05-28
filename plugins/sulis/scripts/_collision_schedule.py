"""Collision-aware wave scheduling for the resolve-lessons orchestrator (#52).

Given a set of work items (lessons) and the files each is predicted to
touch, produce an ordered list of *waves*. Every item in a wave is
guaranteed collision-free with every other item in that wave (they touch
disjoint files), so a wave can be dispatched in parallel. Items that DO
share a file are placed in different waves (serialised), so two workers
never edit the same file at once.

This is the mechanism that makes a central orchestrator safer than
agent-teams self-claim for backlog draining: the schedule is computed up
front from predicted file-touch, not negotiated at runtime.

Pure module — no I/O, fully deterministic (preserves caller insertion
order so the orchestrator can feed lessons oldest-first and get
oldest-first serialisation within each collision group).
"""

from __future__ import annotations


def _connected_components(
    item_files: dict[str, set[str]],
) -> list[list[str]]:
    """Group items into connected components by shared-file overlap.

    Two items are connected iff their predicted file-sets intersect;
    connectivity is transitive (a–b and b–c put a, b, c in one component
    even if a and c don't directly overlap — because serialising a and c
    is still required: b touches both). Returns a list of components,
    each an ordered list of item ids (insertion order preserved).
    """
    ids = list(item_files)  # insertion order
    parent: dict[str, str] = {i: i for i in ids}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]  # path-halving
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    # Map each file to the items touching it; union all items sharing a file.
    file_to_items: dict[str, list[str]] = {}
    for item in ids:
        for f in item_files[item]:
            file_to_items.setdefault(f, []).append(item)
    for items in file_to_items.values():
        first = items[0]
        for other in items[1:]:
            union(first, other)

    # Bucket ids by root, preserving insertion order within + across buckets.
    buckets: dict[str, list[str]] = {}
    for item in ids:
        buckets.setdefault(find(item), []).append(item)
    # Order components by their first member's insertion order (deterministic).
    return list(buckets.values())


def schedule_collision_waves(
    item_files: dict[str, set[str]],
    max_parallel: int = 3,
) -> list[list[str]]:
    """Produce collision-free waves from item → predicted-file-set.

    Guarantees:
    - **No intra-wave collision**: two items in the same wave never share
      a predicted file (each wave takes at most one item per collision
      component, and components have disjoint files).
    - **Serialised collision groups**: items that share files land in
      different waves, oldest-first (caller insertion order).
    - **Respects max_parallel**: no wave exceeds ``max_parallel`` items.

    An empty input yields ``[]``. ``max_parallel`` is clamped to ≥ 1.
    """
    if not item_files:
        return []
    cap = max(1, max_parallel)

    components = _connected_components(item_files)
    queues: list[list[str]] = [list(c) for c in components]

    waves: list[list[str]] = []
    while any(queues):
        wave: list[str] = []
        for q in queues:
            if len(wave) >= cap:
                break
            if q:
                wave.append(q.pop(0))
        if wave:
            waves.append(wave)
    return waves
