# Add-Agent Methodology — Why Each Gate Exists

Companion to `SKILL.md`. The SKILL is the operational checklist; this document is the rationale.

If you've read `add-skill/references/methodology.md` (which this document parallels), 80% of the content is identical — the methodology is the same five-gate structure. This document covers the 20% that's agent-specific: dispatch contract, register declaration, founder-mode evaluation perspectives, and the four MUC-A misuse cases.

## Why agents need their own authoring methodology

`add-skill` v0.7.0 covers skills excellently. Two things make agents different enough to warrant their own meta-skill:

1. **The dispatch contract is load-bearing.** A skill is invoked by name (`/sulis:add-skill`); the user types it explicitly. An agent is invoked by a parent agent based on description matching — the description IS the dispatch contract. A vague description causes dispatch chaos across the entire agent tree. A skill's `description:` is important; an agent's is *critical*.

2. **Agents carry register state.** Skills produce output; agents have ongoing conversational context. Dual-register support (default founder-mode + on-request technical-mode) is a stateful concern with switching mechanics — it has to be designed in, verified, and adversarial-tested differently from how skills produce founder-readable strings.

Both differences concentrate at Gates 2, 4, and 5. The rest of the methodology is `add-skill` applied to agent files.

## Gate 1 — Find: Why deterministic-first

### What failure mode it prevents

Authoring an agent without checking the existing agent inventory leads to **dispatch collisions** — the parent agent has two agents with overlapping descriptions and routes inconsistently. Worse, the new agent might duplicate functionality already covered by another, splitting maintenance and confusing dispatchers.

A subtler failure: authoring an agent for work that should have been a skill. Agents are heavier — they carry context, tool budgets, dispatch overhead. The BRIEF_PACK forces the "could this be a skill instead?" question to be answered with evidence, not by default.

### Why BRIEF_PACK before Claude interpretation

Determinism for the parts a script does better (listing files, checking name collisions, gathering descriptions); LLM judgment for the parts only Claude does well (semantic overlap, "could this be a skill", primitive decomposition).

The pattern from `add-skill`'s methodology applies verbatim: the script is the floor; Claude's interpretation is the ceiling.

### Why Primitive Discovery for agents

Agents own stages, dispatch triggers, or specialised work. Without explicit decomposition into primitives (per PG-01..04 + PD-01..06), the agent ends up with overlapping responsibilities (a stage agent that ALSO classifies depth modes that ALSO orchestrates dispatch) and the dispatch contract becomes muddy.

Primitive Discovery for agents tends to be shallower than for skills (the typical agent owns 2-5 primitives, not 10-20). Shallow is fine — the test isn't depth, it's whether the primitives pass PG-02 (independent) and PG-04 (termination).

## Gate 2 — Scope Lock: Why before drafting

### What failure mode it prevents

Scope creep during drafting. Without a Scope Lock, the agent body grows to absorb every adjacent concern as it occurs to the author. By the time the agent is "done," it does six things, dispatches three other agents, declares ten tools, and reads twelve standards — none well.

### Why the dispatch trigger is in the lock

Because the dispatch trigger is the highest-impact text in the entire agent, Gate 3 (Generate) writes the description into the frontmatter, and from then on it's the contract. Writing it BEFORE drafting forces the author to think about *when* the agent should be dispatched before thinking about *what* the agent does internally. The "when" determines the "what."

### Why register declaration is binding

Once `register: { founder_mode: default, technical_mode: { ... } }` is declared, Gate 4 verifies the switch mechanics actually work. Declaring dual-register without implementing the switch = Gate 4 fails. Not declaring it on a founder-facing agent = Gate 4 fails differently (Tone Conformance + Coaching Delivery scored without a register fallback).

Lock at Gate 2 so the body in Gate 3 is structurally aware of both modes.

### Why "could this be a skill" must be answered

This is the cheapest possible defence against over-using the agent primitive. Agents are heavyweight; skills are lightweight. If the work can be done as a skill (single conversational turn, no ongoing context, no need for distinct role definition), use a skill. Document the answer in VERIFICATION_REPORT so future maintainers see the reasoning.

## Gate 3 — Generate: Why MECE + Pyramid + SCQA

### What failure mode it prevents

Agents that bury the role definition under a wall of workflow detail. The parent agent's first scan reads the description; the second (if dispatched) reads the agent body. If the body doesn't lead with "this is what you are and what you do," the dispatched-into-agent context is wasted on figuring out the role rather than executing it.

### Why the agent body shape matters

A skill's body is consumed when the skill is invoked. An agent's body is consumed every time the agent is dispatched. The agent body shape recurs in every dispatch — getting it wrong has a multiplicative cost.

The standard shape:

```
1. Role (one paragraph — what you are)
2. Required reading (if any — list of standards/references)
3. Workflow / Main loop / When dispatched (what you do)
4. Output shape / Output contract (what you produce — founder-mode AND technical-mode)
5. Gotchas + Vocabulary (optional but encouraged)
```

### Why progressive disclosure matters more for agents

Agents are dispatched many times during a session. Each dispatch pays the cost of loading the agent body into the dispatched-agent's context window. If the body inlines standards or reference content, every dispatch pays that cost. Progressive disclosure (link, don't inline) keeps dispatched-agent context lean.

## Gate 4 — Evaluate: Why three new perspectives for founder-facing

### Coaching Delivery — what it catches

Forgetting to apply COACHING_STANDARD even though it's declared. The seven-question Pass/Fail checklist surfaces:

- Prescriptive language in recommendations ("You need to...")
- Personal framing of structural issues ("Your code has...")
- Conclusion-shaped sentences where hypothesis-shaped would land better
- Missing room-to-step-up framing
- Premature directness (before relationship capital)

These are silent failures otherwise — the agent emits "correct" content that triggers defensiveness, the founder doesn't act on it, and the agent's effective value is zero.

### Tone Conformance — what it catches

The TONE forbidden-vocabulary list is the most reliable Gate 4 catch — agents trained on general English drift toward "comprehensive," "robust," "powerful," "leverage," "magic," "seamless" by default. The Tone Conformance perspective is a focused linguistic audit that runs against the agent's emitted strings, not just the agent body.

Three sub-checks:

1. **Forbidden vocabulary scan** — grep for banned terms in declared founder-mode examples
2. **Preferred vocabulary application** — verify TONE Section A preferred terms used where applicable
3. **Established-term preservation** — verify no novel replacements for "MVP" / "PR" / "guardrails" etc.

### Register Switch Correctness — what it catches

The mechanics of register switching are subtle. Three failure modes the perspective catches:

1. **Intent miss** — agent doesn't recognise "show me the technical version" / "give it to me straight" / "raw output" as switch triggers
2. **Default leak** — agent emits technical-mode content even though no switch trigger fired (founder-mode should be default)
3. **Session toggle ignored** — agent doesn't read `SULIS_JARGON` env var (or equivalent) and keeps emitting founder-mode after `/sulis:jargon on`

For dual-register agents, this perspective is non-negotiable — the dual-register declaration is a promise; this perspective verifies the promise holds.

## Gate 5 — Adversarial Review: Why MUC-A1..A4

### What MUC-A catches that MUC-F doesn't

`founder-facing-conventions.md` defines MUC-F1..F6 for founder-facing skills. Those apply to agents too. But agents have additional failure modes because:

1. **Agents have ongoing context** — a coaching failure compounds across the conversation
2. **Agents dispatch other agents** — a banned-vocabulary leak in this agent might propagate to dispatched specialists
3. **Agents produce many outputs per session** — a missing-commercial-outcome failure happens on every status report, every ship summary

MUC-A1..A4 are the agent-specific instances of these multiplied failures:

- **MUC-A1 (Prescriptive leak)** — agent forgot COACHING; "You need to fix this" lands wrong
- **MUC-A2 (Banned vocabulary leak)** — agent forgot TONE; "We have a powerful solution" lands wrong
- **MUC-A3 (Defensive-trigger leak)** — agent surfaces finding without COACHING Tenet 1 framing
- **MUC-A4 (Missing outcome)** — agent reports completion without TONE T-03 commercial framing

All four MUST be addressed for founder-facing or both agents — they're table-stakes for any founder-facing agent.

### Why MUC-R1..R3 are dual-register-specific

Register switching is a stateful concern unique to dual-register agents. MUC-R1..R3 are the three failure shapes:

- **MUC-R1 (Mode leak)** — technical-mode content emitted in founder-mode default
- **MUC-R2 (Signal drop)** — founder-mode strips an identifier that was load-bearing signal
- **MUC-R3 (Switch ambiguity)** — "more detail" misinterpreted as switch-to-technical rather than deepen-founder-mode

All three MUST be addressed for any agent declaring dual register.

## The mode-detection heuristic

When `add-agent` is invoked, it auto-detects which mode applies:

| Heuristic | Mode |
|---|---|
| `plugins/<plugin>/agents/<agent-name>.md` does NOT exist | Greenfield |
| File exists AND has `verification_spiral:` frontmatter block | Deepening (upsurge) |
| File exists AND lacks `verification_spiral:` frontmatter block | Standards-grounded re-author |

The author can override via explicit `--mode greenfield|deepen|re-author` flag if the heuristic is wrong.

## When to skip a gate (almost never)

The only documented skip case: pure-classifier agents (LIGHT tier) skip the Primitive Discovery sub-step of Gate 1 — record one paragraph of "this agent owns the classifier function" and move on. Everything else runs every time.

If you find yourself wanting to skip more, the agent is probably miscategorised — re-examine whether it should be a skill instead.

## Why VERIFICATION_REPORT.md lives next to the agent

Skills live in their own directory (`plugins/<plugin>/skills/<skill-name>/`) which naturally hosts the verification report alongside. Agents live as single files (`plugins/<plugin>/agents/<agent>.md`) with no host directory.

The convention: VERIFICATION_REPORT.md sits next to the agent file in `plugins/<plugin>/agents/<agent>.VERIFICATION_REPORT.md` (dot-prefixed pattern would conflict with Claude Code conventions; suffix form chosen). Deepening iterations live at `plugins/<plugin>/agents/iterations/<agent-name>/{N}/VERIFICATION_REPORT.md` to preserve history.

The single filesystem check is unchanged: `test -f ... && grep "Verdict:.*PASS"`.

## How the dispatched-trigger BRIEF_PACK works

The inventory script (`scripts/inventory.py`) walks every plugin's `agents/` directory and parses each agent file's frontmatter. For each agent, it extracts:

- name (the subagent_type)
- description (the dispatch trigger)
- plugin home
- audience (parsed from body or frontmatter if present)
- tools (declared list or `*`)
- model preference (if declared)

It then performs three analyses:

1. **Name collision** — proposed agent name vs existing agent names in the marketplace
2. **Description overlap** — semantic similarity scoring (basic substring matching + keyword overlap) between proposed description and existing descriptions
3. **Tool overlap** — for the proposed tool list, which existing agents declare similar tool sets (signals potential functional overlap)

Output: structured Markdown BRIEF_PACK for Claude to interpret.

## Composition with `add-skill`

The recommended pattern when adding new sulis surface area:

1. Use `add-skill` for skills the agent dispatches (the agent is a thin coordinator over skills)
2. Use `add-agent` for the agent itself
3. Reference skills from the agent via `related_skills:` with `relationship: optional_input` (the agent CAN dispatch them) or `depends_on` (the agent MUST dispatch them)

Both use the same five-gate methodology, same SPIRAL_TEMPLATES rubric, same VERIFICATION_REPORT.md format — the workflows compose cleanly.

## When `add-agent` would itself be deprecated

If Claude Code's agent shape changes meaningfully (e.g., agents gain templates / scripts / subdirectories like skills currently have, or the dispatch model changes from subagent_type-string to something richer), this skill would need to be re-authored against the new shape. The methodology (five gates, eight standards) would persist; the gate-content would adapt.

Until then, this skill is the canonical methodology for authoring agents in the Sulis marketplace.
