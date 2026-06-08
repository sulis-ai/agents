# ADR-010 — Per-file diff counts ride the one sanctioned git site

- **Status:** accepted
- **Date:** 2026-06-05
- **Change:** CH-01KT50 · feature: provenance-and-origin
- **Deciders:** SEA

## Decision

Compute per-file `+N −N` diff counts with **`git diff --numstat <baseSha> --`,
added as a new function (`gitDiffNumstat`) inside `server/lib/gitShow.ts`** —
the **one** sanctioned git-spawn site — reusing the existing `runGit` runner
(spawn, `shell:false`, 5 s SIGKILL timeout, `GitError`/`TimeoutError`). The
counts are merged onto each `ChangedFile` in `readChangedFiles.ts`; binary
files (`-\t-` in numstat) map to `added: null, removed: null` (the UI shows no
count, not `+0 −0`).

## Why this is the convention

The cockpit already established (MVP ADR-005, parent §13.7) that **all** git
reads route through `gitShow.ts`. `git diff --numstat` is read-only (no
tree/index mutation) and is the canonical Git porcelain for machine-readable
line counts — the boring, established choice (CP-01). Adding it here keeps the
read-only gate's "exactly one git-spawn site" invariant literally true.

## Alternatives considered

- **A second `spawn("git")` site in `readChangedFiles.ts` (rejected).** Breaks
  the gate's one-git-site invariant; every reviewer then has to re-audit a new
  spawn. The whole value of the single site is that there is exactly one.
- **Parse `--numstat` out of the existing `--name-status` call (rejected).**
  They are different git invocations; conflating them couples the status read
  to the count read and complicates the parser. Two clean calls through one
  runner is simpler.
- **Compute counts client-side from the diff text (rejected).** The client
  never touches git or the filesystem (NFR-ARCH-01); it reads the seam only.

## Consequences

- `gitShow.ts` gains one read-only function; the gate's git allow-list is
  unchanged (still exactly one file).
- `ChangedFile` gains `added`/`removed` (nullable for binary) — a contract
  change pinned in WP-P01.
