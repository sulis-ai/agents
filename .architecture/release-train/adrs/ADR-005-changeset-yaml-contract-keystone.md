---
id: ADR-005
title: .changesets/README.md is the producer/consumer contract; WP-001 lands first
status: accepted
change_id: 01KSQNPBPN7W74QVAZ25F79RNH
date: 2026-05-28
---

# ADR-005 — The changeset YAML is a contract; the keystone lands first

## Decision

The changeset YAML schema is a **producer/consumer contract**. It is authored
once, in `.changesets/README.md`, alongside the deterministic helper
`_changeset.py`, and **lands first (WP-001) before any producer or consumer**.
Per CONTRACT_FIRST, the writer (WP-002) and the two readers (WP-003 GHA,
WP-004 skill) all `dependsOn` WP-001.

### The contract (YAML fields)

```yaml
change_id: 01KSQNPBPN7W74QVAZ25F79RNH   # ULID of the parent change
primitive: create                        # the 22-primitive vocabulary value
tier: minor                              # patch | minor | major (computed; overridable)
touches_plugin: true                     # bool — true when the change touches plugins/sulis/**
summary: |                               # founder-readable; assembled into the CHANGELOG
  One-or-more lines describing what changed and why.
created_at: 2026-05-28T17:30:00Z         # compact-or-ISO UTC timestamp
```

### Filename (triple-key, collision-proof)

```
{primitive}-{slug}-{datetimeZ}.yaml
```

e.g. `create-release-train-20260528T173000Z.yaml`. The triple key (primitive +
slug + UTC datetime) makes collisions across parallel changes effectively
impossible — the #64-vs-#52 conflict class is structurally gone.

## Context

Three components touch the changeset YAML: the ship flow writes it; the GHA and
the release-train skill read it. If each invented its own shape, they would
drift, and a writer/reader mismatch would silently lose changesets at release
time (the exact failure #66 is about, re-introduced one layer down). The
`WORK_PACKAGE_STANDARD.md` CONTRACT_FIRST guidance (WP-08.5) says a
producer/consumer seam gets a contract artifact first.

## Alternatives considered

1. **No written contract; each component reads/writes ad hoc (rejected).**
   *Rejected because* it guarantees drift — the bash GHA reader and the Python
   writer would diverge on field names/format and lose changesets silently.

2. **JSON Schema for the changeset (rejected for now).** A formal schema with a
   validator. *Rejected because* it's heavier than warranted for a 6-field flat
   YAML the team hand-edits occasionally; the README + `_changeset.py`'s
   `read_changesets` (which parses the README's own examples in a unit test)
   gives executable conformance without the schema-tooling tax. Convention
   Preference toward the simpler established shape (honest-claude uses a README,
   not a schema).

3. **README contract + helper module, landing first (CHOSEN).** The README is
   the human/agent-readable contract; `_changeset.py` is the executable one; the
   README's examples are validated by the helper's unit tests, so the two can't
   drift. Everything else depends on this landing first.

## Consequences

- **Positive:** single source of truth for the seam; the contract's examples are
  executable (parsed in a WP-001 unit test); writer and readers can't silently
  diverge.
- **Cost:** WP-001 is on the critical path — nothing else can ship until it
  lands. This is correct: it is the keystone.
- **Override semantics** (the `tier:` field overriding the computed tier, per
  ADR-002) are documented in the README, so an admin editing a changeset on
  `dev` knows the field is authoritative at merge time.

## Related

- ADR-002 (the tier the contract carries), ADR-003 (what the readers do with the
  tier), WP-001 (authors the contract + helper), WP-002/003/004 (the writer +
  readers that depend on it).
