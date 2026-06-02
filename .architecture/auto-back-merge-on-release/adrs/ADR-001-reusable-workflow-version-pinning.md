---
id: ADR-001
spec: auto-back-merge-on-release
title: Consumer shims pin the reusable workflow to a SemVer plugin tag by default
status: accepted
date: 2026-06-02
supersedes: null
extends: null
relates_to: [NFR-008, FR-006, MUC-006]
---

# ADR-001 — Reusable-workflow version pinning

## Context

The reusable workflow at `plugins/sulis/templates/workflows/release-on-merge.yml`
is invoked by consumers via a shim file's `uses:` directive. GitHub Actions
supports three ref forms:

- **Tag pin** — `@sulis-v0.87.0`. Consumer's release flow uses exactly that
  workflow version until they bump the pin.
- **Branch float** — `@dev` (or `@main`). Consumer's release flow always
  picks up the latest commit on that branch.
- **SHA pin** — `@<40-char-SHA>`. Most precise but no human-readable
  ergonomic.

MUC-006 (breaking change to the reusable workflow) is the load-bearing
concern: a future maintainer renames an input or changes a step. Consumers
who always-track break without warning; tag-pinned consumers stay on the
working version.

NFR-008 requires "version-pin is the default, always-track is opt-in" and
that the canonical shim template reference a SemVer tag.

## Decision

**Default to SemVer tag pin** (`@sulis-vN.M.K`) in the canonical shim
template at `plugins/sulis/templates/shims/release-on-merge.yml`. Document
`@dev` always-track as an opt-in alternative with explicit risk language in
the plugin README and in the GIT-12 worked examples (FR-008).

SHA pins are documented as "even more pinned than tag" but not recommended —
the human ergonomic loss is not worth the marginal gain over tag pins for
this use case.

## Rationale

- **CP-01 — established convention.** The dominant pattern in the GitHub
  Actions reusable-workflow ecosystem (used by Kubernetes, Argo, Helm,
  Sigstore, OpenSSF Scorecard, dozens of OSS orgs) is SemVer tag pinning.
  Always-track is a known-risky opt-in. Recommend the convention.
- **MUC-006 mitigation.** A breaking change to inputs or steps reaches
  always-track consumers immediately, with no opt-in path to adopt. Tag
  pinning makes the consumer the gatekeeper of when they upgrade.
- **SemVer 2.0.0 compliance (GIT-08).** The plugin already follows SemVer
  for the marketplace tag and the plugin tag. The same contract extends
  naturally to the reusable workflow.
- **Composes with the changeset model.** Breaking workflow changes ship as
  a major-tier changeset, which produces a major-tier plugin version, which
  becomes a major-tier tag — and tag-pinned consumers are forced to opt-in.
  Always-track consumers bypass this gate.

## Alternatives considered

### A — Branch float (`@dev`) by default

Rejected: would expose all consumers to in-flight changes on the
marketplace's `dev` branch. NFR-008 explicitly forbids this as the default.
A maintainer rebasing or pushing a fix to `dev` would silently affect every
consumer's next release run.

### B — SHA pin by default

Rejected: human ergonomics are poor (consumers reading the shim cannot
identify which plugin version they're on without a separate lookup). The
marginal robustness gain over a tag pin (tags can be re-pointed; SHAs
cannot) is not load-bearing because the marketplace maintains tags
immutably per GIT-08.

### C — `@main` as the default with `@dev` documented separately

Rejected: same problem as branch float. `main` advances on every release;
consumers tracking it experience every release as a forced upgrade.

## Consequences

- **For consumers:** Upgrading the reusable workflow is an explicit action
  (bump the `@sulis-vN.M.K` reference in the shim). It is also a
  reviewable diff in the consumer's own repo.
- **For the marketplace:** Breaking changes to the reusable workflow ship
  as a major-tier changeset. The release-train + changeset system handles
  this without modification (existing SemVer machinery).
- **For documentation:** The plugin README's shim section must show the
  tag-pinned form first, with `@dev` documented underneath as opt-in with
  a warning callout. Captured by FR-006 + FR-008.
- **For testing:** The CI smoke test (FR-013 / FR-014) uses the marketplace's
  own shim, which by definition pins to whatever tag is shipping THIS
  change. This is consistent with how the dogfood works.
