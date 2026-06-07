# ADR-013 — Origin is stamped in the write paths (executor + relay), not the cockpit

- **Status:** accepted (mechanism); **founder confirmation requested** on trailer-vs-sidecar
- **Date:** 2026-06-05
- **Change:** CH-01KT50 · feature: provenance-and-origin
- **Deciders:** SEA

## Context

To turn **inferred** origin (ADR-012) into **recorded** fact, origin must be
stamped at write time. But the cockpit is **provably read-only** (ADR-003): it
must not write. The question the brief raises directly: does origin-stamping
need an ADR-003 amendment, since stamping writes commit metadata?

## Decision

**Stamping happens in the two existing write paths — the executor's commit and
the chat-relay's commit — NOT in the cockpit read surface.** Concretely:

- When the **executor** commits autonomous work, it appends a Conventional-
  Commits **trailer**: `Sulis-Origin: autonomous; run=<lifecyclerun-ulid>;
  confidence=<0..1>`.
- When the **chat relay** commits assisted work, it appends:
  `Sulis-Origin: assisted; conversation=<id>; turn=<n>`.

The stamp is **append-only metadata on a commit the path is already making** —
no new commit, no new process, no network, nothing published. A stamp **failure
is non-fatal**: the commit still lands and origin falls back to the inferred
path (graceful degradation). Where a trailer can't be written, a **sidecar**
fallback (`.sulis/origin/<sha>.json`) is used.

**The cockpit read-only guarantee is untouched** — stamping lives in
`apps/`/executor + relay code **outside** `apps/cockpit/`, so
`check-read-only.sh` (which scans only `apps/cockpit/`) needs **no change** and
**ADR-003 needs no amendment**. The cockpit only ever *reads* the stamp
(`RecordedOriginAttribution`).

## Why the trailer is the convention (recommended; CP-01)

A **git commit trailer** is the established, boring convention for structured
commit metadata (the same family as `Co-Authored-By:` / `Signed-off-by:` — RFC-
style trailers, used by Git itself, GitHub, the kernel). It is greppable
(`git log --grep` / `git interpret-trailers`), travels with the commit through
clones and rebases, and needs no second store. This repo already mandates a
`Co-Authored-By:` trailer on commits — `Sulis-Origin:` rides the same mechanism.

## Alternatives considered

- **Stamp from the cockpit (rejected).** Would force the cockpit to write commit
  metadata, breaking the read-only guarantee and requiring an ADR-003 amendment.
  The cockpit is the wrong place — it observes; the executor/relay act.
- **A separate origin store/database (rejected).** A second source of truth that
  can drift from the commits and violates NFR-DATA-01. The commit *is* the
  natural home for "who made this commit and why".
- **Sidecar-only (no trailer) (offered as the founder alternative).** Writes
  `.sulis/origin/<sha>.json` and never touches the commit message. More
  conservative (no commit-message change at all) but loses the travels-with-the-
  commit and greppability properties and adds files to track. Recommended only
  if the founder wants commit messages untouched.
- **Amend ADR-003 to allow a cockpit write (rejected).** Unnecessary — stamping
  doesn't belong in the cockpit at all.

## Consequences

- Two small write-side additions (executor + relay trailer writers), each with a
  stamp-failure-is-non-fatal test. Outside `apps/cockpit/` → no cockpit gate
  change.
- Every future autonomous/assisted commit carries an origin trailer — a
  **behaviour change to how the agent commits**, surfaced as the founder-owned
  question in TDD §10.1.
- Once stamping lands, `RecordedOriginAttribution` reads the trailer and the
  badge flips inferred → recorded with no UI change (ADR-012).
