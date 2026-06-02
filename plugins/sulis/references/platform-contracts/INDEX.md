# Platform Contracts — Index

> **Derived view.** One row per contract in this directory. This table is not
> the source of truth — each contract's own front matter is. A later
> automation can regenerate this index from those front matters (ADR-002);
> for now it is authored once and updated when a new contract lands.

## What a Platform Contract is

A Platform Contract is our outside-in, evidence-grounded record of how a
third-party platform actually behaves — the rules we must conform to, each one
tied to the platform's own documentation and (where it matters) a probe that
confirms it. It is produced by running the faithful-generation-harness against
the platform's official docs, so every claim is bound to a source rather than
assumed. See
[`../standards/PLATFORM_CONTRACT_STANDARD.md`](../standards/PLATFORM_CONTRACT_STANDARD.md)
for the claim-entry schema, the rules (PC-01..08), and the gate.

## How this index is read

- **Reuse path (FR-011).** A change that touches a platform already listed
  here treats that platform as covered — no need to re-derive the contract
  from scratch — *subject to freshness*.
- **Freshness (FR-013).** The `Oldest retrieval-date` column carries the date
  of the oldest claim in each contract. Any claim older than **180 days** is
  flagged in the `Stale?` column; a stale contract should be re-grounded
  before it is relied on again.

| Platform | Contract | Harness run | Oldest retrieval-date | Stale? (>180d) |
|---|---|---|---|---|
| GitHub Actions | [`github-actions.md`](./github-actions.md) | `01KT419R8MQBQ6BNZPXDSKZBHZ` | 2026-06-02 | No |
