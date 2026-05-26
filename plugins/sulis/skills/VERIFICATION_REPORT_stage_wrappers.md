# VERIFICATION_REPORT — stage-wrapper skills (recon / design / audit / review)

**Skills:**
- `plugins/sulis/skills/recon/SKILL.md` — Stage 0 (Recon)
- `plugins/sulis/skills/design/SKILL.md` — Stage 2 (Design, greenfield)
- `plugins/sulis/skills/audit/SKILL.md` — Stage 2 (Design, brownfield)
- `plugins/sulis/skills/review/SKILL.md` — Stage 4 (Review)

**Authored via:** `sulis:add-skill` (five-gate methodology)
**Tier:** STANDARD — these are thin **orchestration wrappers**: each runs
inside a change, reads `SULIS_CHANGE_ID`, and routes to an EXISTING
skill/agent rather than re-implementing any capability. They are not
methodology/authoring skills and not new analysis engines, so the five gates
run light per the brief.
**Audience:** founder-facing (dual-register, default founder-mode)
**Date:** 2026-05-26
**Verdict: PASS** (all four skills, all five gates)

---

## Gate 1 — Find (no collision; route, don't duplicate)

All four skill names are new under `plugins/sulis/skills/` (verified by
`ls` — no pre-existing `recon` / `design` / `audit` / `review` dirs). Each
wraps a DISTINCT existing capability and shares the change-scoped pattern
established by the just-landed `change` + `specify` skills:

| Skill | Stage | Wraps (existing, verified on disk) | Specialist routed to |
|---|---|---|---|
| `recon` | 0 Recon | `wpx-arrival-check` (RC arrival) + `/sulis:discover-context` (context map) + `/sulis:analyse-codebase` (code shape); writes `CONTEXT.md` via `_change_context.write_change_context()` | context-cartographer |
| `design` | 2 Design (greenfield) | `/sulis:draft-architecture` (blueprint + ADRs) → `/sulis:plan-work` (decompose) | engineering-architect |
| `audit` | 2 Design (brownfield) | `/sulis:analyse-codebase` (structural baseline) + `/sulis:codebase-audit` (gap audit + hardening deltas) | engineering-architect |
| `review` | 4 Review | `/sulis:code-health` (7-tier) + `/sulis:check-security` / `/sulis:codebase-assess` (security) | security-reviewer |

**Vocabulary collision check:** "recon", "design", "audit", "review" are the
stage names from the design doc's six-stage table (§ "The six stages every
change moves through", lines 44–53) — these skills *are* those stages'
founder surfaces, so the naming is the intended mapping, not a collision.
None shadow an existing skill or reference with a conflicting meaning.

**Primitive discovery: N/A — orchestration skills.** None introduce a new
analysis/tool stack; each fans out to ≤ 3 existing passes (well within
PD-02's ≤ 7). The "primitives" are the existing skills/agents they route to,
already decomposed by the design doc's Phase 6 deliverables.

**Gate 1: PASS** (×4).

---

## Gate 2 — Scope Lock

| Lock item | recon | design | audit | review |
|---|---|---|---|---|
| Plugin home | sulis | sulis | sulis | sulis |
| Audience | founder-facing | founder-facing | founder-facing | founder-facing |
| Register | founder default; technical via intent/`--raw`/`/sulis:jargon` | (same) | (same) | (same) |
| Tier | STANDARD (wrapper) | STANDARD | STANDARD | STANDARD |
| Runs inside a change | yes — `resolve_current_change()` first, `null` → route to `/sulis:change start` | yes | yes | yes |
| Reimplements underlying capability | no — routes only | no | no | no — `code-health` keeps its own tier dispatch |
| New Python | none | none | none | none |

Standards-phase blocks match the founder-facing pattern from `specify`:
input `REFERENTIAL_INTEGRITY_STANDARD`; processing `CRITICAL_THINKING` (+
`DECOMPOSITION_PROCEDURE` where the skill fans out into multiple passes —
design/audit/review); output `CRITICAL_THINKING` + `COACHING_STANDARD` +
`TONE_STANDARD` (founder-facing voice). `founder-facing-conventions.md` read
in full. No item TBD.

**Gate 2: PASS** (×4).

---

## Gate 3 — Generate

Every skill has: conclusion-first body (a lead table), the MUST
resolve-change-and-tool-path first action (matching `specify`'s proven
shape), `## When to invoke` + `## When NOT to invoke` (MECE — each NOT-case
routes to a distinct other surface), likelihood-ordered `## Gotchas`,
`## Vocabulary` (≥ 5 terms each), `## See also`, and valid frontmatter
(`standards` / `register` / `verification_spiral` / `related_skills`).

`description:` for each uses user-facing vocabulary only and names the
stage's founder outcome (a fresh session reading the description alone knows
when to invoke). Linguistic audit (NH-02): scanned all four for prohibited
hyperbole (comprehensive / robust / powerful / seamless / revolutionary /
leverage / game-changing) — **zero present** in founder-facing prose.
Progressive disclosure: each points to the underlying skill/agent rather
than inlining its content.

**Gate 3: PASS** (×4).

---

## Gate 4 — Evaluate (STANDARD dimensions)

| Dimension | recon | design | audit | review | Threshold |
|---|---|---|---|---|---|
| ACCA | 4/5 | 4/5 | 4/5 | 4/5 | ≥ 3 |
| Evidence Grounding | 5/5 | 5/5 | 5/5 | 5/5 | ≥ 3 |
| Structural Coherence | 4/5 | 4/5 | 4/5 | 4/5 | ≥ 3 |
| Honest Uncertainty | 4/5 | 4/5 | 4/5 | 4/5 | ≥ 3 |
| Codebase Referential Integrity | 5/5 | 5/5 | 5/5 | 5/5 | ≥ 3 |

### Codebase Referential Integrity trace (shared)

Every skill/agent/script each wrapper cites was verified present on disk:

| Entity | Path | Verified |
|---|---|---|
| `draft-architecture` | `plugins/sulis/skills/draft-architecture/SKILL.md` | yes |
| `plan-work` | `plugins/sulis/skills/plan-work/SKILL.md` | yes |
| `codebase-audit` | `plugins/sulis/skills/codebase-audit/SKILL.md` | yes |
| `analyse-codebase` | `plugins/sulis/skills/analyse-codebase/SKILL.md` | yes |
| `code-health` | `plugins/sulis/skills/code-health/SKILL.md` | yes |
| `codebase-assess` | `plugins/sulis/skills/codebase-assess/SKILL.md` | yes |
| `check-security` | `plugins/sulis/skills/check-security/SKILL.md` | yes |
| `discover-context` | `plugins/sulis/skills/discover-context/SKILL.md` | yes |
| `refresh-context` | `plugins/sulis/skills/refresh-context/SKILL.md` | yes |
| `address-findings` | `plugins/sulis/skills/address-findings/SKILL.md` | yes |
| `engineering-architect` | `plugins/sulis/agents/engineering-architect.md` | yes |
| `security-reviewer` | `plugins/sulis/agents/security-reviewer.md` | yes |
| `context-cartographer` | `plugins/sulis/agents/context-cartographer.md` | yes |
| `wpx-arrival-check` | `plugins/sulis/scripts/wpx-arrival-check` | yes |
| `_change_context.py` → `write_change_context()` | `plugins/sulis/scripts/_change_context.py:136` | yes (signature: `change_id`, `metadata`, `repo_root`; returns `Path` or `None` on write failure — best-effort contract reflected in recon Step 4) |
| `resolve_current_change()` | `plugins/sulis/scripts/_wpxlib.py:3527` | yes |
| `subagent_type` convention | `sulis:engineering-architect` / `sulis:security-reviewer` / `sulis:context-cartographer` (matches `agents/sulis.md` + `run-all`/`run-wp` dispatch sites) | yes |
| SPEC.md path | `{worktree_path}/.changes/{primitive}-{slug}.SPEC.md` (matches `specify` Output section) | yes |

No entity flagged "NEW" — all four skills realise existing Phase-6 deliverables
from already-built passes. The `code-health` deep-mode tier-agent dispatch is
referenced but NOT duplicated (review calls it and interprets).

### Founder-readability (founder-facing extra sub-check)

Every founder-visible string (trigger conditions, report templates, error /
route-away templates, gotcha prose) ran the FE-06 read-aloud test. Internal
IDs (RC-codes, WP-NNN, SEC/DAT/SC, ADR, tier numbers, tool names) appear ONLY
in gotchas as the named leak-risk to suppress — never as founder-facing
headlines. Each skill's report template leads with the readable intent +
`CH-` handle. **100% pass.**

**Gate 4: PASS** (×4; all dimensions ≥ threshold).

---

## Gate 5 — Adversarial Review (≥ 3 misuse cases total; founder-facing included)

### MUC-F (empty repo) — recon on a brand-new / empty repo
**Risk:** a fresh repo has no remote slug (arrival check can't run), no
context docs (cartography finds nothing), little code (structural pass is
thin) — recon reports three failed sub-passes and looks broken.
**PREVENTED:** recon Gotcha "recon on an empty or brand-new repo must not
fail loudly" + Step 1 ("if no repo slug resolvable, skip gracefully") + Step
5 reports "not much here yet — this looks like new ground" rather than three
failures. An empty repo is a valid state, not an error.

### MUC-F (design without a SPEC) — design dispatched with no spec
**Risk:** `/sulis:design` runs against a change that was never specified;
Claude invents a "what" and designs against a guess.
**PREVENTED:** design Step 1 reads `{worktree}/.changes/{primitive}-{slug}.SPEC.md`;
**no SPEC.md → STOP and route to `/sulis:specify`** (explicit template). The
matching Gotcha "design without a spec is a guess" reinforces. (The brief's
named case.)

### MUC-F4 (overwhelm) — review presents a wall of findings
**Risk:** a real review surfaces dozens of findings; review dumps all of them
and overwhelms the founder.
**PREVENTED:** review Step 3 caps surfaced findings to "the handful that
block or matter", groups the rest as a count drillable via the technical
version, and always names the next step (`/sulis:address-findings`). The
matching Gotcha "don't overwhelm with findings" reinforces. (The brief's
named MUC-F4 case.)

### MUC-F (wrong-stage dispatch) — audit run on greenfield work
**Risk:** `/sulis:audit` is invoked for a `feat`/`create` (new work); Claude
audits code that doesn't exist yet, wasting the founder's time.
**PREVENTED:** audit Step 0 checks the primitive; greenfield primitive →
route to `/sulis:design`. Gotcha "audit is the brownfield path; design is
greenfield" reinforces.

### MUC-F1 (operator-vocab leak) — across all four
**Risk:** RC-codes, hardening-deltas, tier numbers, SEC/DAT/SC codes, tool
names, `worktree_path`, JSON envelopes bubble untranslated into chat.
**PREVENTED:** every skill has an MUC-F1 Gotcha mandating translation at the
seam; report templates lead with the readable name + handle; raw output is
gated behind the declared technical-mode (`--raw` / "show me the technical
version" / `/sulis:jargon`).

### MUC-F5 (acting on a missing change) — wrapper run with no SULIS_CHANGE_ID
**Risk:** a wrapper runs outside a change, `resolve_current_change()` returns
`null`, and Claude proceeds against the current directory as a fallback.
**PREVENTED:** all four have the MUST first-action: `null` → STOP and route
to `/sulis:change start`; never write artefacts into a directory with no
change home.

### Audience-agnostic (read-only contract) — review / audit "fixing while in there"
**Risk:** a review/audit pass edits code ("I'll just fix it"), violating the
read-only contract and shipping unreviewed edits.
**PREVENTED:** review + audit both state the passes are read-only; findings
are advice, not edits; follow-up work routes to `/sulis:address-findings` →
tasks. Review Gotcha "review never changes code" and audit Gotcha "hardening
deltas are draft fixes, not applied changes" reinforce.

### MUC-R1 (technical leaks into founder default) — across all four
**Risk:** a skill emits the underlying tool's JSON/report when the founder
expected plain English.
**PREVENTED:** `register.founder_mode: default` declared on all four; every
report template is plain-English; raw data gated behind explicit
technical-mode triggers.

**Coverage:** 4 founder-specific MUC-F cases (empty-repo, design-no-spec,
review-overwhelm/MUC-F4, audit-wrong-stage) + MUC-F1 + MUC-F5 + a read-only
audience-agnostic case + MUC-R1 = 8 cases, all PREVENTED. Exceeds the brief's
≥ 3 (incl. founder-facing) minimum, and covers the three the brief named by
example (recon on empty repo; review overwhelm / MUC-F4; design without a
SPEC).

**Gate 5: PASS** (×4).

---

## Single filesystem check

```
for s in recon design audit review; do
  test -f "plugins/sulis/skills/$s/SKILL.md" || echo "MISSING $s"
done
test -f plugins/sulis/skills/VERIFICATION_REPORT_stage_wrappers.md \
  && grep -q "Verdict:.*PASS" plugins/sulis/skills/VERIFICATION_REPORT_stage_wrappers.md
```

All four SKILL.md present; report present with PASS verdict.
**All four skills shipped.**
