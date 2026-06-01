# Glossary — Discover Project

**Change:** CH-01KT1W
**Date:** 2026-06-01
**Status:** locked (vocabulary frozen for artifact generation)

Every term in this glossary is the **preferred form**. Synonyms appear in the `Also Known As` column with deprecated status. The `NOT the Same As` column distinguishes terms that sound similar but mean different things.

## Preferred terms

| Term | Definition | Also Known As (deprecated) |
|---|---|---|
| **Consuming repo** | A fork-consumer's own repository, distinct from the marketplace itself. The repo in which discovery runs. | "consumer repo", "fork repo", "downstream repo" |
| **Marketplace** | The Sulis AI Claude Code plugin marketplace (this repo: `sulis-ai/agents`). The source of canonical Workflow definitions. | "the source", "upstream", "the template" |
| **Discovery** | The act of running the discover-project Workflow. Always refers to the workflow execution, never the Detect phase alone. | "setup" (deprecated in spec context; `setup` may be a skill alias per OQ-1) |
| **Discovery run** | One execution of the Workflow, from session start through Mint to Verify (or to a failure exit). | "discovery session", "discovery invocation" |
| **Project entity** | The canonical output of discovery: a JSON-LD file at `.sulis/projects/<slug>.jsonld` conforming to the foundation v0.6.0 Project schema. | "Project instance", "Project record", "Project file" |
| **First-time setup** | A discovery run in a repo with no existing Project entity. Triggered by `/sulis:discover-project` without `--update`. | "initial discovery", "fresh discovery" |
| **Re-discovery** | A discovery run in a repo with an existing Project entity. Uses `--update`. Produces a per-field diff. | "update", "refresh" |
| **Monorepo Project** | A Project entity for one of multiple release units in a single consuming repo. Scoped via `--path <sub-path>`. | "sub-project" (avoid — too generic) |
| **Configuration Vocabulary** | The authoritative list of Project entity fields defined in the release-train SRD. See `.specifications/release-train-as-entities/SRD.md#configuration-vocabulary`. | n/a |
| **Detect phase** | The first of the five canonical phases. Reads filesystem state deterministically. Produces inputs for Infer. | n/a |
| **Infer phase** | The single probabilistic phase. Reads Detect's outputs, proposes values for ambiguous fields. Token-bounded per NFR-002. | "inference phase", "LLM phase" |
| **Ask phase** | The human-gated phase between Infer and Mint. Consumer confirms or overrides every inferred value and supplies the truly-ambiguous fields. | "human phase", "confirmation phase" |
| **Mint phase** | The deterministic phase that writes the Project entity to `.sulis/projects/<slug>.jsonld`. | "write phase", "creation phase" |
| **Verify phase** | The final phase. Runs the canonical drift detector on the just-minted entity. | "verification", "drift check" |
| **Drift detector** | The blocking CI gate from `7d666df extend: tighten-drift-gate`. Compares canonical Workflow definition to imperative implementation; fails PRs on divergence. | "drift gate", "drift verification" |
| **Path A** | The execution model: canonical entities are the spec of truth, imperative implementation conforms, drift detector bridges them. Established by `release-train-as-entities`. | n/a |
| **Tenant ULID** | The 26-character Crockford-base32 identifier that scopes ownership of entities. The marketplace tenant is `dna:tenant:6XBZ93FSHN5TRX8MCS5R66FNCM`. Consumer tenants are derived per OQ-4. | "tenant ID", "tenant ref" |
| **Slug** | The short, lowercase, kebab-case string used as the filename stem of a Project entity. Derived from the Project `name` (single-Project repos) or sub-path (monorepo Projects). | "name slug", "Project slug" |

## NOT the Same As (disambiguation)

| Term A | Term B | The Distinction |
|---|---|---|
| **Discovery** | **Detect phase** | Discovery is the whole 5-phase Workflow. Detect is one phase. Don't conflate. |
| **First-time setup** | **Re-discovery** | First-time setup mints a new entity; re-discovery diffs against an existing one. Different flags, different flows. |
| **Marketplace** | **Consuming repo** | Two distinct repos. Marketplace owns the canonical Workflow; consuming repo owns its own Project entity. |
| **Project entity** | **Project (foundation primitive)** | Project entity = the on-disk JSON-LD file. Project (capital P) = the conceptual primitive defined in the foundation v0.6.0 schema. Discovery produces Project entities. |
| **Workflow** | **Skill** | Workflow = canonical entity (the spec). Skill = imperative prose (the implementation). Path A binds them; they are not the same artifact. |
| **Tenant ULID** | **Workflow ULID** | Tenant scopes ownership; Workflow identifies a specific Workflow definition. A Project entity carries both. |
| **`source.repo`** | **`source.path`** | `source.repo` is the GitHub-shorthand org/name (`sulis-ai/agents`). `source.path` is the path inside the repo (`plugins/sulis` for marketplace Projects, empty for repo-root). |
| **`--update`** | **`--path`** | `--update` triggers re-discovery mode (diff against existing). `--path` scopes Detect to a sub-directory (monorepo). They compose: `--update --path apps/cli` re-discovers the cli Project. |
| **`branch_policy`** | **`primary_branch`** | `branch_policy` is the enum (`gitflow-dev-main`, `trunk`, etc.); `primary_branch` is the actual branch name (`main`). One is the model, one is the value. |

## Terms inherited from release-train-as-entities

These appear here for completeness but are defined in `.specifications/release-train-as-entities/SRD.md#glossary`:

- **Project** (foundation primitive, schema v1.0.0)
- **Workflow** (foundation primitive, schema v1.1.0)
- **Step** (foundation primitive, schema v1.2.0)
- **Tool** (foundation primitive)
- **Trigger** (foundation primitive)
- **FailureMode** (FMEA-grounded recovery declaration)
- **DerivedArtifact** (foundation primitive, DR-019)
- **ULID** (26-char Crockford-base32 identifier)

If any of these terms drift in meaning between the two SRDs, the release-train SRD wins — discovery is a *consumer* of those primitives, not their authority.
