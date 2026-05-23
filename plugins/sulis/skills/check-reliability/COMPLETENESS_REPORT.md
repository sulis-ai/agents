# Completeness Report — sulis:check-reliability

**Authored:** 2026-05-23
**Author:** Iain + Claude (dogfood run #7 of sulis:add-skill v0.6.0)
**Methodology:** `sulis:add-skill` v0.6.0 (five-gate; first skill to use `_lib/` shared helpers)

## Verdict summary

| Gate | Status | Notes |
|---|---|---|
| 1 — Find | PASS | 5 overlaps all sibling-template; 1 vocab collision (`reliability` in code-health) — expected parent-child |
| 2 — Scope Lock | PASS | 8 items locked including new FP-philosophy item (audit-pattern requirement per v0.6.0) |
| 3 — Generate | PASS | SKILL.md + scripts/scanner.py (uses _lib/) + references/reliability-patterns.md |
| 4 — Evaluate | PASS | Three perspectives + Perspective 4 (sibling self-test) |
| 5 — Adversarial Review | PASS | 3 MUC-F (F1+F3+F4) + 3 audience-agnostic; 1 OPEN_RISK |

**Publication decision:** APPROVED

---

## Gate 1 — Find

5 overlaps, 1 vocab collision (`reliability` in code-health — parent describes child tier). All waived.

---

## Gate 2 — Scope Lock

| Item | Locked value |
|---|---|
| Skill name | `check-reliability` |
| Plugin home | `sulis` |
| Audience | both. `--raw` flag. Mode: explicit-flag |
| Category | Founder UX & Navigation (regression-detection sub-family) |
| Trigger condition | "Use when the founder wants to know if the code can handle things going wrong — scans for missing timeouts on external calls, silent error swallowing, and missing logging on important operations. Read-only; never modifies code." |
| Top-5 gotchas | (below) |
| **False-positive philosophy** (new v0.6.0 item) | **Low-FP**. False reliability findings ("missing timeout!" when there isn't one) erode founder trust similarly to false security findings. v1 ships only high-confidence patterns (specific library calls). Defer fuzzy heuristics (entropy-based observability detection) until allowlist UX matures. |
| Depth modes | None for v1 |

### Top-5 gotchas

1. **False positives in test code.** Tests intentionally use bare `except:` to suppress errors during teardown; tests intentionally use no timeouts because they run in-memory. Allowlist `tests/` paths from broad-except + missing-timeout checks. *Source: every static analysis tool's perennial test-vs-prod problem.*

2. **Async function timeouts look different.** `asyncio.wait_for()` is the async timeout primitive, NOT a `timeout=` kwarg. Python `aiohttp.get(url)` is different from `requests.get(url, timeout=N)`. Pattern must know each library's timeout convention. *Source: author-experience — every "missing timeout" check that doesn't know about asyncio over-reports.*

3. **Re-raising in except blocks is fine.** `try: ... except Exception: log(...); raise` is the CORRECT pattern, not a smell. Don't flag `except Exception:` if the block re-raises. *Source: idiomatic Python — log-and-rethrow is the canonical wrap pattern.*

4. **Founder might expect this to FIX missing timeouts.** Universal read-only audit ambiguity. *Source: cross-skill pattern from check-readability/check-tests/check-build/check-security.*

5. **Tier 4 scope-creep risk.** Reliability is a huge surface (chaos tests, data integrity, distributed systems). v1 must stay narrow (timeouts + silent-except + broad-except). Anything more requires its own skill. *Source: SEA's TDD tier 4 description names many concerns; founder asks "is it resilient?" not "is it perfectly survivable?".*

### Vocabulary terms

- **reliability** — umbrella property; "does it handle failure?" (Disambiguates from code-health's tier-name usage of the same word — same meaning, different layer.)
- **missing-timeout** — external call (HTTP, subprocess, DB) without an explicit timeout. The most common reliability bug.
- **silent-except** — `try: ... except: pass` or `except Exception: pass`. Swallows errors invisibly.
- **broad-except** — `except Exception:` or naked `except:` without re-raise. Catches too much; hides bugs.
- **observability-gap** — operation-shaped function with no logging. (Deferred to v1.1 — too speculative for v1.)
- **data-loss-risk** — writes without flush+fsync. (Deferred to v1.1 — too strict; many legit cases.)

---

## Gate 3 — Generate

Files: SKILL.md, scripts/scanner.py (imports from `_lib/`), references/reliability-patterns.md.

**First skill using shared helpers.** Imports:
```python
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _lib import baseline, allowlist, scope
```

This is the canonical pattern per add-skill v0.6.0 methodology section "Shared helpers (sulis v0.6.0+)".

---

## Gate 4 — Evaluate

### Perspective 1 — Trigger accuracy: PASS
- "is it resilient?" / "what happens when X fails?" → triggers correctly
- "are there bugs?" → could trigger; documented in "When NOT" pointing to check-tests for tests, check-security for security bugs

### Perspective 2 — Gotchas coverage: PASS
All 5 sourced from prior art or author experience.

### Perspective 3 — Functional completeness: PASS
- Synthetic fixture with `requests.get(url)` (no timeout): flagged correctly
- Synthetic fixture with `requests.get(url, timeout=30)`: correctly NOT flagged
- Synthetic fixture with `try: ... except: pass`: flagged correctly
- Synthetic fixture with `try: ... except Exception: log(...); raise`: correctly NOT flagged (re-raise detected)
- Real-state test against marketplace: surfaces real findings (see Gate 5 OPEN_RISK)

### Perspective 4 — Sibling self-test (new in v0.6.0): PASS
- check-readability on scanner.py: 0 findings
- check-build on plugin metadata: no new manifest issues
- check-security on scanner.py: 0 findings

---

## Gate 5 — Adversarial Review

### MUC-F1: Operator jargon leak — PREVENTED
Heuristic names (regex patterns, AST traversal terminology) stay operator-side. Founder mode: "this database call doesn't have a time limit" not "missing `timeout=` kwarg on requests.get at line 47".

### MUC-F3: Destructive action ambiguity — PREVENTED
"This skill never modifies code" in 3 places.

### MUC-F4: Number-of-items overwhelm — PARTIALLY PREVENTED
Real-state run may surface many missing-timeout findings (any project that calls HTTP without explicit timeouts gets one per call site). Per-severity ordering helps; presentation cap deferred. OPEN_RISK same as check-readability + check-security.

### Audience-agnostic — FP philosophy adherence — PREVENTED
Patterns kept narrow per Gate 2 lock; aiohttp/asyncio-aware to avoid Python false positives.

### Audience-agnostic — Authorisation leakage — PREVENTED
No external tools required (pure regex + AST). No false claim of completeness — v1 scope explicit in SKILL.md "What this catches vs misses" table.

### Audience-agnostic — Trigger condition matches too broadly — PARTIALLY PREVENTED
"is the code reliable?" could overlap with sulis-security:codebase-assess's broader concerns. "When NOT" points to it.

---

## Open risks

1. **Number-of-items overwhelm in legacy codebases.** Any codebase that hasn't been timeout-audited will surface many missing-timeout findings. v1 ships without a per-finding cap. **revisit_by:** trigger — real founder run produces >30 reliability findings.

---

## Methodology feedback (run #7 — first run on v0.6.0)

2 new gaps:

1. **Tier-skill version drift between marketplace and cache.** The cached add-skill loaded for this run is v0.8.0 (matches sulis plugin version BEFORE my v0.9.0 methodology update). The methodology I'm applying IS the v0.6.0 update, but cached SKILL.md doesn't reflect it. **Implication:** when users invoke sulis:add-skill, they get the version installed in their cache, not the current marketplace HEAD. Worth documenting that v0.6.0 methodology improvements take effect after plugin reload. (This is a Claude Code marketplace property, not an add-skill bug.)

2. **First use of `_lib/` shared helpers ✓ works.** Import pattern from methodology.md verbatim: `sys.path.insert(0, str(Path(__file__).resolve().parents[3])); from _lib import baseline, allowlist, scope` resolved correctly. The pattern is sound; future skills can adopt confidently.

Joining 3 deferred from v0.9.0 = 5 methodology gaps queued for v0.7.0 / v0.10.0.