# VERIFICATION_REPORT — /sulis:jargon

**Skill:** `plugins/sulis/skills/jargon/SKILL.md`
**Authored via:** add-skill five-gate methodology (LIGHT tier — the skill is a one-setting toggle)
**Verification tier:** LIGHT
**Date:** 2026-05-26
**Verdict: PASS**

---

## Why LIGHT tier

This is the smallest founder-facing primitive in the marketplace: a session
toggle that flips one register default the Sulis agent body reads. It owns no
analysis, no facilitation, no destructive action, and no Python. The
dual-register *behaviour* is owned by the agent body and already verified
there; this skill only sets the default the body consults. LIGHT tier (the
five gates, but proportionate) is correct — STANDARD/HEAVY would be ceremony.

---

## Gate 1 — Find (collision check)

- **No existing skill named `jargon`** (full skill tree enumerated; 92+ skills
  across plugins; `ls plugins/sulis/skills/` confirms `jargon` was absent
  before this change). CC verdict: VALIDATED.
- Nearest neighbours and the boundary against each:
  - The `--raw` flag on any command — the **per-invocation** technical-mode
    request. `jargon` is the **session-wide** equivalent. Declared
    `related_to` via `../change/SKILL.md`. Distinct scope.
  - Natural-language intent ("give it to me straight") — the **per-response**
    request, owned by the agent body. `jargon` sets the default that intent
    overrides for a single response. Distinct scope.
- Vocabulary introduced: none new — "technical-mode" / "founder-mode" already
  exist in founder-facing-conventions.md Rule 6 and the Sulis agent body.

**Gate 1 verdict:** PASS.

---

## Gate 2 — Scope Lock

| Item | Lock |
|---|---|
| **Skill name** | `jargon` |
| **Plugin home** | `sulis` |
| **Audience** | **founder-facing** (Rules 1-6 apply; the confirmation sentence is the only founder-visible string) |
| **Category** | Founder UX & Navigation (register control) |
| **Trigger condition** | the `description:` — "Use when the founder wants Sulis to talk to them like an engineer for the rest of this session…" |
| **Standards-phase** | input: REFERENTIAL_INTEGRITY; output: TONE |
| **Verification tier** | LIGHT (single-setting toggle; no analysis, no Python, no destructive action) |
| **Mechanism** | session state file `.sulis/.session/jargon` (dot-prefixed private agent state), with `SULIS_JARGON` env var honored above it; per-response intent above both |

**Gate 2 verdict:** PASS.

---

## Gate 3 — Author

The skill body leads with the conclusion, states the three argument forms,
documents the session-state mechanism + precedence ladder, gives the
one-sentence confirmation strings for every case, and stops. It does **not**
restate the dual-register pattern (the agent body owns it — cited
`depends_on`). Size is proportionate to LIGHT tier.

**Gate 3 verdict:** PASS.

---

## Gate 4 — Verify

### Codebase Referential Integrity

Every cited path verified on disk:

| Cited entity | Path | Exists |
|---|---|---|
| Sulis agent body | `plugins/sulis/agents/sulis.md` | yes |
| Founder-Facing Conventions | `plugins/sulis/references/founder-facing-conventions.md` | yes |
| change skill | `plugins/sulis/skills/change/SKILL.md` | yes |

Referential integrity: **3/3.** No dangling references.

### Founder-readability perspective (founder-facing lock)

Founder-visible strings = the four confirmation sentences + the trigger
`description`. Each applies the FE-06 read-aloud test:

- "Switched to technical-mode for the rest of this session — `/sulis:jargon off` reverts." → PASS (one term, "technical-mode", glossed throughout the body as "the technical version").
- "Back to plain English — `/sulis:jargon on` switches to the technical version again." → PASS.
- The two no-argument status sentences → PASS (plain English, command in backticks).
- `description` → PASS (no operator jargon; "talk to them like an engineer" / "the raw, technical version" / "plain English").

Threshold (100% of founder-visible strings pass): **MET.**

The state-file path and env-var name appear only in the **mechanism** section
(operator-readable documentation), never in a founder-visible runtime string
— satisfying Rule 1 + the agent body's "internal taxonomy MUST NOT appear in
founder-readable output" rule.

### Register-default-check (MUC-R1)

The skill explicitly documents that the toggle sets a **default, not a lock**,
and the precedence ladder puts per-response intent above the session toggle.
Verified the body states this in two places (mechanism precedence list +
Gotchas). PASS.

**Gate 4 verdict:** PASS.

---

## Gate 5 — Adversarial sweep

Founder-facing skills must address ≥3 of MUC-F1..F5; dual-register skills
add ≥2 of MUC-R1..R3. Six cases below.

| # | Case | Scenario | Mitigation | Verdict |
|---|---|---|---|---|
| MUC-F1 | Operator-vocab leak | The confirmation echoes the state-file path or `SULIS_JARGON` env-var name to a founder | Confirmation strings are fixed plain-English sentences; path/env-var live only in the operator-readable mechanism section, never emitted at runtime unless the founder asked for the technical version | PREVENTED |
| MUC-R1 | Technical-mode leaks into founder default | Founder runs `/sulis:jargon on` once early, then a teammate (or the same founder weeks later) who never asked gets JSON-shaped replies because the toggle silently persisted | Toggle is **session-scoped** (`.sulis/.session/jargon`), not project-permanent or per-author durable; it dies with the session. Default without the file is founder-mode. Documented in the body and asserted here | PREVENTED |
| MUC-R3 | Register-switch ambiguity / toggle without persistence | Founder says "show me the raw output" expecting it to stick, but it was a one-off intent and the next reply reverts — or runs `/sulis:jargon on` but the agent doesn't read the file next turn | The skill draws the explicit line: per-response intent = one response; `/sulis:jargon on` = the session default the agent reads each turn from the state file. The precedence ladder makes "stick vs one-off" unambiguous. The agent body's routing reads the state file every turn | PREVENTED |
| MUC-F3 | Destructive action via ambiguous phrasing | Turning jargon on is read as permission to skip the destroy-prompt | Body states explicitly: technical-mode never skips Rule 3; only the prompt's language gets terser. No destructive shortcut is enabled by this toggle | PREVENTED |
| MUC-R2 | Founder-mode strips needed info | N/A to this skill — it does no translation itself; it only selects which register everything else uses. Load-bearing-identifier surfacing is the agent body's job | N/A (documented in Vocabulary: "this skill performs no operator→founder translation of its own") | N/A |
| Edge | No-argument call | Founder types `/sulis:jargon` with no on/off | Body specifies the read-and-report behaviour with two status sentences | PREVENTED |

Adversarial sweep: **5 PREVENTED, 1 N/A (justified).** Meets the ≥3 MUC-F
and ≥2 MUC-R thresholds (MUC-F1, F3 + MUC-R1, R3).

**Gate 5 verdict:** PASS.

---

## Final verdict

**PASS** across all five gates at LIGHT tier. The skill is the session-wide
entry-point for the dual-register pattern the Sulis agent body owns; it sets
a session default via private state, confirms in one sentence, and never
locks out per-response plain-English requests. No Python; referential
integrity 3/3; founder-readability 100%.
