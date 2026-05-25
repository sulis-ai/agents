# Change as a first-class primitive — design

**Status:** Design (pre-build)
**Date:** 2026-05-25
**Author:** Iain (with the Sulis agent)
**Estimated build:** ~5–6 weeks of focused work, split across 6 phases that each commit independently

---

## Summary

The Sulis plugin introduces a new primitive: **the Change**. Every piece of work in flight gets its own ULID-keyed identity, its own long-lived git branch, its own terminal session with a focused Sulis agent, and travels through six stages — **recon → specify → design → execute → review → ship** — before merging to `dev`.

Five specialist agents (context-cartographer, requirements-analyst, engineering-architect, executor + orchestrator, security-reviewer) consolidate under one Sulis agent that routes between them. The change branch is the single integration point — **one PR per change to `dev`** — with auto back-integration keeping it current as `dev` moves.

Specify is **always on** with three depth modes (lite / standard / deep). Storage is hybrid: committed manifest + spec in the repo (teammates see in-flight work; SaaS-ready), session state + dashboard local in `~/.sulis/changes/`. CLI-first; tmux / desktop / web UI in later phases.

---

## The central idea

The founder thinks *"I want to fix the auth bug"* — not *"WP-101 + WP-102 + WP-103."* Today's Work Package is the engineering breakdown; the **change** is the founder's mental model. Lifting "change" to first-class fixes the mental-model gap and unlocks parallel work across multiple in-flight changes without losing context.

---

## What the founder experiences

The founder runs:

```
/sulis:change start "fix the auth bug"
```

A new terminal opens. Inside it, the Sulis agent is already focused on that change, has already done reconnaissance on the repo, and walks the founder through the journey. The original terminal returns to a dashboard view.

The founder can have multiple changes in flight in parallel — each in its own terminal — and never lose track because:

- Each terminal session is bound to its change (env var + heartbeat)
- The dashboard view (`/sulis:changes`) shows everything across them
- `/sulis:change focus CH-01HQ8X` jumps to any change's terminal (respawns if the original session died)

---

## The six stages every change moves through

| # | Stage | Founder command | Skill(s) | Agent | Produces | State |
|---|---|---|---|---|---|---|
| 0 | **Recon** | (implicit at change start) | new: `recon` (RC arrival + cartograph + app-topology) | context-cartographer | `CONTEXT.md` | `recon ✅` |
| 1 | **Specify** | `/sulis:specify` | new: `specify` with depth modes (lite / standard / deep) | requirements-analyst | `SPEC.md` (+ UML in deep) | `specify ✅` |
| 2 | **Design** | `/sulis:design` (or `/sulis:audit` brownfield) | existing sea skills: greenfield-design, brownfield-audit, decompose | engineering-architect | `DESIGN.md` + WP files | `design ✅` (optional for lite-specify) |
| 3 | **Execute** | `/sulis:run-all` (or `/sulis:run-wp WP-NNN`) | existing: run-wp, run-all, retry, wp-status, backfill-* | executor + orchestrator | merged WPs on change branch | `execute ▶ N/M` |
| 4 | **Review** | `/sulis:review` | existing code-health (check-* tier 1–7) + assess + code-review | security-reviewer | review report | `review ✅` or `⚠️` |
| 5 | **Ship** | `/sulis:change ship` | new: ship (rebase + merge-queue + deploy-staging + promote + health) | (Sulis orchestrates; no dedicated agent) | merged to dev → main | `ship ✅` |

Sulis sits across all stages as the founder's coach + invoker + partner. Specialists are dispatched per stage.

### Depth modes for Specify (always on)

| Mode | What the founder does | What gets produced | When |
|---|---|---|---|
| **Lite** | Three-field template (intent / acceptance / what-to-avoid), ~30 seconds | ~10-line `SPEC.md` | Hotfix, typo, single-file mechanical change |
| **Standard** | 5–10 question facilitated conversation, ~3 minutes | `SPEC.md` with intent, scope, acceptance, constraints, non-goals | Most changes |
| **Deep** | Full SRD with use cases + sequence/state/process diagrams (Mermaid) | `SPEC.md` + diagrams | New features, new systems, anything user-facing or cross-team |

The Sulis agent proposes a depth from change-intent signals + repo signals via a deterministic classifier (file count, primitive count, founder-facing flag). On uncertainty, defaults to standard. Founder confirms or overrides.

### Design is optional for lite-specify changes

Decomposition is usually obvious for lite changes (one WP). The Sulis agent proposes: *"This is small enough to go straight to a single WP — want me to draft `WP-NNN` and run it, or do you want a design pass first?"*

---

## The branching model

```
main ← promote (existing RC workflow: promote-dev-to-main)
  ↑
dev ← merge queue (existing RC; source = change/* branches)
  ↑
change/create-payments-01HQ8X ← long-lived integration branch
  ↑↑↑
feat/wp-101-schema   feat/wp-102-handler   feat/wp-103-tests
                          (each WP branches from change, merges back)
```

The **change branch is the integration point**. One PR per change reaches `dev` — not one PR per WP. Reviewers see the cohesive change; CI runs on the cohesive unit. Today's WP-level executor flow stays unchanged.

The branch architecture is already specified by `CW-04` in the Change Work Standard (`plugins/srd/references/change-work-standard.md`). Today's executor (in `plugins/sulis/scripts/_wpxlib.py`) already branches WP off the change branch via `_branch_name() → feat/wp-{id-lower}-{slug}`. The gap is the founder-facing surface — not the data model.

---

## Auto back-integration from trunk

The change branch stays current with `dev` automatically. The mechanism is **merge, not rebase** — preserving commit SHAs so any in-flight WP worktrees stay valid.

### Two trigger points

| When | What runs | Why |
|---|---|---|
| After every WP merges back to change | `git fetch origin dev && git merge --no-edit origin/dev` on change branch; push | Keeps change branch within one WP of dev |
| Before every new WP starts (executor Step 0 / arrival check) | Same — fast no-op if already up-to-date | Defence in depth |

Both together. After is the active driver; before is the safety net for teammate pushes to `dev` that happened between WPs.

### Conflict handling

If `git merge origin/dev` on the change branch fails:

- Don't auto-resolve
- Sulis pauses the WP-in-flight and surfaces the conflict in founder English:
  > *"Dev moved while you were working — there's a conflict in `src/auth.py` between your change and what was merged 12 minutes ago. Want me to walk you through resolving it?"*
- Founder picks: resolve interactively / abandon back-integration for now (continue on stale branch; surfaces again next time) / abort this WP

### Lifecycle amendments

Two paragraph-sized additions to `plugins/sulis/references/lifecycle.md` (the 2292-LOC executor bible):

- Step 0 (arrival check) gains: "is the change branch behind dev? If yes, run back-integration before creating WP worktree"
- New Step 12.5: after WP merges back to change, run back-integration on change branch + push

Plus one clarifying amendment to `plugins/srd/references/repository-contract-standard.md` (`RC-04`): merge-queue source is `change/*` branches, not `feat/*` directly.

---

## Identity scheme — IDs that survive multi-author collaboration

Three layers per change:

| Layer | Identity | Example | Purpose |
|---|---|---|---|
| Canonical | **ULID** (128-bit, sortable, collision-free by construction) | `01HQ8XQM8G5KZGZQXPZD8H6PJ7` | Primary key; SaaS-ready by construction |
| Display handle | **First 6 Crockford-base32 chars** | `CH-01HQ8X` | What the CLI shows; jj-style enough-to-disambiguate |
| Human slug | **Author-chosen kebab** | `create-payments` | Branch name; what humans recognise |

Branch name combines them: `change/create-payments-01HQ8X`. Two founders working offline can both create a change called `create-payments` and never collide because their ULIDs differ.

**SaaS-ready by construction.** When the cloud offering lands, the server adopts the same ULID — no migration needed. Locally, [`python-ulid`](https://pypi.org/project/python-ulid/) is the implementation choice (zero deps, stdlib-style).

### WP identity gains a `change_id:` field

WP frontmatter (per `WORK_PACKAGE_STANDARD.md`) gets one new field:

```yaml
id: WP-101
change_id: 01HQ8XQM8G5KZGZQXPZD8H6PJ7
# ... existing fields
```

WP-NNN sequential within a change remains the convention; cross-change collisions don't matter because the change_id disambiguates.

---

## Storage — hybrid (committed + local)

| What | Location | Why |
|---|---|---|
| Change manifest (id, slug, intent, status, WP list, current stage) | `.architecture/{project}/changes/{ulid}.yaml` — **committed** | Teammates see in-flight changes |
| Spec + Design docs | `.architecture/{project}/changes/{ulid}/{SPEC,DESIGN}.md` — **committed** | Reviewable artefacts |
| Work Packages | `.architecture/{project}/work-packages/WP-NNN.md` — **committed** | + new `change_id:` linking back |
| Session state (pid, heartbeat, transient WIP, patch-set drafts) | `~/.sulis/changes/{ulid}/` — **local only** | Operational; SaaS replaces with server |
| Cross-change dashboard state | `~/.sulis/sulis.db` (SQLite) — **local only** | Fast queries for smartlog view |

A teammate cloning the repo can run `/sulis:changes --remote` to see all in-flight changes (reading the committed manifests), even without local session state. SaaS later replaces the local SQLite with a server.

---

## Session binding — how a terminal stays bound to its change

When `/sulis:change start "fix the auth bug"` runs:

1. Allocate ULID + slug; write change manifest to `~/.sulis/changes/{ulid}/CHANGE.md` and `.architecture/{project}/changes/{ulid}.yaml`
2. Run recon synchronously; write `CONTEXT.md` to both locations
3. Create `change/{slug}-{handle}` branch + `~/repo-change-{slug}/` worktree per CW-04
4. Spawn new terminal — `osascript` on macOS (lifted from `terminal_launcher.py:308` in `ae_task_executor`), `gnome-terminal/konsole/xterm` on Linux
5. New terminal `cd`s into the change worktree, sets `SULIS_CHANGE_ID={ulid}` env var, invokes `claude` with a HERE-DOC pre-prompt:
   ```
   You are Sulis, focused on change CH-01HQ8X: "fix the auth bug".
   Working directory is the change worktree.
   Context recon is at ~/.sulis/changes/01HQ8X.../CONTEXT.md.
   Current stage: Specify. Suggest: /sulis:specify
   ```
6. Original terminal returns to dashboard

### Session binding mechanics

- `SULIS_CHANGE_ID` env var is the primary binding — every sulis CLI script reads it first
- `~/.sulis/changes/{ulid}/session.json` records: pid, tmux pane id, spawn timestamp, last-heartbeat
- Heartbeat updated on every CLI invocation (so `/sulis:changes` shows "active 3 min ago")
- If session dies (terminal closed, machine rebooted), `/sulis:change focus CH-01HQ8X` detects stale pid and respawns with the same context

### Reattach behaviour

`/sulis:change focus CH-NNN`:
- If pid alive: bring window to front (osascript)
- If pid stale: confirm respawn, then run the spawn flow again (same change_id, same worktree, fresh Sulis session)

---

## Agents — five specialists under Sulis

| Agent | Stage | Source plugin (pre-consolidation) |
|---|---|---|
| **Sulis** (renamed from concierge) | All stages — coach, invoker, partner | sulis |
| context-cartographer | 0. Recon | sulis-context |
| requirements-analyst | 1. Specify | srd |
| engineering-architect | 2. Design | sea |
| executor + orchestrator | 3. Execute | sulis (already) |
| security-reviewer | 4. Review | sulis-security |

The founder talks to Sulis. Sulis dispatches the right specialist at the right stage. No founder-direct invocation of specialists is needed — though `/sulis:agent-direct {name}` is available as an operator escape hatch.

---

## Tone stack — five standards layered

| Layer | Standard | What it asks |
|---|---|---|
| Audience detection | **AAF** (existing — `plugins/srd/references/audience-adapted-framing-standard.md`) | Who am I talking to, what depth? |
| Vocabulary translation | **FE** (existing — `plugins/srd/references/founder-english.md`) | Have I stripped jargon, translated identifiers? |
| Voice and lexicon | **TONE** (new — port from `platform/methodology/standards/TONE_STANDARD.md`) | Am I in operator voice using preferred vocabulary? |
| Insight delivery | **COACHING** (new — port from `platform/methodology/standards/COACHING_WITHOUT_CONFLICT.md`) | Does this land without triggering defensiveness? |
| Sulis-layer apply | **Founder-Facing Conventions** (existing) | Are echo-before-act + prompt-before-destroy honoured? Dual-register pattern applied? |

### Dual-register pattern (new section in Founder-Facing Conventions)

Every founder-facing agent is **dual-register** — defaults to founder-mode (full tone stack applied), switches to technical-mode on request.

**Three trigger mechanisms** in order from lightest to heaviest:

| Trigger | Scope | Example |
|---|---|---|
| Natural language intent | This response only | "show me the technical version" → Sulis detects and switches |
| `--raw` flag on command | This invocation only | `/sulis:wp-status WP-101 --raw` returns JSON envelope |
| Session toggle | Until toggled back | `/sulis:jargon on` switches to technical; `/sulis:jargon off` reverts |

Founder-mode is a **translation, not a filter**. Same substance, different shape. No information hidden in founder-mode that surfaces only in technical — that would erode trust.

### What COACHING + TONE add (already in the platform standards; port into sulis-local)

**COACHING_WITHOUT_CONFLICT** — seven tenets for delivering insight without triggering defensiveness:
- Structural over personal
- Diagnostic over prescriptive
- Questions over statements
- Modelling over telling
- Hypotheses over conclusions
- Sequence for relationship capital
- Room to step up

Plus a seven-question validation checklist (red-flag phrases → green-light alternatives).

**TONE_STANDARD** — five non-negotiable directives + systemic lexicon:
- T-01 Pragmatic Authority (operator voice, not theorist)
- T-02 Radical Clarity (plain English, fewest words)
- T-03 Build + Market Reality (always connect technical to commercial outcome)
- T-04 Governance Over Mystification (AI as governed activity, not magic)
- T-05 Vocabulary Governance (three-zone framework: ban / preserve / coin-selectively)

Plus a forbidden-vocabulary list (no "help", "try", "passion", "magic", "seamless", "revolutionary", "leverage", etc.) and preferred-vocabulary table.

---

## What's already built vs what's new

### Already built — no change needed

- Change-branch architecture (`CW-04` in Change Work Standard)
- Two-level worktree hierarchy (`~/repo-change-{slug}/` containing `~/repo-wp-{id}-{slug}/`) per `lifecycle.md:46-114`
- WP lifecycle and executor flow (12 steps)
- All five specialist agents in their current plugins (will be consolidated into sulis)
- Repository Contract Standard (RC-01..RC-13: dev/main + merge queue + 6 GitHub Actions workflows)
- AAF + FE + Founder-Facing Conventions (the founder-tone foundation)
- `add-skill` v0.7.0 (the five-gate standards-grounded methodology)
- The 5 sulis-local cross-cutting standards (Critical Thinking, Decomposition, Spiral Templates, Standards Rubric, Referential Integrity)

### New — build this

- `add-agent` meta-skill (agent-authoring sibling of add-skill)
- `consolidate-into-sulis` meta-skill (codify the proven sulis-execution → sulis pattern)
- ULID + handle + slug allocator
- `/sulis:change start | list | focus | ship | rebase` CLI surface
- Terminal-spawn-per-change mechanism (port from `ae_task_executor`)
- Auto back-integration (lifecycle Step 0 check + Step 12.5)
- Recon pipeline (RC arrival + cartograph + app-topology)
- `/sulis:specify` with three depth modes + deterministic classifier
- `/sulis:design`, `/sulis:audit`, `/sulis:review`, `/sulis:change ship` skills
- `~/.sulis/changes/` local store + SQLite dashboard schema
- `/sulis:changes` smartlog view
- Per-stage auto-scoping via `SULIS_CHANGE_ID` env var
- Sulis agent rewrite (rename from concierge; embed COACHING + TONE; apply dual-register pattern)
- `/sulis:jargon on | off` session toggle + `--raw` flag handling
- COACHING_WITHOUT_CONFLICT.md + TONE_STANDARD.md ported into sulis-local

### Deferred — future phases

- tmux sidebar for live cross-session dashboard (opensessions-style)
- Desktop UI (Tauri / Electron — Kanban view, click-to-attach, patch-set history)
- Web / mobile UI for AFK status
- SaaS sync of change records (replace local SQLite with server)
- jj-style cross-change operations (`/sulis:change stack | rebase | abandon | reorder`)

---

## Methodology — the two new authoring meta-skills

### `add-agent` (sibling of `add-skill`)

Mirrors `add-skill` v0.7.0's five gates — Find / Scope Lock / Generate / Evaluate / Adversarial Review — adapted for agents.

| Gate | What it checks for agents |
|---|---|
| 1. Find | BRIEF_PACK of every existing agent in the marketplace; vocabulary collision; dispatch-trigger overlap |
| 2. Scope Lock | Agent name; plugin home; dispatch trigger; tools needed; audience; related skills/agents; model preference; **register declaration** (founder-mode + technical-mode shapes if founder-facing or both) |
| 3. Generate | `agent.md` with standard frontmatter; declares dispatch contract; cites wrapped references |
| 4. Evaluate | Three perspectives: dispatch-accuracy, tool-completeness, output-shape. Plus for founder-facing: coaching-delivery, register-switch correctness |
| 5. Adversarial | Audience-agnostic: over-dispatch, under-dispatch, tool-leakage, context-bloat. Founder-facing adds MUC-A1..A4 (prescriptive leak, banned-vocabulary leak, defensive-trigger leak, commercial-outcome missing). Register-aware adds MUC-R1..R3 (technical leaks into founder default, founder-mode drops needed information, register-switch ambiguity) |

Standards citation requirement varies by audience:

| Audience | Must cite |
|---|---|
| operator-facing | Five sulis-local standards (Critical Thinking / Decomposition / Spiral / Standards Rubric / Referential Integrity) |
| founder-facing | All five operator standards PLUS AAF + FE + Founder-Facing Conventions + COACHING + TONE |
| both | All ten + mode-selection strategy documented |

Produces `agent.md` + `VERIFICATION_REPORT.md` on disk.

### `consolidate-into-sulis` (codifies the proven migration pattern)

Encodes the eight-step recipe from the sulis-execution → sulis consolidation (5 commits, 50 files moved, 0-finding self-test sustained):

1. Inventory source plugin (skills, agents, scripts, references, docs, tests, CI workflows)
2. Map old paths → new paths; design rename strategy where conflicts exist
3. Move scripts + tests + CI workflow (`git mv` preserves history)
4. Move skills (ref updates across ~12 categories: cache path, dev fallback, plugin install, subagent_type renames)
5. Move agents (same ref-update pattern)
6. Move references (handle cross-plugin refs)
7. Move docs (rename to deduplicate when names collide)
8. Source plugin becomes `[DEPRECATED]` (manifest, README, CLAUDE.md, CHANGELOG); decide on shim policy (default: no shims, per sulis-concierge precedent)
9. Sulis metadata bumped (plugin.json + CHANGELOG with full migration story + marketplace.json + marketplace version)
10. Cross-skill self-test on the migrated tree

Produces `CONSOLIDATION_REPORT.md` documenting what moved, what didn't, what renames were necessary, deprecation policy.

---

## Phased build plan

Each phase commits independently; partial adoption is defensible at any boundary.

### Phase 0 — Tone foundation (~2–3 days)

**Goal:** Port COACHING + TONE into sulis-local standards; add dual-register section to Founder-Facing Conventions. Foundation for every founder-facing agent that follows.

**Deliverables:**
- `plugins/sulis/references/standards/COACHING_STANDARD.md` (adapted from platform; trim engagement-week sequencing for sulis scale)
- `plugins/sulis/references/standards/TONE_STANDARD.md` (adapted from platform; trim OFM-only scoping; apply to all founder-facing surfaces in sulis)
- `plugins/sulis/references/founder-facing-conventions.md` — new section on dual-register pattern + `/sulis:jargon` mechanics
- `plugins/sulis/references/standards/README.md` updated to list 7 standards (was 5)

**Commit:** `feat(sulis): v0.x.0 — port COACHING + TONE standards; dual-register pattern in Founder-Facing Conventions`

### Phase 1 — Meta-skills (~3–4 days)

**Goal:** Author the two new authoring meta-skills before anything else. Every subsequent agent and consolidation uses them.

**Deliverables:**
- `/sulis:add-agent` skill, authored via `add-skill` v0.7.0; cites all 7 sulis-local standards + 3 founder-facing standards (AAF, FE, Founder-Facing Conventions)
- `/sulis:consolidate-into-sulis` skill, authored via `add-skill` v0.7.0
- `VERIFICATION_REPORT.md` for each, all dimensions ≥ threshold
- Trial run: author one small new agent (e.g., a `change-classifier` agent for the depth-mode classifier) via add-agent to validate the methodology before using it for consolidations

**Commits:**
- `feat(sulis:add-agent): v0.1.0 — five-gate agent-authoring methodology`
- `feat(sulis:consolidate-into-sulis): v0.1.0 — plugin consolidation methodology`

### Phase 2 — Sulis agent rewrite (~2–3 days)

**Goal:** Rename concierge → Sulis; rewrite the agent spec to embed COACHING + TONE + dual-register; delete deprecated sulis-concierge plugin shell.

**Deliverables:**
- `plugins/sulis/agents/concierge.md` → `plugins/sulis/agents/sulis.md`
- All 145+ references updated (mechanical sed, verified by ripgrep)
- Sulis agent persona update: "Hi, I'm Sulis" — capitalised when speaking
- COACHING + TONE embedded at the right phases (coaching for feedback delivery; tone for vocabulary discipline); existing AAF + FE embedding stays
- Dual-register pattern applied; `/sulis:jargon` toggle wired
- `plugins/sulis-concierge/` deleted outright (deprecation shim since v0.2.0)

**Commit:** `feat(sulis): v0.x.0 — concierge → Sulis rename; COACHING + TONE embedded; dual-register pattern applied`

### Phase 3 — Consolidations (~1–2 weeks)

**Goal:** Use `consolidate-into-sulis` four times to bring the specialist plugins into sulis. Each consolidated agent re-authored via `add-agent` so it inherits the coaching/tone discipline from the start.

Order by size/risk: smallest as practice run; largest last when the pattern is proven.

| Order | Plugin | Estimate | Why this order |
|---|---|---|---|
| 1 | sulis-context | ~1–2 days | Smallest (1 agent + a few skills); safest practice run |
| 2 | sulis-security | ~2–3 days | Small; folds into Phase 4 review surface |
| 3 | sea | ~3–5 days | Medium (1 agent + 4–5 skills); shipped first as it underwrites Phase 2 design surface |
| 4 | srd | ~5–7 days | Largest (10+ skills + cross-plugin standards); shipped last when pattern is well-proven |

**Commits:** one chain per consolidation, mirroring the sulis-execution → sulis pattern (5 commits per consolidation, ~50 files moved each).

### Phase 4 — Standards amendments (~1–2 days)

**Goal:** Amend existing standards for the new fields and steps.

**Deliverables:**
- `WORK_PACKAGE_STANDARD.md` — add `change_id:` field; amend WP-01 Identity section
- `change-work-standard.md` (CW-04) — add auto back-integration mechanics
- `repository-contract-standard.md` (RC-04) — clarify merge-queue source = `change/*` branches
- `lifecycle.md` — paragraph addition for Step 0 arrival-check; new Step 12.5 for back-integration

All amendments via `add-skill` deepening mode (no new edit-standard skill needed).

**Commit:** `feat(sulis): v0.x.0 — standards amendments for change-as-primitive (CW-04 + RC-04 + WP-01 + lifecycle Step 0/12.5)`

### Phase 5 — Change-as-primitive infrastructure (~1 week)

**Goal:** Build the data + spawn + session-binding infrastructure. CLI surface goes live in Phase 6.

**Deliverables:**
- `plugins/sulis/scripts/_change.py` — ULID + handle + slug allocator; change manifest CRUD
- `~/.sulis/sulis.db` SQLite schema (changes, sessions, heartbeats, patch-sets)
- Terminal launcher (port from `ae_task_executor/terminal_launcher.py:24-349` — osascript on macOS, gnome-terminal/konsole/xterm dispatch on Linux); shell-script-per-session with HERE-DOC pre-prompt injection
- `SULIS_CHANGE_ID` env-var binding; heartbeat updater
- Auto back-integration mechanic in `wpx-pipeline` Step 0 + new Step 12.5

**Commit:** `feat(sulis): v0.x.0 — change-as-primitive infrastructure (ULID, terminal spawn, session binding, auto back-integration)`

### Phase 6 — Founder-facing skills (~1 week)

**Goal:** Author the user-visible CLI surface via `add-skill` v0.7.0.

**Deliverables:**
- `/sulis:change start` — spawn flow
- `/sulis:changes` — smartlog view
- `/sulis:change focus CH-NNN` — reattach
- `/sulis:change ship CH-NNN` — rebase + PR + merge queue + deploy + promote
- `/sulis:change rebase` (manual escape hatch, in addition to auto)
- `/sulis:specify` with three depth modes + deterministic classifier
- `/sulis:recon` (Stage 0 entry — wraps RC arrival + cartograph + app-topology)
- `/sulis:design`, `/sulis:audit` (consolidated from sea)
- `/sulis:review` (consolidated; folds in code-health + security-reviewer)
- `/sulis:jargon on | off` toggle

Sulis agent dispatches the right specialist per stage based on `SULIS_CHANGE_ID` + change manifest current stage.

**Commits:** one per skill (or grouped logically), each with VERIFICATION_REPORT.md on disk.

### Phase 7 — End-to-end test + harden (~2–3 days)

**Goal:** Run the full journey on a real change in this repo. Probably the next consolidation eats its own dogfood.

**Deliverables:**
- A real change drives recon → specify → design → execute → review → ship
- Cross-skill self-test sweep on the entire migrated tree
- Founder-mode walkthrough of the dashboard view
- Any gaps discovered → fixed before declaring v1 ready

**Commit:** `feat(sulis): v1.0.0 — change-as-primitive end-to-end (founder-facing CLI surface live)`

---

## Locked decisions

1. **Three-layer identity:** ULID (canonical) + 6-char display handle + author-chosen slug
2. **Branch model:** change branch as integration point; one PR per change to dev; WPs branch from change, merge back
3. **Auto back-integration:** merge-not-rebase, after each WP + before next; pause on conflict
4. **Specify always on:** lite mode is the escape valve, never skip entirely
5. **Depth classifier:** deterministic heuristics first; default-to-standard on uncertainty
6. **Hybrid storage:** committed manifest + specs in repo; session state + dashboard local; SaaS-ready by construction
7. **Five specialists under one Sulis agent** (consolidated from sulis-context / srd / sea / sulis / sulis-security)
8. **Session-per-change:** osascript spawn + `SULIS_CHANGE_ID` env var + HERE-DOC pre-prompt
9. **Concierge → Sulis rename** (agent file rename; persona "Sulis"; 145+ references updated)
10. **Five-layer tone stack:** AAF + FE + COACHING + TONE + Founder-Facing Conventions
11. **Dual-register pattern:** default founder-mode; on-request technical-mode via intent + `--raw` + `/sulis:jargon`
12. **Option A:** every specialist speaks founder-mode by default; user can always ask for the technical version
13. **CLI first; UI later** — tmux / desktop / web all deferred
14. **Meta-skills first:** `add-agent` + `consolidate-into-sulis` before any consolidation
15. **Order of consolidation:** sulis-context → sulis-security → sea → srd (smallest first as practice)
16. **No deprecation shim skills** during consolidations (mirrors sulis-concierge precedent)
17. **`/sulis:jargon on | off`** session toggle (names the discipline being toggled, not the mode label)
18. **Delete deprecated `plugins/sulis-concierge/`** outright (Phase 2)
19. **COACHING + TONE port to sulis-local** as adapted standards (Phase 0)
20. **Dual-register as section in Founder-Facing Conventions**, not new standard

---

## Open questions for future phases

These are deliberately deferred to the phase that lands them:

- **REGISTER_STANDARD vs section in Founder-Facing Conventions** → locked to section (this design doc)
- **tmux sidebar shape** — opensessions-style is the reference; concrete shape decided in the UI phase
- **Desktop UI tech choice** — Tauri vs Electron vs native; decided when UI phase starts
- **SaaS sync mechanics** — out of scope for this design; separate design doc when that phase starts
- **Cross-change operations (stack / rebase / abandon)** — jj-style; out of scope for v1; revisit after Phase 7 when usage signal exists

---

## What this doesn't do (deferred / out of scope)

- **Founder-facing notification surfaces** (status line, system notifications, slack/email digests) — deferred to UI phase
- **Multi-machine session sync** — single-machine only for v1; SaaS phase
- **Cross-repo / multi-repo changes** — single-repo for v1
- **Change-templating** ("change like the last one") — could land in v1.x if usage signal exists
- **Patch-set history beyond the most recent** — full history in repo via git, but no UI for browsing patch-set N vs N-1; UI phase
- **Founder identity / multi-user** — single-founder local for v1; SaaS phase introduces accounts

---

## Critical files (orientation for the build)

### Heavily extended in this work

- `plugins/sulis/scripts/_wpxlib.py` — Step 0 arrival check + back-integration helpers
- `plugins/sulis/scripts/wpx-pipeline` — Step 0 invocation + Step 12.5 invocation
- `plugins/sulis/scripts/sulis-change` — extended with ULID + spawn + session binding
- `plugins/sulis/agents/sulis.md` (renamed from concierge.md) — COACHING + TONE + dual-register embedded
- `plugins/sulis/references/lifecycle.md` — Step 0 + Step 12.5 paragraphs added
- `plugins/sulis/references/founder-facing-conventions.md` — dual-register section added
- `plugins/sulis/references/standards/README.md` — updated to list 7 standards

### New files

- `plugins/sulis/references/standards/COACHING_STANDARD.md`
- `plugins/sulis/references/standards/TONE_STANDARD.md`
- `plugins/sulis/skills/add-agent/SKILL.md` (+ scripts, references, templates)
- `plugins/sulis/skills/consolidate-into-sulis/SKILL.md` (+ scripts, references, templates)
- `plugins/sulis/skills/change-start/SKILL.md`
- `plugins/sulis/skills/changes/SKILL.md` (smartlog)
- `plugins/sulis/skills/change-focus/SKILL.md`
- `plugins/sulis/skills/change-ship/SKILL.md`
- `plugins/sulis/skills/change-rebase/SKILL.md`
- `plugins/sulis/skills/specify/SKILL.md` (with depth modes)
- `plugins/sulis/skills/recon/SKILL.md`
- `plugins/sulis/skills/design/SKILL.md` (consolidated from sea)
- `plugins/sulis/skills/audit/SKILL.md` (consolidated from sea)
- `plugins/sulis/skills/review/SKILL.md` (consolidated; folds in security-reviewer)
- `plugins/sulis/skills/jargon/SKILL.md`
- `plugins/sulis/scripts/_change.py` — ULID + handle + slug allocator + manifest CRUD
- `plugins/sulis/scripts/_terminal_launcher.py` — port from ae_task_executor

### Reused unchanged

- `plugins/sulis/skills/run-wp`, `run-all`, `retry`, `wp-status`, `backfill-code-review`, `backfill-gates` — already in sulis from v0.30.0 migration
- `plugins/sulis/skills/code-health` + `check-*` family — already in sulis
- `plugins/sulis/skills/add-skill` — used to author every new skill in this work
- `plugins/sulis/skills/address-findings` — already in sulis; minor extension to attach `change_id` to generated WPs
- `plugins/sulis/agents/executor.md`, `orchestrator.md` — unchanged
- All 5 sulis-local standards (Critical Thinking / Decomposition / Spiral / Standards Rubric / Referential Integrity) — unchanged

---

## Defensible stopping points

- **After Phase 0** — tone foundation live; existing concierge agent stays as-is. Could pause indefinitely; future founder-facing skills get the new standards for free.
- **After Phase 1** — meta-skills live. Could pause; future agent authoring + consolidations have the methodology even if not yet applied.
- **After Phase 2** — Sulis agent rewritten with COACHING + TONE. Visible founder-tone improvement; no other structural change.
- **After Phase 3** — all specialists consolidated under sulis. Operationally, srd/sea/sulis-context/sulis-security become `[DEPRECATED]`; sulis is the canonical plugin. No change-as-primitive yet.
- **After Phase 5** — infrastructure live but no founder surface; can be operator-tested in isolation.
- **After Phase 6** — full founder-facing CLI live; the journey works end-to-end.
- **After Phase 7** — hardened v1; safe to declare and announce.

---

*This design document is the canonical reference for the change-as-primitive work. Amendments after build starts should be appended here (with date + commit hash) rather than rewritten in place — the design's evolution is itself signal.*
