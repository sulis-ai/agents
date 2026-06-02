# Misuse Cases — Discover Project

**Change:** CH-01KT1W
**Date:** 2026-06-01
**Spec reference:** `SRD.md` (Use Cases UC-001..UC-006)

Each misuse case carries an **abusive actor** (who would do it, intentionally or accidentally), an **abuse pattern** (the specific failure path), and a **System response (REQUIRED)** — the negative requirement the implementation MUST satisfy.

The system responses here are the load-bearing requirements. They flow into the TDD as Step preconditions, FailureMode recovery declarations, and drift-detector rules.

---

## MUC-001 — Founder runs discovery in non-git directory

- **Abusive actor.** A consumer who has cloned the marketplace but hasn't yet run `git init` in their consuming repo. Not malicious; an honest-mistake path.
- **Targets.** UC-001 first-time setup.
- **Abuse flow.** Consumer runs `/sulis:discover-project`. Detect phase attempts to read git remote, fails (no `.git/`). Without explicit handling, downstream steps would either crash with a cryptic error or worse — silently default `source.repo` to a garbage value and write an entity that fails drift verification two steps later.
- **System response (REQUIRED).**
  - MUST detect non-git state in the very first Detect step (`read-repo-root`).
  - MUST fail fast with the exact error: *"This directory is not a git repository. discover-project requires a git remote to mint a Project. Run `git init` and add a remote first, or specify `--source-repo <org/name>` explicitly."*
  - MUST NOT write any partial entity to disk.
  - MUST exit with non-zero status so any wrapping automation surfaces the failure.
- **Related NFRs.** NFR-004 (safety — no writes outside entity path), NFR-006 (graceful degradation).

---

## MUC-002 — Founder cancels mid-flow (partial state cleanup)

- **Abusive actor.** A consumer who's halfway through the Ask phase and decides they need to think more, switch repos, or just close the terminal.
- **Targets.** UC-005 founder-cancels-mid-flow.
- **Abuse flow.** Consumer answers Detect + Infer + half of Ask, then Ctrl-Cs. Without explicit handling, the skill might leave behind a partial `.sulis/projects/<slug>.jsonld.tmp`, a stale lock file, or — worst case — a mostly-written entity that has some inferred fields but missing the human-confirmed ones.
- **Targets.** UC-005.
- **Abuse flow.** Cancellation at any point between session start and `write-project-entity` Step completion.
- **System response (REQUIRED).**
  - MUST write the Project entity atomically — either the full entity persists or nothing does. No partial files.
  - MUST clean up any temporary files (`.tmp`, lock files, half-written drafts) on cancellation.
  - MUST be idempotent: re-running discovery after a cancellation MUST produce the same outcome as a first-time run.
  - MUST NOT leave behind a `.sulis/projects/` directory that contains anything other than fully-valid entities.
- **Related NFRs.** NFR-003 (deterministic re-run), NFR-004 (safety).

---

## MUC-003 — `.sulis/projects/<slug>.jsonld` already exists

- **Abusive actor.** A consumer running discovery a second time on a repo where it has already run successfully. Intent could be benign (re-discovery after repo evolution — that's UC-002) or accidental (forgot the entity exists).
- **Targets.** UC-001, UC-002.
- **Abuse flow.** Consumer runs `/sulis:discover-project` (without `--update`). Without explicit handling, the skill would overwrite the existing entity — destroying any consumer-customised values that don't survive the new Infer phase.
- **System response (REQUIRED).**
  - MUST detect existing entity at the target path before the Detect phase runs (cheap check).
  - MUST refuse to overwrite. Exit with: *"A Project entity already exists at `.sulis/projects/<slug>.jsonld`. To update it, run `/sulis:discover-project --update`. To start fresh, delete the existing file first."*
  - The `--update` flag activates the re-discovery diff flow (FR-009), which is the only safe overwrite path.
- **Related NFRs.** NFR-004 (safety).

---

## MUC-004 — LLM inference proposes incorrect deploy target

- **Abusive actor.** The probabilistic Infer phase itself — not malicious, just wrong. LLMs hallucinate; this is the structural counter-measure.
- **Targets.** UC-006 LLM-inference correction.
- **Abuse flow.** Infer phase reads the repo, sees a `package.json` with `"private": true`, and proposes `deploy_target: github-release`. The consumer actually publishes to a private npm registry. Without explicit handling, the inferred value would mint into the Project and the consumer wouldn't notice until their release-train invocation fails.
- **System response (REQUIRED).**
  - The `gather-ambiguous-fields` Step MUST surface every inferred value to the consumer as a confirmation prompt, not as a fait accompli.
  - The Ask phase MUST display: *"Inferred deploy_target = github-release. Confirm or override:"* — with the override path requiring a single keystroke / typed value.
  - MUST NOT mint any inferred value without explicit consumer confirmation (per FR-011).
  - The `inferred-value-rejected` FailureMode (FR-004) handles the override — recording the corrected value before Mint writes the entity.
- **Related NFRs.** NFR-003 (deterministic re-run — consumer's override survives), NFR-002 (token budget).

---

## MUC-005 — Project references a Workflow ULID not on the marketplace

- **Abusive actor.** Either a consumer who has manually edited `.sulis/projects/<slug>.jsonld` to point at a non-existent Workflow, OR a discovery bug that wrote a wrong ULID.
- **Targets.** UC-001 (mint phase), UC-002 (re-discovery).
- **Abuse flow.** The minted Project carries `release_workflow_ref: dna:workflow:01XXXXXXXXX...` that doesn't resolve to any Workflow the marketplace ships. Without the post-mint drift check (Verify phase), the consumer wouldn't discover the breakage until they invoked `/sulis:release-train` and the Workflow lookup failed.
- **System response (REQUIRED).**
  - The Verify phase (FR-008) MUST invoke the canonical drift detector on the newly-minted entity.
  - The drift check MUST validate that `release_workflow_ref` resolves to a known Workflow ULID (the marketplace's `dna:workflow:01KT0RTRA1NWFW00000000000A` per release-train).
  - If the drift check fails, the Mint MUST be rolled back (entity deleted) and the consumer sees the specific failure: *"Project references Workflow `<ulid>` which is not on the marketplace. The mint has been rolled back."*
  - The drift detector is now blocking per the `7d666df extend: tighten-drift-gate` change — this also catches the case at PR time if the entity is somehow committed.
- **Related NFRs.** NFR-005 (drift visibility).

---

## MUC-006 — Founder's repo lacks .git remote (no remote URL)

- **Abusive actor.** A consumer who has `git init`'d but hasn't added a remote (`git remote add origin ...`).
- **Targets.** UC-001 first-time setup.
- **Abuse flow.** Detect phase finds the `.git/` directory but no remote. Without explicit handling, `source.repo` cannot be inferred and the consumer sees an opaque "field missing" error at Mint time.
- **System response (REQUIRED).**
  - Detect phase MUST recognise the `git-no-remote` substate distinctly from MUC-001's `not-git` state.
  - Skill MUST surface: *"This repo has no git remote configured. discover-project cannot infer `source.repo`. Either run `git remote add origin <url>`, or specify `--source-repo <org/name>` explicitly to override."*
  - MUST NOT proceed with discovery without a resolvable `source.repo`. No defaults, no guesses.
  - MUST accept a `--source-repo <org/name>` override on the command line for cases where the consumer hasn't set the remote yet but knows the target.
- **Related NFRs.** NFR-006 (graceful degradation).

---

## MUC-007 — Monorepo collision (overwrites sibling Project entity)

- **Abusive actor.** A consumer running discovery on a monorepo's root, where one Project already exists at `.sulis/projects/backend.jsonld` and the consumer is trying to add `.sulis/projects/cli.jsonld` but invokes discovery without `--path`.
- **Targets.** UC-003 monorepo with multiple Projects.
- **Abuse flow.** Without `--path` scoping, Detect reads the whole repo, Infer proposes one Project that conflates both the backend and the CLI, Mint would write to a slug that collides with the existing sibling and overwrite it.
- **System response (REQUIRED).**
  - When `--path` is omitted AND `.sulis/projects/` already contains entities, MUST refuse to mint and surface: *"This repo already has Project entities at `.sulis/projects/`. To mint an additional Project for a sub-path, run `/sulis:discover-project --path <sub-path>`. To update an existing Project, run `/sulis:discover-project --update <slug>`."*
  - When `--path` is specified, MUST scope Detect to that sub-path only. MUST NOT read manifests or CI outside the sub-path.
  - The derived slug for the new Project MUST be unique. If it would collide with an existing sibling, MUST refuse to overwrite (same as MUC-003).
- **Related NFRs.** NFR-004 (safety — no writes outside scoped entity path).

---

## MUC-008 — Token budget exceeded on probabilistic step

- **Abusive actor.** A very large or unusual repo that pushes the Infer phase past its 10k-token budget (NFR-002). Or rate-limit / network issues that artificially inflate token costs.
- **Targets.** UC-001 first-time setup, UC-002 re-discovery.
- **Abuse flow.** Infer phase hits 10k tokens without completing the inference. Without explicit handling, the consumer either sees a half-formed inference (which they can't sensibly confirm) or a cryptic LLM-side error.
- **System response (REQUIRED).**
  - The `propose-configuration-values` Step MUST enforce the 10k token cap and detect when the budget is exceeded.
  - On exceedance, MUST surface: *"Inference exceeded the 10k token budget. Falling back to asking you for all Configuration Vocabulary fields directly."*
  - MUST then transition to a degraded Ask phase that prompts the consumer for every field the Infer phase would have populated.
  - MUST still produce a valid Project entity at the end (just with more typing for the consumer).
  - MUST log the budget-exceedance signal so the founder can pin a realistic NFR-002 number for v1.1.
- **Related NFRs.** NFR-002 (token budget), NFR-006 (graceful degradation under no LLM — same fallback path).

---

## Coverage map (use case → misuse case)

| Use Case | Misuse Cases that target it |
|---|---|
| UC-001 first-time setup | MUC-001, MUC-003, MUC-004, MUC-005, MUC-006, MUC-008 |
| UC-002 re-discovery | MUC-002, MUC-003, MUC-005, MUC-008 |
| UC-003 monorepo | MUC-007 |
| UC-004 non-git directory error | MUC-001, MUC-006 |
| UC-005 founder cancels mid-flow | MUC-002 |
| UC-006 LLM-inference correction | MUC-004 |

Every UC has at least one MUC. No "no plausible adversary" notes are required — discovery touches the filesystem (write boundary) and an external LLM (integration boundary), both of which carry plausible failure modes.

---

## Pre-mortem

**Question (asked once):** *Assume discover-project has been live for 6 months. We're in a post-incident review. What are the top 3 most likely failure causes?*

**Candidate failures (from autonomous analysis, not founder-supplied):**

1. **LLM drift / model changes.** The Infer phase produces a value that worked at v1.0 but doesn't survive a model update — consumers running discovery a year apart get inconsistent inferences. **Spec response:** NFR-003 mandates deterministic re-run on unchanged repos, but the Infer phase is probabilistic by design. The consumer-confirmation gate (FR-011) is the structural mitigation: any model-drift surfaces as a "did you mean..." prompt, never as a silent value change.
2. **Drift detector false positives.** Post-mint drift verification (FR-008) catches a legitimate consumer Project as a violation because the consumer's tenant ULID doesn't match the marketplace's. **Spec response:** OQ-4 pins the tenant derivation recipe; the drift detector treats consumer-tenant refs as a valid cross-boundary reference, not a violation. The TDD must explicitly encode this.
3. **Slug collisions in monorepos.** Two sibling Projects derive to the same slug from different sub-paths. **Spec response:** MUC-007 covers this; the TDD must specify the slug derivation function (likely: `basename(path)` lowercased + sanitised) and the collision-detection logic.

These three failures are added to the spec via NFR-003, FR-008+OQ-4, and MUC-007 respectively. The pre-mortem is recorded; no additional requirements are needed.
