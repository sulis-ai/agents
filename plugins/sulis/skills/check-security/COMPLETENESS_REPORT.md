# Completeness Report — sulis:check-security

**Authored:** 2026-05-23
**Author:** Iain + Claude (dogfood run #6 of sulis:add-skill v0.4.0)
**Methodology:** `sulis:add-skill` v0.4.0 (five-gate)

## Verdict summary

| Gate | Status | Notes |
|---|---|---|
| 1 — Find | PASS | 5 overlaps all sibling-template; 0 vocab collisions; sulis-security:codebase-assess noted as deeper-scope sibling |
| 2 — Scope Lock | PASS | 7 items locked; v1 scope kept narrow (credentials + dangerous-patterns) to keep false-positive rate low |
| 3 — Generate | PASS | SKILL.md + scripts/scanner.py + references/security-patterns.md |
| 4 — Evaluate | PASS | Synthetic fixture with planted secret + real-state run against marketplace |
| 5 — Adversarial Review | PASS | 3 MUC-F + 3 audience-agnostic; 2 OPEN_RISK (false-positive risk + non-exhaustive scope) |

**Publication decision:** APPROVED

---

## Gate 1 — Find

5 overlaps all sibling-template (check-build, check-readability, check-tests, code-health) or coincidental (sea:code-review). No collisions. **Critically:** `sulis-security:codebase-assess` covers deeper security scope (25 primitives, OODA-spiral); this skill is the fast founder-facing pattern scan with baseline-aware regression. Documented as separate-purpose, not replacement.

---

## Gate 2 — Scope Lock

| Item | Locked value |
|---|---|
| Skill name | `check-security` |
| Plugin home | `sulis` |
| Audience | **both**. Founder default; `--raw` for operator JSON. Mode: explicit-flag |
| Category | **Founder UX & Navigation** (regression-detection sub-family) |
| Trigger condition | "Use when the founder wants to know if anything in the code could harm users or the business — scans for leaked credentials, dangerous patterns (eval, SQL injection, shell injection), and missing security basics. Read-only; never modifies code." |
| Top-5 gotchas | (below) |
| Depth modes | None for v1 |

### Top-5 gotchas

1. **Security false positives are scary.** A founder seeing "AWS_SECRET_ACCESS_KEY in your code" panics. We MUST keep false-positive rate low — only flag high-confidence patterns. Same problem the sulis-security CQ-04 finding showed when sea:probe's first version over-flagged. *Source: HD-013 prior art + sulis-security tier 2 known issues.* Mitigation: pattern allowlist (known test fixtures, doc examples like `AKIA1234567890ABCDEF` in security primitives); high-confidence patterns only in v1.

2. **Test fixture credentials look like real leaks.** The marketplace has `leaked_key.py` and similar files in `tests/fixtures/` that intentionally contain fake AWS keys. Mis-flagging these would cry wolf. *Source: this exact pattern surfaced when check-readability ran against the marketplace and flagged the fixture file under jargon-density.* Mitigation: same fixture-path skip as check-readability; document the allowlist convention.

3. **Pattern-based security is necessarily incomplete.** This skill catches LOW-HANGING fruit; it does NOT catch sophisticated vulnerabilities (auth-bypass logic errors, race conditions, business-logic flaws). Founders may assume "passed check-security = safe" — that's wrong. *Source: every static-analysis tool's perennial problem.* Mitigation: explicit "this is the basics — for thorough security analysis, use sulis-security:codebase-assess" pointer.

4. **First-run has no baseline.** Same as check-tests/check-build. Mitigation: first run captures baseline; explicitly says so; never silent.

5. **Founder might expect this to FIX security issues.** Universal read-only audit ambiguity. *Source: cross-skill pattern from check-readability, check-tests, code-health, check-build.* Mitigation: "this skill never modifies code — only reports."

### Vocabulary terms

- **credential-leak** — a string in source code matching a high-confidence credential pattern (AWS key, GitHub token, etc.) without being on the allowlist
- **dangerous-pattern** — code construct with known security risk (eval, exec on user input, SQL string concatenation)
- **security-finding** — generic term for any check-security finding (covers credential-leak + dangerous-pattern + future categories)
- **high-entropy-string** — a string with Shannon entropy above a threshold, typically indicating a key/token/secret. Heuristic with documented false-positive trade-offs.
- **secret-pattern** — a regex matching a known credential format (AWS_*, ghp_*, sk-*, etc.) — high-confidence; opposite end of the false-positive spectrum from high-entropy heuristics

---

## Gate 3 — Generate

**Files:**

- `SKILL.md` — entrypoint; three-mode invocation; founder/operator modes
- `scripts/scanner.py` — pattern catalogue + scanner + baseline + delta
- `references/security-patterns.md` — pattern catalogue with examples + false-positive notes
- `COMPLETENESS_REPORT.md` — this file

---

## Gate 4 — Evaluate

### P1 Trigger accuracy: PASS
- "is the code secure?" / "any leaked credentials?" → triggers correctly
- "deep security audit" → could trigger but should route to sulis-security; documented in "When NOT"

### P2 Gotchas coverage: PASS
All 5 sourced.

### P3 Functional completeness: PASS
- Real-state test against marketplace: ran scanner; **caught the test-fixture AWS key in `plugins/sulis/skills/analyse-codebase/tests/fixtures/polyglot_monorepo/apps/api/src/leaked_key.py`** correctly identified AND correctly allowlisted (fixture path)
- Synthetic fixture with planted real-looking credential: caught with high severity
- Synthetic fixture with `eval(user_input)`: caught
- **Cross-skill:** check-readability run on scanner.py = 0 findings (clean code)

---

## Gate 5 — Adversarial Review

### MUC-F1: Jargon leak — PREVENTED
Pattern names (regex patterns, entropy scores) stay operator-side; founder mode says "looks like an AWS access key" not "matched regex `^AKIA[0-9A-Z]{16}$`".

### MUC-F3: Destructive action — PREVENTED
"This skill never modifies code" stated 3 places.

### MUC-F4: Overwhelm — PREVENTED  
v1 scope kept narrow (credentials + dangerous-patterns only) precisely to avoid overwhelming with false positives.

### MUC-F5: Stale-state false-positives — PARTIALLY PREVENTED
Allowlist for known fixture paths + explicit `--allowlist-add PATTERN` for project-specific waivers. OPEN_RISK: founder may add a real secret to allowlist by mistake; documented.

### Audience-agnostic — Authorization leakage — PREVENTED
No external tools required (pure regex); no false claim of completeness (v1 scope documented).

### Audience-agnostic — Trigger condition matches too broadly — PARTIALLY PREVENTED  
"Is the code secure?" could overlap with sulis-security:codebase-assess. "When NOT to invoke" names that skill explicitly. OPEN_RISK: ambiguity persists until both skills are well-known.

---

## Open risks

1. **Non-exhaustive scope by design.** Pattern-based; misses sophisticated vulns. Documented in SKILL.md; sulis-security:codebase-assess is the depth-first alternative. **revisit_by:** never — this is by-design, not a defect.

2. **Allowlist abuse.** Founder might add a real secret to the allowlist thinking it's a fixture. **revisit_by:** event — founder reports allowlist-abuse incident.

---

## Methodology feedback (run #6)

3 new gaps for add-skill v0.6.0:

1. **Security skills need a "false-positive philosophy" gate item.** Other skills don't, but security FP rate matters more than coverage. Worth adding to Gate 2 for skills audit=security.
2. **Allowlist pattern is now consistent across three skills** (check-readability for vocab, check-tests for flaky tests, check-security for known secrets). Worth extracting a shared `allowlist_loader.py` helper.
3. **Cross-skill validation pattern is genuinely working.** Three skills built; each tested via check-readability on its own code; all came back clean. Worth documenting this pattern in the methodology as "self-test via sibling skills."

20 methodology gaps queued for add-skill v0.6.0.