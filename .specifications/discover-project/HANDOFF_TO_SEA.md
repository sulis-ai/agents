# Handoff to SEA — Discover Project

**Change:** CH-01KT1W · `change/create-discover-project` · primitive: create
**Date:** 2026-06-01
**SRD:** `.specifications/discover-project/SRD.md`
**Next command:** `/sulis:draft-architecture .specifications/discover-project/`

This handoff is intentionally specific. SEA should be able to produce the TDD without re-litigating requirements — only filling in the design choices the SRD deliberately deferred.

---

## Path A reminder

This change follows Path A exactly like `release-train-as-entities` did. Same artifact shape:

| Artifact | Purpose |
|---|---|
| `plugins/sulis/instances/discover-project/workflow.jsonld` | Canonical Workflow envelope (5-phase shape from FR-002) |
| `plugins/sulis/instances/discover-project/steps.jsonld` | Steps array (one Step per phase activity) |
| `plugins/sulis/instances/discover-project/triggers.jsonld` | Triggers per FR-003 |
| `plugins/sulis/instances/discover-project/failuremodes.jsonld` | FailureModes per FR-004 |
| `plugins/sulis/instances/discover-project/tools.jsonld` | Tool refs per FR-005 |
| `plugins/sulis/instances/discover-project/schemas/tools/*.schema.json` | Tool I/O schemas (only for new tools — most reuse from release-train) |
| `plugins/sulis/skills/<resolved-name>/SKILL.md` | Imperative skill (the conforming implementation) |
| Tests under `tests/discover-project/` | Path A test parity: drift detector test + per-Step test parity |
| Drift-detector compliance | The (now-blocking) drift detector treats discover-project the same way it treats release-train |

The closest structural precedent is `plugins/sulis/instances/release-train/`. Read it side-by-side when authoring the TDD.

---

## Five resolved decisions (founder-pinned in dispatch context)

1. **Project entity location:** `.sulis/projects/<slug>.jsonld` in the consuming repo. Pluralised path mirrors the `.sulis/changes/<id>/` convention and supports monorepos. **Do not move this.**
2. **Methodology depth:** full pass (specify → design → decompose → execute). Don't shortcut.
3. **Marketplace's own 4 Projects stay put** at `plugins/sulis/instances/release-train/projects.jsonld` (marketplace-owned). Consumer Projects go to `.sulis/projects/<slug>.jsonld` (consumer-owned). Two ownership models; two paths. This boundary is load-bearing — the drift detector must respect it.

---

## Five Open Questions for the founder (SRD-deferred)

These are surfaced in `SRD.md § Open Questions` with autonomous recommendations. SEA should pin each before producing the TDD. If the founder doesn't pin them in the design session, default to the SRD's recommendations.

| OQ | Topic | SRD's recommendation |
|---|---|---|
| OQ-1 | Skill name (`setup` vs `discover-project`) | `/sulis:discover-project` (canonical drives imperative) |
| OQ-2 | Auto-prompt on missing entity? | Fail-fast with clear error; no auto-route |
| OQ-3 | Token budget for Infer phase | Ship at 10k, instrument, adjust v1.1 |
| OQ-4 | Tenant ULID derivation for consumers | Per-consumer derived: `SHA256("tenant-name:" + repo-org-slash-name)` → Crockford base32 → 26 chars |
| OQ-5 | Re-discovery semantics | Per-field diff with explicit approval |

---

## Cross-WP identifier canonicalisation (P8 rubric)

Per `f59fc36 extend: canonicalise-cross-wp-ids`, the TDD MUST pre-canonicalise every ULID it references. Specifically:

- **Workflow ULID (discover-project):** Propose `dna:workflow:01KT1WDSCVRWFW0000000000A` (or whatever ULID format conforms — the proposed value is illustrative). Pre-canonicalise this BEFORE the decompose stage so every Step's `for_workflow` reference uses the canonical ULID from WP-001 onwards.
- **Tenant ULID (marketplace):** `dna:tenant:6XBZ93FSHN5TRX8MCS5R66FNCM` — identical to release-train; pre-canonicalised; no minting in this change.
- **Tenant ULID (consumer):** Derived per OQ-4. The derivation recipe is itself a canonical artifact — the TDD should document it once and reference it everywhere (Project entity, drift-detector rules, test fixtures). A consumer running discovery against `acme/my-app` always produces the same ULID; this is testable.
- **Step ULIDs:** One per Step in `steps.jsonld`. Use the same Crockford-base32 pattern as release-train Steps (`01KT1WDS...ST01...`). Pre-canonicalise the full set in WP-001.
- **Tool ULIDs:** New Tools (e.g., a tenant-derivation Tool if not just inline math) get new ULIDs. Reused Tools (entity-emitter, drift-detector, file-read) reference existing ULIDs from the codebase — don't mint duplicates.

The P8 rubric check will block PRs that mint ULIDs late or duplicate existing ones. Surface all ULIDs in the TDD's Form #2 (Steps table) and Form #5 (Tools table) so the rubric pass is mechanical.

---

## Skill prose convention

The skill's prose (likely at `plugins/sulis/skills/discover-project/SKILL.md` per OQ-1's recommendation) follows the existing convention:

- YAML front matter with `name`, `description`, `model` (if needed), `allowed-tools`, `skills` references.
- Body sections matching the canonical phases (Detect, Infer, Ask, Mint, Verify).
- Plain-language consumer prompts — every prompt that surfaces to a consumer must pass the FE-06 five-point check (no internal IDs, no acronyms beyond AAF-03 lexicon, no internal taxonomy).
- Failure paths from MISUSE_CASES.md mapped to FailureMode declarations in the canonical Workflow.

The drift detector will compare the skill's Step ordering and Tool bindings to `workflow.jsonld` + `steps.jsonld`. Any divergence blocks the PR. **Author the canonical first, then the skill — the skill cannot be ahead of the canonical.**

---

## Output path mkdir safety

The skill writes to `.sulis/projects/<slug>.jsonld` in the consuming repo. Per FR-007:

- MUST `mkdir -p .sulis/projects/` if missing — this is the one filesystem write outside the entity file itself that is permitted.
- MUST verify the directory creation didn't fail (permissions, etc.) before attempting the entity write.
- MUST NOT touch any other directory under `.sulis/` (e.g., `.sulis/changes/`, `.sulis/instances/`).

The atomic write semantics (write to `.tmp`, fsync, rename) per MUC-002 are a TDD-level detail — surface them in the TDD's reliability section.

---

## Tool reuse map

The TDD should reuse existing Tools where possible rather than minting new ones.

| Capability | Reuse from | Notes |
|---|---|---|
| File read | Agent harness `Read` tool | Wrap if a typed I/O schema is required for the canonical |
| Git remote read | Likely a `subprocess` call to `git remote get-url origin` | Could be a new typed Tool or just inline; founder's call |
| JSON-LD entity write | Existing entity-emitter skill (per feedback log task #58) | This is the load-bearing reuse — it's well-validated |
| Drift detector | The blocking drift detector from `7d666df extend: tighten-drift-gate` | Invoked with a scope arg to check only the new entity |
| Schema validation | Foundation v0.6.0 schemas at `plugins/sulis/brain/compiled/foundation/*.schema.json` | The Project schema is already vendored |

**New Tools to author:**
- (Possibly) a tenant-derivation Tool that takes a repo URL and outputs a ULID. Could be inline; founder's call on whether to elevate to a Tool entity.
- (Possibly) a CI-workflow parser if the Detect phase needs to discriminate GitHub Actions vs GitLab CI deeply. Likely inline.

---

## Test strategy hints (non-binding)

The TDD owns the full test strategy; these are hints from the SRD's perspective on what *must* be covered:

- **UC-001 happy path:** discovery in a synthetic git repo with a `package.json`. Asserts the entity file exists, conforms to schema, and references the marketplace's release-train Workflow ULID.
- **UC-002 re-discovery:** create a Project entity, modify the repo (add a version file), re-run with `--update`, assert the diff shows the new file and only it.
- **UC-003 monorepo:** create a multi-package repo, run discovery twice with different `--path` values, assert two sibling entities exist.
- **UC-004 non-git:** run discovery in a tempdir with no `.git/`, assert non-zero exit + specific error message + no files written.
- **UC-005 cancel:** simulate cancellation (e.g., SIGINT during Ask phase mock), assert no partial files exist on disk.
- **UC-006 override:** mock Infer to return a specific value, simulate consumer overriding it, assert the entity carries the override not the inference.
- **MUC-003 already-exists:** create entity, run without `--update`, assert refusal + no overwrite.
- **MUC-005 unknown Workflow ULID:** create entity with a bad `release_workflow_ref`, assert drift detector blocks.
- **MUC-007 sibling collision:** create entity for slug `backend`, run discovery again with `--path apps/backend` that would derive same slug, assert refusal.
- **MUC-008 token budget:** mock LLM to exceed budget, assert fallback to all-human-ask + valid entity still produced.
- **Drift detector parity:** the same drift-detector test that release-train uses, applied to discover-project's canonical + skill.

---

## What SEA should produce

1. **TDD.md** — full Technical Design Document with Form #1 (overview), Form #2 (Steps), Form #3 (Triggers), Form #4 (FailureModes), Form #5 (Tools), Form #6 (state contract), Form #7 (cross-WP identifier table per P8), Form #8 (test strategy), Form #9 (rollout).
2. **ADRs** — at minimum:
   - ADR-001: Tenant ULID derivation recipe (per OQ-4).
   - ADR-002: Skill name (per OQ-1).
   - ADR-003: Re-discovery semantics (per OQ-5).
   - ADR-004: Token budget for Infer phase (per OQ-3 — even if the value is "10k, revisit at v1.1", the ADR captures the rationale).
3. **Work packages** — atomic, Red-Green-Blue DoDs. Suggested decomposition:
   - WP-001: Canonical entities (workflow.jsonld, steps.jsonld, triggers.jsonld, failuremodes.jsonld, tools.jsonld + tool schemas).
   - WP-002: Tenant-derivation logic + test.
   - WP-003: Detect phase (deterministic steps).
   - WP-004: Infer phase (probabilistic step + token budget enforcement + fallback).
   - WP-005: Ask phase (human-gate prompts).
   - WP-006: Mint phase (atomic entity write).
   - WP-007: Verify phase (drift detector invocation).
   - WP-008: Skill prose at the resolved location.
   - WP-009: Drift detector parity tests.
   - WP-010: End-to-end dogfood test on a synthetic consumer repo.

---

## Completeness verdict

This SRD passes the structural checks (every UC has a flow, every MUC has a system response, every NFR is measurable, every term is in the glossary, every Configuration Vocabulary field traces to release-train's authoritative SRD). The Open Questions are deliberately deferred to founder pinning — they're not gaps, they're design choices the SRD shouldn't pre-empt.

**Verdict:** PASS (with 5 founder-owned Open Questions ready for pinning in the design session).

**Next:**

```
/sulis:draft-architecture .specifications/discover-project/
```
