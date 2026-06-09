# fix: guard runtime IMPLEMENTATION_KINDS == vendored tool.schema.json enum

Closes #258.

## Problem

journey-rigor #207 added a `browser` driver to the runtime
`_scenario_runtime.IMPLEMENTATION_KINDS` allow-list but NOT to the vendored
`plugins/sulis/brain/compiled/foundation/tool.schema.json`
`implementation_kind` enum. Effect: a `browser`-kind foundation Tool
validated fine at the runtime layer but was REJECTED at persistence
(LocalFileEntityAdapter / schema) — a silent split-brain between the runtime
allow-list and the persistence allow-list (SF-164c3e5f, CH-01KTMA).

## State on arrival

The one-enum-value half (`browser` added to the schema enum) already landed
on `main` in the change that surfaced the lesson — runtime and schema both
carry the same 8 kinds today. What was missing is the lesson's durable ask:
a consistency check so the **next** divergence fails loudly instead of
split-braining.

## Fix

Add `tests/unit/test_implementation_kind_enum_sync.py` — a guard that asserts
the runtime `IMPLEMENTATION_KINDS` frozenset is identical to the vendored
schema's `implementation_kind` enum, naming exactly which member is missing
from which side. A future change that adds a kind to one but not the other
fails this test at CI time.

Verified: green on the current (synced) state; red with a clear message when
either side drops a member (demonstrated by temporarily removing `browser`
from the schema enum).

## Note (out of scope)

The schema's source-of-truth lives in the separate sulis-brain library; this
repo carries the *vendored compiled* copy. The guard pins the vendored copy
against the runtime. Keeping the upstream brain source in lock-step is a
brain-repo concern.
