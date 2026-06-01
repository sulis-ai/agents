---
id: ADR-002
title: Consumer tenant ULID derivation — SHA256("tenant-name:" + repo-org/name) → Crockford base32
status: accepted
date: 2026-06-01
deciders: [iain]
resolves: SRD Open Question 4
---

## Context

A consumer-owned Project entity carries `belongs_to_tenant` per the
foundation v0.6.0 Project schema. The marketplace's own Projects use
`dna:tenant:6XBZ93FSHN5TRX8MCS5R66FNCM` (the marketplace tenant,
derived as `SHA256("tenant-name:sulis-plugins-marketplace")` per
release-train's `failuremodes.jsonld` `_about`).

Two ways for consumer Projects to handle tenancy:

1. **Shared marketplace tenant** — every consumer Project carries the
   same tenant ULID as the marketplace. The drift detector would see
   the Workflow reference + the Project as same-tenant.
2. **Per-consumer derived tenant** — each consumer gets its own
   tenant ULID, deterministically derived from their repo URL. Cross-
   tenant references (Project → Workflow) become a recognised pattern
   the drift detector treats as a valid boundary.

Option 1 collapses the ownership model — every Project a consumer mints
would be tagged as marketplace-owned, which is semantically wrong (the
consumer owns their Project; the marketplace owns the Workflow
definition). Option 2 preserves the ownership model and makes the
cross-tenant reference (Project → Workflow) the canonical pattern for
"this entity is consumer-owned and binds to a marketplace-owned
workflow".

## Decision

**Adopt per-consumer derived tenant ULID.** Recipe:

```
input  = "tenant-name:" + <repo-org> + "/" + <repo-name>
         where <repo-org>/<repo-name> is the GitHub-shorthand form
         of source.repo (e.g., "acme/payments-app")

digest = SHA256(input)                       # 32 bytes / 256 bits

bits   = digest[:130]                        # first 130 bits, MSB-first

# Crockford base32 character set: 0123456789ABCDEFGHJKMNPQRSTVWXYZ
# (excludes I, L, O, U)
ulid26 = crockford_base32_encode(bits, length=26)

# ULID first-char clamp per ULID spec: only 0..7 are valid for the
# first character (it encodes the top 3 bits of the 48-bit timestamp
# prefix; 5 bits would overflow).
if ulid26[0] > '7':
    ulid26 = chr(ord(ulid26[0]) - 8) + ulid26[1:]

result = "dna:tenant:" + ulid26
```

The recipe is deterministic, collision-resistant, and publicly
verifiable: anyone with the consumer's repo URL can compute the same
tenant ULID. This makes cross-repo coordination (e.g., a future
"federate consumer Projects across orgs" feature) tractable without
shared registries.

The Verify phase's drift detector treats `belongs_to_tenant`
(consumer-tenant) and `release_workflow_ref` (marketplace-tenant) as a
recognised cross-tenant boundary, not a violation. WP-009 adds the
`--cross-tenant-refs-allowed-for` flag to enable this.

## Worked example

| Input | Output |
|---|---|
| `tenant-name:acme/payments-app` | `dna:tenant:<some-26-char-ulid>` (locked as a fixed-vector test in WP-002) |
| Same input run on any machine | Same output (deterministic) |

WP-002's test suite includes ≥3 fixed input-output vectors so any
future regenerate produces byte-identical ULIDs. The marketplace's own
tenant (`6XBZ93FSHN5TRX8MCS5R66FNCM`) is one of them — the recipe must
reproduce the existing marketplace tenant ULID from input
`tenant-name:sulis-plugins-marketplace`, otherwise the recipe is wrong.

## Options Considered

- **Per-consumer derived (CHOSEN).** Preserves the ownership model;
  deterministic; collision-resistant; publicly verifiable; consistent
  with the marketplace tenant's own derivation; makes cross-tenant
  references the canonical pattern.
- **Shared marketplace tenant** — rejected. Semantically wrong; a
  consumer running discovery on their own repo doesn't make their
  Project marketplace-owned.
- **Random ULID per discovery run** — rejected. Breaks
  NFR-003 (deterministic re-run); two discovery runs on the same repo
  would produce different tenant ULIDs; re-discovery (UC-002) would
  spuriously diff the tenant field.
- **Use the repo URL hash as-is (no `"tenant-name:"` prefix)** —
  rejected for consistency with the marketplace tenant recipe; the
  prefix is the marketplace's own convention and discovery follows it.

## Consequences

- **Positive:** Cross-tenant boundary becomes a first-class concept in
  the canonical entities, not an ad-hoc exception. The marketplace's
  governance (canonical Workflow ownership) and the consumer's autonomy
  (their own Project entity) are encoded in the data model. A future
  multi-org federation feature has a clean starting point.
- **Negative:** The drift detector must learn the cross-tenant-allowed
  flag. Without that extension, every consumer discovery run would
  fail the drift gate. WP-009 makes the extension small and surgical.
- **Neutral:** Consumers who care about the tenant ULID's specific
  value can compute it themselves with the published recipe. Consumers
  who don't care will never see it (it's an internal-ID concern, not
  a founder-English surface).

## Composition

This ADR encodes the recipe; WP-002 implements + tests it; WP-001
references it from the canonical entities; WP-009 extends the drift
detector to honour cross-tenant references at the Project → Workflow
edge.
