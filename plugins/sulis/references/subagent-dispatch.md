# Subagent Dispatch

<!-- summary -->
Decision rules for "spawn vs recommend" per specialist. This v0.1.0
release uses the **recommend** pattern exclusively (founder runs slash
commands, concierge reads produced artifacts). v0.2 adds Agent-tool
spawning for short-running specialists (sulis-context, sea:verify,
sulis-security). Long-running interactive specialists (SRD, SEA
blueprint, SEA decompose) always remain recommend-only.
<!-- /summary -->

> **Version:** 0.1.0
> **Status:** Active — recommend-only pattern in v0.1.0; spawning added in v0.2.

---

## Pattern: Recommend (v0.1.0 — all specialists)

The concierge surfaces a paste-ready slash command in plain English. The
founder runs it. The specialist's session is interactive and lives in
the founder's terminal. When the founder returns to the concierge, the
concierge reads the produced artifacts and continues.

**Why recommend (v0.1.0 default):**
- Cross-plugin Agent-tool spawning is not an established marketplace
  pattern. Pioneering it requires careful design of context handover,
  long-running conversation handling, and return control.
- Long-running interactive specialists (SRD facilitation, SEA blueprint
  conversation) genuinely need the founder in the loop — spawning them
  silently would lose the conversational nature of the work.
- Recommend is simpler to debug: the founder sees exactly what's
  happening; the concierge sees exactly what was produced.

**The recommendation shape** (action-then-report, AAF-08 compliant):

> *"Now [plain-English description]. Run this when you're ready:*
>
> *`/[specialist:command]`*
>
> *When it's done, come back to me."*

Never use forbidden permission-theater shapes:
- *"Want me to tell you the next command?"* ✗
- *"Should I recommend something?"* ✗

Just announce:
- *"Run `/sea:blueprint` next."* ✓

---

## Specialist Dispatch Table

| Specialist | Command | This release (v0.1) | v0.2 plan |
|---|---|---|---|
| sulis-context (discover) | `/sulis-context:discover` | recommend | spawn (short, returns INDEX.md) |
| sulis-context (refresh) | `/sulis-context:refresh` | recommend | spawn (short) |
| srd:requirements-analyst | `/srd:start` | recommend | recommend (always; long conversation) |
| srd:requirements-validation | `/srd:requirements-validation` | recommend | spawn (short, returns COMPLETENESS_REPORT.md) |
| sea:blueprint | `/sea:blueprint` | recommend | recommend (always; long conversation) |
| sea:decompose | `/sea:decompose` | recommend | spawn (short, autonomous) |
| sea:verify | `/sea:verify` | recommend | spawn (short, returns COMPLETENESS_REPORT) |
| sulis-execution:executor | `/sulis-execution:run-all` | recommend (this WP-execution plugin ships in same v1.12.0 release) | spawn (long but autonomous) |
| sulis-security:codebase-assess | `/sulis-security:codebase-assess` | recommend | spawn (short-to-medium, returns report) |

---

## When to Recommend vs Spawn (v0.2 criteria)

A specialist is a **spawn candidate** if:
- Output is a single artifact (or small set of artifacts) returned in a
  bounded time (≤ 5 minutes typical).
- No interactive multi-turn conversation with the founder is needed.
- The specialist's work can be summarised in a few sentences after.

A specialist is **recommend-only** if:
- The work requires a long interactive conversation with the founder
  (SRD facilitation, SEA blueprint discussions, brand-discovery
  one-question-at-a-time facilitation).
- The founder benefits from being in the specialist's session
  conversationally (asking clarifying questions, exploring tangents).
- The specialist asks for founder input multiple times before producing
  the artifact.

The v0.2 spawning addition follows this classification strictly. v0.1.0
uses recommend for everything to establish the pattern reliably first.

---

## Version History

| Version | Date | Change | Author |
|---|---|---|---|
| 0.1.0 | 2026-05-16 | Initial dispatch table. Recommend-only pattern. v0.2 will add spawning for short-running specialists. | Standards team |
