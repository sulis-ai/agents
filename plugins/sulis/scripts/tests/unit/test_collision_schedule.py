"""Unit tests for the collision-aware wave scheduler (#52).

The scheduler is the heart of why a central orchestrator beats agent-teams
self-claim for backlog draining: it guarantees no two parallel workers
touch the same file by computing the schedule up front from predicted
file-touch. These tests pin the two invariants — no intra-wave collision,
serialised collision groups — plus determinism + the max_parallel cap.
"""

from __future__ import annotations

from _collision_schedule import (
    _connected_components,
    schedule_collision_waves,
)


def _all_items(waves):
    return [i for w in waves for i in w]


def _wave_is_collision_free(wave, item_files):
    """No two items in a wave share a file."""
    for a in range(len(wave)):
        for b in range(a + 1, len(wave)):
            if item_files[wave[a]] & item_files[wave[b]]:
                return False
    return True


# ─── edge cases ──────────────────────────────────────────────────────────────


def test_empty_input_yields_no_waves():
    assert schedule_collision_waves({}) == []


def test_single_item_one_wave():
    waves = schedule_collision_waves({"L1": {"a.py"}})
    assert waves == [["L1"]]


def test_single_item_no_files():
    waves = schedule_collision_waves({"L1": set()})
    assert waves == [["L1"]]


# ─── parallel vs serial ──────────────────────────────────────────────────────


def test_disjoint_items_run_in_one_parallel_wave():
    item_files = {"L1": {"a.py"}, "L2": {"b.py"}}
    waves = schedule_collision_waves(item_files)
    assert len(waves) == 1
    assert set(waves[0]) == {"L1", "L2"}
    assert _wave_is_collision_free(waves[0], item_files)


def test_overlapping_items_are_serialised_oldest_first():
    item_files = {"L1": {"shared.py"}, "L2": {"shared.py"}}
    waves = schedule_collision_waves(item_files)
    assert waves == [["L1"], ["L2"]]  # serialised, insertion order


def test_anonymiser_case_four_lessons_one_file_fully_serialised():
    """The #39-#42 reality: four lessons all touching _anonymiser.py.
    They must land in ONE collision group → four serial waves, never
    parallel. This is the case I resolved by hand this session."""
    item_files = {
        "#39": {"_anonymiser.py"},
        "#40": {"_anonymiser.py"},
        "#42": {"_anonymiser.py"},
        "#41": {"_anonymiser.py"},
    }
    waves = schedule_collision_waves(item_files)
    assert waves == [["#39"], ["#40"], ["#42"], ["#41"]]
    assert all(len(w) == 1 for w in waves)


def test_transitive_overlap_groups_all_three():
    """a-b share f1, b-c share f2, a-c disjoint — but b connects them, so
    all three serialise (b touches files both a and c touch)."""
    item_files = {
        "a": {"f1.py"},
        "b": {"f1.py", "f2.py"},
        "c": {"f2.py"},
    }
    waves = schedule_collision_waves(item_files)
    # One component → one item per wave → 3 waves.
    assert len(waves) == 3
    assert all(len(w) == 1 for w in waves)
    assert _all_items(waves) == ["a", "b", "c"]


def test_components_confirmed_by_helper():
    item_files = {
        "a": {"f1.py"}, "b": {"f1.py"},   # component 1
        "c": {"f2.py"},                    # component 2
        "d": {"f3.py"}, "e": {"f3.py"},   # component 3
    }
    comps = _connected_components(item_files)
    comp_sets = sorted([sorted(c) for c in comps])
    assert comp_sets == [["a", "b"], ["c"], ["d", "e"]]


# ─── mixed: serial group alongside parallel singletons ───────────────────────


def test_mixed_serial_group_and_parallel_singletons():
    """Two overlapping (serialise) + two disjoint singletons (parallel
    with the group's items)."""
    item_files = {
        "S1": {"shared.py"}, "S2": {"shared.py"},  # serialise
        "P1": {"x.py"},                             # parallel
        "P2": {"y.py"},                             # parallel
    }
    waves = schedule_collision_waves(item_files, max_parallel=3)
    # Every wave collision-free; S1 before S2; all 4 scheduled.
    for w in waves:
        assert _wave_is_collision_free(w, item_files)
    flat = _all_items(waves)
    assert set(flat) == {"S1", "S2", "P1", "P2"}
    assert flat.index("S1") < flat.index("S2")


# ─── max_parallel cap ────────────────────────────────────────────────────────


def test_max_parallel_caps_wave_size():
    item_files = {f"L{i}": {f"f{i}.py"} for i in range(5)}  # all disjoint
    waves = schedule_collision_waves(item_files, max_parallel=3)
    assert all(len(w) <= 3 for w in waves)
    assert sum(len(w) for w in waves) == 5
    # 5 disjoint items, cap 3 → waves of 3 + 2
    assert sorted(len(w) for w in waves) == [2, 3]


def test_max_parallel_one_is_fully_serial():
    item_files = {"L1": {"a.py"}, "L2": {"b.py"}, "L3": {"c.py"}}
    waves = schedule_collision_waves(item_files, max_parallel=1)
    assert all(len(w) == 1 for w in waves)
    assert len(waves) == 3


def test_max_parallel_clamped_to_at_least_one():
    item_files = {"L1": {"a.py"}, "L2": {"b.py"}}
    waves = schedule_collision_waves(item_files, max_parallel=0)
    # clamped to 1 → fully serial, no crash
    assert all(len(w) == 1 for w in waves)
    assert _all_items(waves) == ["L1", "L2"]


# ─── invariant: NEVER an intra-wave collision (property-ish) ─────────────────


def test_no_wave_ever_has_a_collision_complex_case():
    item_files = {
        "a": {"f1.py", "f2.py"},
        "b": {"f2.py"},            # collides with a
        "c": {"f3.py"},            # disjoint
        "d": {"f3.py", "f4.py"},  # collides with c
        "e": {"f5.py"},            # disjoint
        "f": {"f1.py"},            # collides with a (transitively b)
    }
    waves = schedule_collision_waves(item_files, max_parallel=4)
    for w in waves:
        assert _wave_is_collision_free(w, item_files), f"collision in {w}"
    assert set(_all_items(waves)) == set(item_files)
