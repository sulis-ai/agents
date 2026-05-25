---
name: critical-thinking
description: >
  Apply the Critical Thinking Standard to the current task. Loads the three-phase
  reasoning framework (input/processing/output), identifies which principles matter
  most, and structures the work accordingly. Use when analytical rigour is needed.
user_invocable: true
---

# Critical Thinking

When invoked, apply the Critical Thinking Standard to the current task or conversation.

If arguments are provided, treat them as a description of the task to analyse.
If no arguments are provided, apply critical thinking to the most recent task or
question in the conversation.

---

## What This Skill Does

This skill loads the Critical Thinking Standard and applies its three-phase model to
the current work. It does not produce a deliverable — it structures HOW you think
about the work before and during execution.

---

## Execution

### Step 1: Load the Standard

Read `references/critical-thinking-standard.md` completely. This is your reasoning
framework for the duration of this task.

### Step 2: Frame the Task (Input Phase)

Apply BI (Begin with Inquiry):

1. State the question this task answers
2. State what success looks like
3. State what would make the answer adequate

Then identify which Input phase principles are most relevant:
- Does this task involve gathering evidence? → CI (Counter-Investigation), SI (Source Independence), HE (Hierarchy of Evidence)
- Does this task risk reasoning from internal structure? → OI (Outside-In Reasoning)

### Step 3: Identify Key Risks (Processing Phase)

Before doing any work, identify:

1. The **3 most relevant principles** from the standard for this specific task.
   State which they are and why.
2. The **3 most likely anti-patterns** (AP-01 through AP-09) that could affect
   this task. State which they are and what you will do to avoid them.
3. Any **assumptions** you are making. Flag them explicitly per EH (Epistemic Humility).

### Step 4: Present the Plan

Present to the user:
- The question being answered (from Step 2)
- The 3 priority principles and why
- The 3 risk anti-patterns and mitigations
- Your execution plan — what you will do, in what order
- Any clarifying questions before proceeding

### Step 5: Align Before Executing

DO NOT begin work until the user confirms the plan. If the user has questions or
corrections, incorporate them and re-present.

### Step 6: Execute with Phase Discipline

As you work:
- **Input phase:** Apply the relevant input principles identified in Step 3
- **Processing phase:** Apply the relevant processing principles. For each major
  claim, state confidence level (CC) and falsification condition (FR)
- **Output phase:** Lead with conclusions (PP). Use precise language (PL).
  Back quantitative terms with metrics.

### Step 7: Quality Check

Before delivering, run the Quality Checklist from the standard against your output.
Report any items that are not satisfied and either fix them or flag them to the user
with rationale.

---

## When to Use This Skill

- Research tasks where evidence quality matters
- Strategic decisions where narrative fallacy or confirmation bias are risks
- Validation work where adversarial posture is needed
- Any task where the user says "I need to think critically about this"
- When you notice yourself making unsupported claims or skipping counter-evidence

---

## When NOT to Use This Skill

- Simple implementation tasks (write this function, fix this bug)
- Mechanical work (rename files, update imports)
- Tasks where the user has already done the analysis and just wants execution

The standard governs analytical work, not all work.
