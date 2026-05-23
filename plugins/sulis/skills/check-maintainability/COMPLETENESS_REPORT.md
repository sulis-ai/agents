# Completeness Report — sulis:check-maintainability

**Authored:** 2026-05-23
**Author:** Iain + Claude (dogfood run #8 of sulis:add-skill v0.6.0)

## Verdict summary

| Gate | Status | Notes |
|---|---|---|
| 1 — Find | PASS | 5 sibling-template overlaps; 1 vocab collision (`maintainability` in code-health) — parent-child |
| 2 — Scope Lock | PASS | 8 items locked; FP-philosophy: advisory-default (dead-code detection has inherent FP rate from dynamic dispatch) |
| 3 — Generate | PASS | SKILL.md + scripts/scanner.py (uses _lib/) + references/dead-code-patterns.md |
| 4 — Evaluate | PASS | 3 perspectives + Perspective 4 sibling self-test |
| 5 — Adversarial Review | PASS | 3 MUC-F + 3 audience-agnostic; 2 OPEN_RISK |

**Publication decision:** APPROVED

---

## Gate 2 — Scope Lock

| Item | Value |
|---|---|
| Skill name | `check-maintainability` |
| Plugin home | `sulis` |
| Audience | both. `--raw` flag |
| Category | Founder UX & Navigation |
| Trigger | "Use when the founder wants to know if the code will be easy to change later — scans for dead code (unused functions, classes, imports) that accumulates and makes future changes harder. Read-only; never modifies code." |
| FP philosophy | **Advisory-default.** Dead-code detection has inherent FP rate (dynamic dispatch, reflection, plugin systems, test introspection). v1 ships ALL findings at `advisory` severity — founder reviews each rather than auto-acting. No `high`/`concern` from this skill. |
| Top-5 gotchas | (below) |
| Depth modes | None for v1 |

### Top-5 gotchas

1. **Dynamic dispatch is invisible to static analysis.** `getattr(module, name)`, `globals()[name]`, plugin-registration systems all reference functions by string. Static scan flags them as "unused" — false positive. *Source: vulture / ts-prune universal limitation.* Mitigation: advisory-only severity; allowlist for known-dynamic patterns; SKILL.md says "review each finding before deleting."

2. **Test introspection patterns hide usage.** pytest finds tests by name convention (`test_*`); fixtures by `@pytest.fixture`; conftest auto-imports. Static scan can't see these. Mitigation: skip `tests/`, `conftest.py`, anything matching `test_*` from scanning (don't audit them for dead code).

3. **Plugin/skill systems load by convention.** Claude Code skills are loaded by `SKILL.md` discovery; agents by `agent.md` discovery. Functions referenced from those files are "used" but a Python-AST scan won't see it. Mitigation: skip the marketplace itself (special-case sulis plugins) OR document the known-blind-spot.

4. **Public API surface looks unused if you're the library.** A function exported as `__all__` or a package's public API can have zero internal callers but many external ones. Mitigation: skip `__init__.py` exports + functions matching `__all__`.

5. **Founder might expect this to DELETE dead code.** Universal read-only ambiguity. Mitigation: SKILL.md says "this skill never modifies code" 3 places; suggestions are "consider removing if confirmed unused" not "remove".

### Vocabulary

- **maintainability** — umbrella property: "can we change this later without breaking things?" (Disambiguates from code-health's tier-name use.)
- **dead-code** — a symbol (function / class / variable / import) with no detected references elsewhere in the codebase.
- **unused-symbol** — singular noun for an individual dead-code finding.
- **reference-graph** — the static-analysis graph of symbol-to-callers used to detect dead code.
- **advisory-severity** — the FP-philosophy lock: ALL findings ship as advisories; founder reviews before acting.

---

## Gate 3 — Generate

Files: SKILL.md, scripts/scanner.py (uses `_lib/`), references/dead-code-patterns.md.

---

## Gate 4 — Evaluate

### P1 Trigger accuracy: PASS
- "is my code maintainable?" / "any dead code?" / "stuff I can delete?" → triggers correctly

### P2 Gotchas coverage: PASS
All 5 sourced (vulture limitation, test introspection, plugin systems, public API, read-only ambiguity).

### P3 Functional completeness: PASS
- Synthetic fixture with unused function: flagged correctly
- Synthetic fixture with `getattr()`-referenced function: NOT flagged (allowlist + heuristic exemption)
- Real-state run against marketplace: produces advisory findings

### P4 Cross-skill self-test: PASS
- check-readability on scanner.py: 0 findings
- check-security on scanner.py: 0 findings
- check-reliability on scanner.py: 0 findings

---

## Gate 5 — Adversarial Review

### MUC-F1: Operator jargon — PREVENTED
Heuristic names + AST terminology stay operator-side.

### MUC-F3: Destructive ambiguity — PREVENTED
"Never modifies code" stated 3 places; suggestions are "consider removing if confirmed" not "remove".

### MUC-F4: Overwhelm — PARTIALLY PREVENTED
Advisory-default severity prevents false-urgency. Per-category presentation. OPEN_RISK: legacy codebases may surface 100+ findings — same overwhelm as other audit skills.

### Audience-agnostic — FP-philosophy adherence — PREVENTED
ALL findings ship at `advisory` per the Gate 2 lock. Skill body documents why (dead-code detection FP-prone by nature).

### Authorisation leakage — PREVENTED
No external tools. v1 limit (Python-only) explicit.

### Trigger too broad — PARTIALLY PREVENTED
"is my code maintainable?" could overlap with check-reliability (resilience). "When NOT" points to the right alternatives.

---

## Open risks

1. **Number-of-items overwhelm in legacy codebases.** revisit_by: trigger — real founder run >50 findings.
2. **Dynamic-dispatch false positives.** Inherent to static dead-code detection. Allowlist mitigates; founder still must review each.

---

## Methodology feedback (run #8 — second on v0.6.0)

1 new gap:
- **Audit-pattern skills with high inherent FP rate should advertise the rate.** check-maintainability is the first skill where the FP-philosophy lock is "advisory-default" because the static-analysis limit is fundamental. Worth adding a "FP-rate disclosure" to the Gate 4 perspective list — give founders calibration.

Joining 5 queued = 6 methodology gaps for v0.7.0.