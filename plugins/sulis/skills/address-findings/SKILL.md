---
name: address-findings
description: "Turns code-health findings into an ordered to-do list of fixes."
standards:
  input: [REFERENTIAL_INTEGRITY_STANDARD]
  processing: [CRITICAL_THINKING_STANDARD, DECOMPOSITION_PROCEDURE, WORK_PACKAGE_STANDARD]
  output: [CRITICAL_THINKING_STANDARD]
verification_spiral:
  tier: heavy
  template_base: HEAVY_TIER_DEFAULT
  custom_dimensions:
    - name: "WP Standard Conformance"
      threshold: ">= 4/5"
      standard_reference: "plugins/sulis/references/standards/WORK_PACKAGE_STANDARD.md WP-01..WP-11"
      scorer: generating_agent
      evidence_required: "Every produced WP file passes the frontmatter schema (WP-01 identity, WP-06 lineage, WP-07 status), atomic-scope check (WP-02), and references at least one finding signature via addresses_findings (WP-06)"
    - name: "Recurrence Heuristic Discipline"
      threshold: ">= 4/5"
      standard_reference: "this SKILL.md §Recurrence detection"
      scorer: generating_agent
      evidence_required: "When a pattern recurs ≥ 3 times, mechanical-identity check passes before a skill-proposal is written. False-positive skill-proposals are blocked."
related_skills:
  - relationship: depends_on
    skill: code-health
    notes: primary upstream — consumes deep-mode CHECKUP output or per-tier --raw envelopes
  - relationship: depends_on
    skill: ../../references/standards/WORK_PACKAGE_STANDARD.md
    notes: produces WP files matching WP-01..WP-11
  - relationship: depends_on
    skill: _lib/wp_index
    notes: calls generate_index() after writing WP files to refresh INDEX.md
  - relationship: depends_on
    skill: sea:engineering-architect
    notes: dispatched via Agent for characterisation (root cause + fix shape + effort + risk + recurrence)
  - relationship: optional_input
    skill: check-security
    notes: can consume check-security --raw envelope directly
  - relationship: optional_input
    skill: check-readability
    notes: can consume check-readability --raw envelope directly
  - relationship: related_to
    skill: sulis-execution:run-all
    notes: downstream consumer — runs the WPs this skill produces
  - relationship: related_to
    skill: sea:decompose
    notes: sibling — same WP output shape, different input (TDD vs findings)
  - relationship: related_to
    skill: sea:harden
    notes: downstream when source=hardening; consumes Hardening Delta artifacts this skill writes
---

# Address Findings

## Conclusion (Pyramid — lead with the answer)

Bridge skill: takes scanner findings and turns them into a queue of actionable Work Packages the founder can execute one by one. Reads any check-* `--raw` envelope (or a deep-mode CHECKUP.md), dispatches the engineering architect to characterise each finding (what's the root cause, what's the fix shape, how big is it, how risky, does this pattern recur), writes one WP file per atomic unit of work per `WORK_PACKAGE_STANDARD`, and refreshes `INDEX.md` so the founder sees what's next.

Three things make this skill different from "just write some WPs":

1. **The recurrence heuristic.** If the same fix shape recurs ≥ 3 times in one findings batch, propose extracting a skill via `/sulis:add-skill` instead of writing 6 one-off WPs. The skill captures the mechanics; subsequent instances become single-skill-invocations.
2. **The lineage chain.** Every WP carries PROV-O-aligned pointers back to the finding signatures it addresses. The loop closes when the next scanner run confirms those signatures are gone.
3. **The founder-mode summary.** Founder reads three sentences (what was found, what's proposed, in what order) — not 50 raw findings. Operator mode (`--raw`) gives the full JSON envelope.

Read `references/characterisation-prompt.md` for the SEA dispatch contract. Read `references/standards/WORK_PACKAGE_STANDARD.md` (one level up) for the WP file shape.

## When invoked

### Step 1 — Resolve input

Three input shapes accepted:

| Input | Source | Use |
|-------|--------|-----|
| Deep-mode CHECKUP.md path | `/sulis:code-health --mode deep` output | Default — aggregate of all 7 tiers + per-primitive interpretation |
| Single check-* `--raw` JSON | e.g., `python3 plugins/sulis/skills/check-security/scripts/scanner.py --raw` | Focused single-tier characterisation |
| Multiple check-* `--raw` JSONs | merged into one batch | Cross-tier characterisation without code-health overhead |

Validate input via `scripts/findings_loader.py`:

```bash
python3 plugins/sulis/skills/address-findings/scripts/findings_loader.py \
  --input <path-or-glob> \
  [--project NAME] \
  [--max-age-hours 24]
```

Returns: `{ findings: [...], stale: bool, signatures: [...], existing_wp_signatures: [...] }`.

If `stale: true` (input older than `--max-age-hours`), warn the founder and require explicit `--force-stale` to proceed. **Gotcha #4 prevention.**

If a finding signature already appears in an existing WP file's `addresses_findings`, the loader marks it `duplicate: true` — skip in characterisation. **Gotcha #7 prevention (idempotency).**

### Step 2 — Group + classify

Group findings by:

- **Source** (likely value of WP `source:`): hardening (security/reliability findings) / refactor (readability/maintainability) / migration (cross-cutting) / observability / bug
- **Kind** (likely value of WP `kind:`): backend / frontend / async / docs / infra — inferred from finding paths (`.tsx` / `.vue` → frontend; `*_consumer.py` / `*queue*` → async; `.tf` / `Dockerfile` → infra; `*.md` / `README` → docs; everything else → backend)

Output: list of `{source, kind, findings: [...]}` groups. Show the founder these groups (count + severity histogram per group) BEFORE dispatching characterisation. **Gotcha #1 prevention (overwhelm).**

### Step 3 — Dispatch characterisation (SEA via Agent)

For each group with ≥1 finding, dispatch an Agent call:

```
Agent(subagent_type='general-purpose', description='characterise <source>/<kind> findings',
      prompt=<read+substitute references/characterisation-prompt.md>)
```

Multiple groups → multiple Agent calls in ONE message (parallel — same dispatch primitive as `code-health` deep mode).

Per `references/characterisation-prompt.md`, each agent returns a structured response:

```yaml
characterisations:
  - finding_signatures: [list of signatures grouped into one WP]
    root_cause: "..."
    fix_shape: "..."          # e.g., "single-line library swap" / "extract function"
    fix_shape_class: "..."    # e.g., "library-swap" / "missing-timeout" / "kitchen-sink-split"
    effort: small | medium | large
    blast_radius: low | medium | high
    proposed_wp_title: "..."
    proposed_wp_kind: backend | frontend | async | docs | infra
    proposed_acceptance_criteria: [...]
    proposed_test_plan: {...}
recurrence_check:
  fix_shape_class: "..."
  instances_count: N
  mechanically_identical: true | false   # ALL instances must share the same code-edit pattern
  proposed_skill: { name, description, justification }  # only if mechanically_identical AND N >= 3
```

**Gotcha #5 prevention:** the agent prompt explicitly requires `mechanically_identical: true` before proposing a skill — superficial similarity isn't enough.

### Step 4 — Validate + reject scope-violating WPs

For each proposed WP, validate:

- **WP-02 atomic scope:** does the fix fit on one branch + one engineer? If `blast_radius: high` AND `effort: large` AND `fix_shape_class != composite` → reject; ask SEA to decompose. **Gotcha #6 prevention.**
- **WP-03 acceptance criteria falsifiable:** each criterion must be testable mechanically; no "looks good" or "works correctly".
- **Destructive intent echo (MUC-F3):** if the proposed WP touches DB schema / production config / deployed-only files, the title MUST start with `[DESTRUCTIVE] ` and the body MUST have a `## Destructive intent` section. **Gotcha #2 prevention.**

If validation fails, do NOT write the WP; surface in the founder summary as "needs SEA re-characterisation."

### Step 5 — Write WP files

For each validated WP, write a markdown file to `.architecture/{project}/work-packages/WP-NNN.md` per `WORK_PACKAGE_STANDARD` shape:

- Frontmatter: identity (WP-01) + scope (WP-02..04) + verification gates (WP-05) + lineage (WP-06) + status (WP-07) + dependencies + rollback
- Body: why + what changes + how + tests + rollback (founder-readable; no operator jargon)

Use `WP-{NNN}` IDs auto-incremented from existing files; for `source: hardening`, optionally prefix with `HD-{phase}-` (e.g., `WP-HD-AA-042`) per project convention.

### Step 6 — Write characterisation artifacts (when applicable)

Per `WORK_PACKAGE_STANDARD` WP-11 file layout:

| Source | Artifact path | Format |
|--------|---------------|--------|
| `hardening` | `.architecture/{project}/hardening-deltas/HD-NNN.md` | Per `sea:references/hardening-deltas.md` |
| `refactor` | `.architecture/{project}/refactor-plans/{slug}-{date}.md` | Free-form analysis from SEA characterisation |
| Recurrence ≥ 3 + mechanically_identical | `.architecture/{project}/skill-proposals/SP-NNN-{slug}.md` | Pre-fills Gate 2 scope-lock for `/sulis:add-skill` |
| `feature` / `migration` / `bug` / `observability` | No artifact; WP file alone | |

### Step 7 — Regenerate INDEX.md

```bash
python3 plugins/sulis/_lib/wp_index.py --project {project} --repo-root .
```

INDEX.md derived from per-WP files per `WORK_PACKAGE_STANDARD` WP-10.

### Step 8 — Render the founder summary (or operator JSON)

**Founder mode (default):**

```
✏️ Addressed {N} findings → {M} Work Packages

What I found:
  Tier 2 (Safe) — 3 security findings
  Tier 5 (Understandable) — 28 complexity findings (clustered into 2)
  Tier 6 (Evolves) — 1 review-practices hypothesis

What I propose:

🛡 Hardening (3 WPs)
  - WP-042 — Replace xml.etree with defusedxml in probe (backend, 2h, low risk)
  - WP-043 — [DESTRUCTIVE] Swap SHA1 → BLAKE2b in dedup-signature path (backend, 1h, low risk)
  - WP-044 — Add HSTS header on staging (infra, 30min, low risk)

♻️ Refactor (2 WPs from a cluster)
  - WP-045 — Extract `render_markdown` shared helper (backend, 4h, medium risk)
  - WP-046 — Split compute_router.py (backend, 8h, high risk) → composite

💡 Skill proposal (1)
  - SP-001 — /sea:split-kitchen-sink — 4 of 6 kitchen-sink findings have mechanically-identical
    fix mechanics. Worth extracting before writing 4 one-off WPs.

What I suggest sequencing:
  1. WP-044 first (lowest blast radius; closes 1 finding)
  2. WP-042 next (low risk; closes 2 findings; same defusedxml pattern)
  3. Pause + author SP-001 via /sulis:add-skill (validate on 1 instance)
  4. Use the new skill for the remaining 3 kitchen-sink WPs

Full queue: INDEX.md updated — 6 WPs ready to start, 1 skill proposal awaiting authoring.
Run /sulis:execute to start, or /sulis:status to see the full picture.
```

**Operator mode (`--raw`):**

```json
{
  "input_source": "code-health/.checkup/agents/runs/2026-05-25T14:30Z/CHECKUP.md",
  "input_mtime": "2026-05-25T14:30:00Z",
  "findings_total": 32,
  "findings_addressed": 31,
  "findings_deferred": 1,
  "wps_created": [
    {"id": "WP-042", "kind": "backend", "source": "hardening", "addresses": ["..."],
     "characterisation_artifact": ".architecture/agents/hardening-deltas/HD-042.md"}
  ],
  "skill_proposals": [
    {"id": "SP-001", "name": "split-kitchen-sink", "recurrence_count": 4,
     "mechanically_identical": true, "path": ".architecture/agents/skill-proposals/SP-001-split-kitchen-sink.md"}
  ],
  "index_path": ".architecture/agents/work-packages/INDEX.md",
  "errors": []
}
```

## Gotchas

- **MUC-F4 — Number-of-items overwhelm.** 50+ findings = wall of WPs = founder freeze. *Mitigation:* Step 2 groups by source+kind; Step 8 founder summary caps display per category; full list in INDEX.md.
- **MUC-F3 — Destructive WP without echo.** Some fix shapes are destructive (DB migrations, schema changes, production config). *Mitigation:* Step 4 validation requires `[DESTRUCTIVE]` title prefix + `## Destructive intent` body section.
- **MUC-F1 — Operator jargon leak.** SEA characterisation responses use HD / primitive IDs / MECE-3. *Mitigation:* founder-mode renderer translates at the seam; never echoes raw SEA terms.
- **MUC-F5 — Source-of-truth stale.** Old CHECKUP.md → WPs reference findings that may no longer exist. *Mitigation:* Step 1 validates input mtime ≤ 24h; requires `--force-stale` flag to override.
- **Recurrence misfire.** ≥3 superficially-similar but mechanically-different findings → bad skill proposal. *Mitigation:* SEA prompt (`references/characterisation-prompt.md`) requires `mechanically_identical: true` flag set explicitly.
- **WP bloating.** Characterisation produces kitchen-sink WP touching 12 files. *Mitigation:* Step 4 rejects WPs failing WP-02 atomic scope (one-branch + one-engineer); asks SEA to decompose into composite.
- **Idempotency on re-run.** Running address-findings twice on the same CHECKUP.md → duplicate WPs. *Mitigation:* Step 1 loader checks finding signatures against existing WP `addresses_findings` arrays; marks duplicates for skip.

## Vocabulary

- **Characterisation** — the SEA-mediated activity of turning a raw finding into a structured WP shape: root cause + fix shape + effort + risk. (Distinct from `sea:harden`'s "characterisation test" which means a regression-locking test type.)
- **Address** — the verb in the skill name; means "take action on a finding by producing executable work." Plain English; not jargon.
- **Recurrence threshold** — the heuristic: if ≥ 3 findings in one batch share a mechanically-identical fix shape, propose extracting a new skill via `/sulis:add-skill` instead of writing one-off WPs.
- **Characterisation artifact** — a markdown file written alongside WPs to document the SEA analysis (`hardening-deltas/HD-NNN.md` / `refactor-plans/*.md` / `skill-proposals/SP-NNN-*.md`). Optional per source type.
- **Skill proposal (SP)** — output when recurrence threshold fires. Pre-fills the Gate 2 scope-lock for `/sulis:add-skill` so the next step is one-command.
- **Founder summary** — Step 8 output in founder mode: 3 sentences (what was found / what's proposed / sequencing); cap-applied; no operator jargon.

## When to invoke this skill

- Founder ran `/sulis:code-health` (any mode) and asks "now what?"
- Founder ran any individual `/sulis:check-*` skill and wants to act on the findings
- A `/sulis:code-review` run produced draft Hardening Deltas the founder wants to operationalise
- Founder is preparing a hardening sprint and wants the queue scoped + sequenced

## When NOT to invoke this skill

- Founder wants to run a scan — use `/sulis:code-health` or a specific `/sulis:check-*` first
- Founder wants to execute existing WPs — use `/sulis:execute` (or `/sulis-execution:run-all` today)
- Founder wants to see the existing queue without changing it — use `/sulis:status` or open `INDEX.md` directly
- The work is a one-off fix the founder already understands — write the WP file by hand (see `WORK_PACKAGE_STANDARD` for the schema)
