# Completeness Report — sulis:check-polish

**Authored:** 2026-05-23
**Author:** Iain + Claude (dogfood run #9 of sulis:add-skill v0.6.0)

## Verdict summary

| Gate | Status | Notes |
|---|---|---|
| 1 — Find | PASS | 5 sibling-template overlaps; 0 vocab collisions |
| 2 — Scope Lock | PASS | 8 items locked; v1 scope narrowed from SEA TDD original (perf/a11y/UX deferred — needs upstream design) |
| 3 — Generate | PASS | SKILL.md + scripts/scanner.py (uses _lib/) + references/polish-rules.md |
| 4 — Evaluate | PASS | 3 perspectives + Perspective 4 self-test |
| 5 — Adversarial Review | PASS | 3 MUC-F + 3 audience-agnostic; 1 OPEN_RISK |

**Publication decision:** APPROVED

---

## Gate 2 — Scope Lock

| Item | Value |
|---|---|
| Skill name | `check-polish` |
| Plugin home | `sulis` |
| Audience | both. `--raw` flag |
| Category | Founder UX & Navigation |
| Trigger | "Use when the founder wants to know if the project feels professional — checks documentation completeness (README, CHANGELOG), tech-debt markers (TODO/FIXME/HACK density), and basic file hygiene (trailing whitespace, mixed line endings). Read-only; never modifies code." |
| FP philosophy | **Advisory-default** with one concern-severity case (missing README on a versioned plugin). Polish is by definition subjective; almost everything is advisory. |
| Top-5 gotchas | (below) |
| Depth modes | None for v1 |

### Top-5 gotchas

1. **Polish is opinionated; v1 scope is narrow.** SEA's TDD originally specified tier 7 as perf/a11y/UX. Those need upstream design work (which performance budget? which a11y standard?). v1 ships a NARROWER tier-7: documentation completeness + tech-debt markers + file hygiene. Document the scope-difference; founders expecting perf/a11y won't get it. *Source: SEA TDD ADR-006 deferral.*

2. **Tech-debt markers (TODO/FIXME) aren't bugs.** Some projects use TODO as "intentional future-work" — flagging high TODO density would over-report. v1: only flag when density >5% of total comments. *Source: every linter's known limit on TODO interpretation.*

3. **Missing README on legacy plugins isn't a regression.** Existing plugins without README are pre-existing; v1 ships them as concern (not high) so founder doesn't see "❌ failed" for old work. *Source: HD-004 incomplete cleanup pattern — same problem.*

4. **Line-ending mix is often legitimate** in cross-platform projects. Windows + Unix collaborators produce mixed line endings; .gitattributes fixes it at commit time. v1: advisory only. *Source: cross-platform development reality.*

5. **Founder might expect this to FIX polish issues.** Universal read-only. Mitigation: "never modifies code" in 3 places. *Source: cross-skill pattern.*

### Vocabulary

- **polish** — umbrella property: "does the project feel professional and complete?"
- **docs-completeness** — has README + CHANGELOG + (where applicable) LICENSE + plugin.json keywords.
- **tech-debt-marker** — TODO / FIXME / HACK / XXX / TEMPORARY comment.
- **trailing-whitespace** — lines ending in spaces/tabs (cosmetic).
- **line-ending-mix** — files with both CRLF and LF (or just CRLF in a primarily-LF project).

---

## Gate 3 — Generate

Per-plugin scope (each `plugins/*/` audited as a unit) + per-file scope for hygiene checks.

---

## Gate 4 — Evaluate

### P1 Trigger accuracy: PASS
- "does this look professional?" / "what's missing?" / "is documentation complete?" → triggers

### P2 Gotchas coverage: PASS
All 5 sourced.

### P3 Functional completeness: PASS
- Real-state run against marketplace: surfaces TODO density + missing READMEs in some plugins
- Synthetic fixture with trailing whitespace: flagged
- Cross-skill: 0 findings on new code from sibling skills

### P4 Cross-skill self-test: PASS
- check-readability on scanner.py: 0
- check-security on scanner.py: 0
- check-reliability on scanner.py: 0
- check-maintainability on scanner.py: 0 (self-file ref-count fix verified the new symbol-counter works)

---

## Gate 5 — Adversarial Review

### MUC-F1: Jargon — PREVENTED. Rule names stay operator-side.
### MUC-F3: Destructive — PREVENTED. "Never modifies code" stated 3 places.
### MUC-F4: Overwhelm — PREVENTED. Per-plugin grouping caps the list; many plugins = scrollable but structured.
### Audience-agnostic — FP philosophy adherence: PREVENTED. Advisory-default; one concern case explicit.
### Trigger too broad: PARTIALLY PREVENTED. "professional" is subjective; "When NOT" points elsewhere for specific concerns.

---

## Open risks

1. **Tier 7 scope intentionally narrower than SEA's original.** Perf / a11y / UX deferred. Documented in SKILL.md. **revisit_by:** event — founder asks for perf budget enforcement.

---

## Methodology feedback

No new gaps. Pattern is well-established by run #9.

5 methodology gaps remain queued for add-skill v0.7.0 (no change from previous runs).