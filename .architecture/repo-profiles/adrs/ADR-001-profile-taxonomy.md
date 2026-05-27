---
id: ADR-001
title: Repo profile taxonomy — three profiles on the deployability axis
status: implemented in repository-contract-standard.md v0.3.0
date: 2026-05-25
author: SEA
relates_to: repository-contract-standard.md (RC v0.3.0)
supersedes: none
extends: none
---

# ADR-001 — Repo profile taxonomy

## Decision

The Repository Contract gains a **`profile`** field with exactly three
values, partitioned on a single discriminator — *"what does a release
artifact look like?"*:

- **`deployable-web-app`** — release artifact is a running service at a
  URL. Deploys to staging + production. (Today's strict contract,
  unchanged.)
- **`published-artifact`** — release artifact is a versioned package
  consumers install: npm/PyPI library, CLI tool, **Claude Code plugin
  marketplace**. Releases by publishing; health-checks by validating the
  artifact, not polling a URL.
- **`internal-tool`** — no published artifact and no server; the repo on
  `main` is the deliverable (scripts, infra-as-code, docs source).

The deployability axis names the profile. The contribution-volume axis is
a **separate** field (`contribution_model`), not part of the profile — see
ADR-002.

A repo is **either**:

- **single-artifact** — declares one `profile` from the three above
  (the common case; what RC v0.2.0 always assumed), **or**
- **multi-artifact** — declares an `artifacts:` list of N typed artifacts,
  each carrying its own type ∈ {`deployable-web-app`, `published-artifact`,
  `internal-tool`} and per-artifact config. The three profiles above are the
  **per-artifact types**; the multi-artifact model is a composition layer
  on top of them, not a fourth profile. See **ADR-004** for the composition
  semantics. This is **first-class in v0.3.0** (no longer deferred).

## Why this partition (MECE on the discriminator)

- **Mutually exclusive:** a repo's release artifact is exactly one of {a
  running service, an installable versioned package, nothing published}. A
  repo cannot be two for the same release.
- **Collectively exhaustive:** every repo the marketplace operates on
  produces one of the three. There is no fourth kind of release artifact.

The discriminator is *contract-relevant*: it is precisely the property
that determines whether RC-04 deploy/health/release workflows, RC-05
environments, RC-06 deploy secrets, and RC-08 signed tags have a literal
target.

## Alternatives considered

### Rejected: separate `marketplace` / `library` / `cli` profiles

Marketplace, library, and CLI differ in *what the package is*, but are
**identical with respect to every RC clause**: none deploys to a server,
all release by publishing a versioned artifact, all validate the artifact
instead of polling a URL. Three profiles sharing every contract clause is
a MECE violation — the partition would not be on a contract-relevant
discriminator. The package-type difference belongs in the per-project
**command slots** (`.sulis/repo-contract.yml` `commands:`), which is
exactly where the marketplace already puts its `marketplace.json`
validation today. Keeping it there honours CP-01 priority-0 (build on the
existing mechanism) and keeps the profile set minimal.

### Rejected: a single boolean `deployable: true|false`

The current hack (`deploy_target: none`) is effectively this boolean. It
cannot express `internal-tool` (no environments at all) vs
`published-artifact` (environments exist as a formality so
`environment:` resolves, but carry no deploy secrets). The two
non-deployable cases differ in RC-05 handling (N/A vs WARN) and RC-04
workflow presence (four files vs six repurposed). A boolean collapses
them; three profiles distinguish them.

### Rejected: folding volume (merge queue) into the profile axis

Deployability and contribution volume are orthogonal: a deployable web app
can be solo; a library can be high-volume OSS. Folding them would produce
a combinatorial profile set (`deployable-solo`, `deployable-team`,
`library-solo`, …) that is not MECE on any single discriminator. ADR-002
keeps volume as a separate field.

### Accepted (v0.3.0, was deferred): multi-artifact composition

A monorepo shipping **both** a deployable service **and** a published
library from one repo fits no *single* profile — but it is a real,
present shape (the founder has such a repo today). The prior proposal
deferred it (declare-dominant-or-split); that is **reversed for v0.3.0**.

Rather than add a fourth profile (which would not be MECE on the
release-artifact discriminator — a multi-artifact repo's release is *not*
a single artifact, so it cannot sit in the partition alongside the three),
v0.3.0 adds a **composition layer**: a repo declares `artifacts:` — a list
of N typed artifacts, each typed by one of the three profiles. The
partition stays MECE *per artifact*; the repo is the union of its
artifacts. RC-04/05/06/08 applicability composes across the list (a rule
applies if **any** artifact requires it), with per-artifact workflow
files and one deploy ladder per deployable artifact.

This keeps the three single-artifact profiles and their strict guarantees
untouched: a single-artifact `deployable-web-app` is byte-for-byte the
v0.2.0 contract, and a deployable artifact *inside* a multi-artifact repo
gets the identical strict deploy/health/secrets/signed-tag MUST set. See
**ADR-004** for the declaration shape, the composition rules, and the
arrival-check union semantics.

The earlier "declare the dominant artifact / split the repo" stance is
retained only as a **fallback the owner may choose**, not the required
path. Splitting is still valid; it is no longer mandatory.

## Convention alignment (CP)

Declarative per-repo config in a checked-in manifest is the dominant
convention (`package.json`, `pyproject.toml`, `Cargo.toml`, `.github/`).
We extend the repo's existing `.sulis/repo-contract.yml` rather than
inventing a new mechanism — CP-01 priority-0 (internal prior art).

## Consequences

- The marketplace repo's `profile: plugin-marketplace` migrates to
  `profile: published-artifact` (package-type detail moves to `commands:`,
  where it already lives). It is single-artifact.
- The arrival check gains a profile applicability matrix (DESIGN §7.2)
  replacing the `deploy_target == "none"` hack, **and** a union step for
  multi-artifact repos (ADR-004, DESIGN §7.4).
- A repo may now declare `artifacts:` (N typed artifacts) instead of a
  single `profile:`. The two declarations are mutually exclusive — a repo
  is single-artifact or multi-artifact, never both. ADR-004 owns the
  composition semantics.
- `deployable-web-app`'s rule set is byte-for-byte the v0.2.0 strict
  contract — the founder's non-compromise constraint is satisfied by
  construction — and a deployable artifact inside a multi-artifact repo
  inherits that same strict set (ADR-004 guarantees multi-artifact does
  not weaken it).
