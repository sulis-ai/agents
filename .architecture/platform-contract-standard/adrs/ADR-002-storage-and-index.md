---
id: ADR-002
title: Where platform contracts live and how they are indexed for reuse
status: accepted
date: 2026-06-02
change: platform-contract-standard
relates-to: [FR-010, FR-011, NFR-006, UC-002, "SRD:OpenQuestion-1"]
---

# ADR-002 — Platform contracts: storage location and reuse index

## Decision

Platform Contracts live in **`plugins/sulis/references/platform-contracts/<platform>.md`**,
one file per platform, version-controlled and durable across changes. The
directory carries an **`INDEX.md`** — a flat table of
`{platform, contract-path, claims-count, oldest-retrieval-date, last-harness-run}`.

The reuse mechanism is **directory-scan-plus-index**: the gate (and the P-PLAT
rubric phase) resolves a platform name to a contract by checking for
`platform-contracts/<platform>.md`. The `INDEX.md` exists for human review and
for the freshness sweep (ADR-003) — it is a generated convenience, not the
source of truth. The **file's existence** is the authoritative "is this platform
covered?" signal; `INDEX.md` is regenerated from the directory, never
hand-maintained as the primary record.

## Platform-name normalisation

`<platform>` is a lowercase, hyphenated slug (`github-actions`, `stripe`,
`aws-s3`). The standard records the slug convention so the gate's
name→file lookup is deterministic. A change names the platform in its SRD;
the gate slugifies and looks up.

## Why

- **CP-01 internal prior art.** The marketplace already stores durable reference
  material under `plugins/sulis/references/` (standards, the rubric). Platform
  contracts are reference material of the same kind — they belong in the same
  tree. The dispatch and FR-010 both name this location; no novelty is warranted.
- **File-existence as the cover signal is the simplest correct mechanism.** It
  needs no parser, no registry write-path, no consistency protocol between a
  manifest and the files. The rubric P-PLAT check is a single `test -f`-shaped
  lookup (NFR-006 measurable: a second change touching a covered platform
  triggers zero new full harness runs — the file is simply found).
- **INDEX.md is a derived view, so it cannot drift into a second source of
  truth.** Regenerating it from the directory keeps the REFERENTIAL_INTEGRITY
  discipline (no two authorities for "what contracts exist").

## Alternatives considered

- **A hand-maintained manifest file as the source of truth.** Rejected: a manifest
  that must be edited alongside every new contract is a second authority that
  drifts (a contract file added without the manifest entry, or vice versa). The
  REFERENTIAL_INTEGRITY_STANDARD already warns against mirror drift. Directory
  scan removes the drift class entirely.
- **A database / SQLite registry** (mirroring the change-store). Rejected:
  over-engineered for a handful of version-controlled markdown files that humans
  must review by reading. Contracts are reviewed in PRs, not queried at runtime;
  a DB adds a moving part with no reviewability benefit and breaks the
  "reviewable, version-controlled" requirement (NFR-003).
- **Per-change throwaway contracts** (co-located with the change's
  `.architecture/`). Rejected explicitly by the dispatch and FR-011 — contracts
  are *durable and reused*, not regenerated per change. A per-change contract
  would re-incur the full harness cost every time and accrue no shared knowledge.
