---
id: WP-005
title: Create roadmap sidecar reader + writer
status: pending
change_id: 01KT60QGXQDF3Q3QPXQ354N5Q0
kind: backend
sequence_id: WP-005
dependsOn: [WP-003]
blocks: [WP-004, WP-007]
estimated_token_cost:
  input: 5k
  output: 3k
tdd_section: Form — roadmap sidecar reader/writer; ADR-001
adrs: [ADR-001]
primitive: create
group: expand
verification:
  adapter: backend
  artifact: plugins/sulis/scripts/tests/unit/test_roadmap_sidecar.py::test_add_is_idempotent_set_semantics
---

## Context

Implements ADR-001: the Roadmap flag is a per-repo **sidecar label file**
(`.brain/labels/roadmap.jsonld`), keyed by entity id — never a field on the
entity (the vendored schemas are `unevaluatedProperties:false`, so a
`roadmap:true` field would fail validation at the adapter boundary). FR-05
(Roadmap labelling) and FR-07 (traverse lists Roadmap separately). This WP
owns both ends of the sidecar: the **writer** (`roadmap_add`, used by
capture, WP-004) and the **member reader** (`roadmap_members`, used by the
query extension, WP-007). EXPAND-Create — a tiny, self-contained file store
that travels with the repo (FR-06).

The writer lives in `_brain_capture.py` (next to its only writer, capture);
the reader lives in `_brain_query.py` (the single read seam — ADR-006).
Both share the same on-disk shape, defined once here.

## Contract

```python
# plugins/sulis/scripts/_brain_capture.py
def roadmap_add(base_dir: Path, member_ids: list[str]) -> None:
    """Append ids to .brain/labels/roadmap.jsonld 'members' (set semantics,
    sorted). Creates the file/dir if absent. Idempotent (NFR-04)."""

# plugins/sulis/scripts/_brain_query.py
def roadmap_members(base_dir: Path) -> list[str]:
    """Read .brain/labels/roadmap.jsonld → sorted member ids.
    Missing OR malformed file → [] (best-effort, NFR-01). Never raises."""
```

On-disk shape (ADR-001):
```jsonc
{ "label": "roadmap", "members": ["dna:opportunity:01J...", "dna:requirement:01J..."] }
```

Contract invariants:
- **Set semantics** — `roadmap_add` never creates duplicate members; re-adding an existing id is a no-op (NFR-04).
- **Sorted members** — diff-friendly, deterministic (ADR-001 consequence).
- **Best-effort read** — `roadmap_members` returns `[]` on missing OR malformed file; never raises (NFR-01).
- **Tolerant write** — `roadmap_add` on a malformed existing file rewrites it cleanly rather than failing (ADR-001 Armor row).
- Travels with the repo (lives under `.brain/`, FR-06).

## Definition of Done

### Red — Failing tests written
- [ ] `tests/unit/test_roadmap_sidecar.py::test_add_creates_file_on_first_call` — fresh temp dir; after `roadmap_add` the sidecar exists with the member.
- [ ] `tests/unit/test_roadmap_sidecar.py::test_add_is_idempotent_set_semantics` — adding the same id twice → one member; members sorted.
- [ ] `tests/unit/test_roadmap_sidecar.py::test_members_empty_when_file_absent` — `roadmap_members` on a dir with no sidecar → `[]`, no error.
- [ ] `tests/unit/test_roadmap_sidecar.py::test_members_empty_when_file_malformed` — sidecar containing junk → `[]`, no error (NFR-01).
- [ ] `tests/unit/test_roadmap_sidecar.py::test_add_rewrites_malformed_file` — `roadmap_add` over a malformed file produces a clean valid sidecar.
- [ ] `tests/unit/test_roadmap_sidecar.py::test_round_trip` — `roadmap_add([a,b])` then `roadmap_members` → `[a,b]` sorted.

### Green — Implementation makes tests pass
- [ ] All Red tests pass.
- [ ] Boring code: plain `json` read/write; no schema validation needed (it is a marketplace-local label, not a vendored entity).
- [ ] No module-level state; both functions take `base_dir` explicitly.

### Blue — Refactor complete
- [ ] The on-disk shape constants (`label`, filename `.brain/labels/roadmap.jsonld`) defined once and imported by both functions — no duplicated string literals across the two modules.
- [ ] No new behaviour in Blue.
- [ ] All tests green after refactor.

## Sequence
- **dependsOn:** WP-003 (`roadmap_add` is added to the `_brain_capture.py` module WP-003 creates — sequenced to avoid a same-file merge collision; `roadmap_members` is a pure addition to the pre-existing `_brain_query.py`)
- **blocks:** WP-004 (capture calls `roadmap_add`), WP-007 (query calls `roadmap_members`)
- **Parallelisable with:** WP-001, WP-002, WP-007 (WP-007's `_brain_query.py` edit is sequenced after this one via `dependsOn`)

## Estimated Token Cost
- **Input:** ~5k
- **Output:** ~3k (two small functions + test file)
- **Total:** ~8k

## Notes
- The shared shape constant is the single migration point if the Brain contract later grows first-class labels (ADR-001 consequence): the query seam is the one read point.
- Keep `roadmap_members` in `_brain_query.py` so the read seam stays the only reader of on-disk layout (ADR-006 / the query-module single-read-point discipline).

## Acceptance Evidence

- Branch: feat/wp-005-roadmap-sidecar (deleted post-merge)
- Completed: `2026-06-03T08:40:48Z` (Step 12 by calling session)
