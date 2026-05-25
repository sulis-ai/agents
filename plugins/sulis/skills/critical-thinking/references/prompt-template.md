# Critical Thinking Prompt Template

A copy-paste prompt structure for applying critical thinking to any analytical task.
Uses the [Critical Thinking Standard](critical-thinking-standard.md) as the
reasoning framework.

**Fetch the standard directly:**
- GitHub: https://github.com/sulis-ai/agents/blob/main/plugins/sulis/skills/critical-thinking/references/critical-thinking-standard.md
- Raw (for AI tools): https://raw.githubusercontent.com/sulis-ai/agents/main/plugins/sulis/skills/critical-thinking/references/critical-thinking-standard.md

---

## How to Use

Copy the template below. Fill in the bracketed sections. Either attach the standard
as a file or point the AI at the raw URL to fetch it. The standard does the heavy
lifting — your prompt just points the AI at it.

---

## The Template

```markdown
## 1. Task

I want to [WHAT YOU WANT TO ACHIEVE] so that [WHAT SUCCESS LOOKS LIKE].

## 2. Context Files

First, read these files completely before responding:

- Critical Thinking Standard — 13 analytical principles organised by phase
  (input/processing/output) and 9 anti-patterns. This governs how you reason.
  Fetch from: https://raw.githubusercontent.com/sulis-ai/agents/main/plugins/sulis/skills/critical-thinking/references/critical-thinking-standard.md
- [YOUR DOMAIN FILE] — [what it contains and why it matters]
- [YOUR DATA/EVIDENCE FILE] — [what it contains and why it matters]

## 3. Reference

Here is an example of what good output looks like for this kind of task:
[Attach an example, or describe the pattern, structure, and tone you expect.]

## 4. Brief

- Output type: [analysis / recommendation / comparison / validation / ...]
- Length: [short summary / detailed report / ...]
- Does NOT sound like: [marketing copy / academic paper / ...]
- Success means: [specific, verifiable criteria]

## 5. Rules

The Critical Thinking Standard is your reasoning framework. Apply it by phase:

**Input phase** — before you start:
- State the question you are answering and what would make the answer adequate (BI)
- Start from external evidence, not internal assumptions (OI)
- For every supporting search, conduct a counter-search (CI)
- Verify source independence — sources citing each other count as one (SI)
- Rank evidence by type — measured data beats expert opinion beats anecdote (HE)

**Processing phase** — while you reason:
- State what would falsify each claim (FR)
- Attach confidence levels calibrated to evidence, not conviction (CC)
- Ensure categories are MECE — no overlaps, no gaps, no fluff (MECE)
- Distinguish known facts, inferences, and assumptions (EH)
- Argue against your own conclusions before presenting them (AT)

**Output phase** — when you deliver:
- Lead with the conclusion, not the journey. Use SCQA for decisions (PP)
- No prohibited terms. Back every quantitative claim with a metric (PL)

If you are about to break one of these rules, stop and tell me.

## 6. Conversation

DO NOT start executing yet. Ask me clarifying questions so we can refine the approach
together before you begin work.

## 7. Plan

Before you write anything:
1. List the 3 principles from the Critical Thinking Standard that matter most for
   this specific task and why.
2. Give me your execution plan — what you will do, in what order, and what each
   step produces.

## 8. Alignment

Only begin work once we have aligned on the plan. Restate what you understand the
task to be, what success looks like, and which principles you will prioritise. I will
confirm or correct before you proceed.
```

---

## Adapting the Template

**For quick tasks** — skip sections 6–8. Use sections 1–5 for a single-shot prompt.

**For research** — emphasise Input phase rules (CI, SI, HE). Add: "Document all searches
attempted, including those that yielded nothing."

**For strategic decisions** — emphasise Processing phase (FR, CC, AT). Add: "Include a
pre-mortem: if this decision fails, what are the three most likely reasons?"

**For validation work** — emphasise AT (adversarial posture). Add: "Your job is to find
reasons this won't work, not reasons it will."

**For requirements** — emphasise OI (outside-in) and MECE. Add: "Derive requirements from
user evidence, not from existing system structure."

---

## What This Replaces

The old prompting era: "Act as a senior [role] with 20 years of experience."

The new approach: give the AI a reasoning framework, not a costume. The Critical Thinking
Standard tells it HOW to think. Your context files tell it WHAT to think about. The
template tells it WHEN to apply each discipline.

Roles are theatre. Standards are engineering.
