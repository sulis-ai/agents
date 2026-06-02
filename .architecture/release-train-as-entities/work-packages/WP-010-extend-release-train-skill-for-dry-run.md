---
id: WP-010
title: Extend `/sulis:release-train` skill — dry-run-walks-canonical mode
status: pending
kind: docs
primitive: extend
group: EXPAND
sequence_id: WP-010
dependsOn: [WP-001, WP-002]
blocks: []
estimated_token_cost:
  input: 4k
  output: 2k
tdd_section: FR-011; UC-001
adrs: [ADR-001]
---

## Context

Extends `plugins/sulis/skills/release-train/SKILL.md` to add a new
behaviour: when invoked with `--dry-run` (default), invoke
`/sulis-brain:execute-workflow plugins/sulis/instances/release-train/`
to walk the canonical via the brain's LLM-driven runner. The walk
produces a founder-readable preview of each Step + the structural
verdict.

The non-dry-run path is unchanged (continues today's imperative
preview-then-ship flow).

Depends on WP-001 (Workflow exists) + WP-002 (Steps exist) — the
execute-workflow agent needs both to walk.

## Contract

### Skill prose extension (≤ 40 lines added to existing ~440-line skill)

Section added to the existing SKILL.md after step 5 (Surface +
confirm):

```markdown
## Dry-run mode — walk the canonical (default, when canonical present)

When `plugins/sulis/instances/release-train/` exists (canonical
authored), the dry-run preview walks it via the brain's
execute-workflow runner instead of building the preview from
imperative YAML inspection. This gives the founder a Step-by-Step
narrative of what the release would do — derived from the canonical
spec, not from re-reading bash.

To invoke:

\`\`\`bash
SCRIPTS_DIR=$(find ~/.claude/plugins/cache -name execute-workflow -type d \
  -path '*/sulis-brain/*/agents*' 2>/dev/null | sort -r | head -1 | xargs -I{} dirname {})

# Resolve the marketplace plugin Project the founder is releasing
PROJECT_ID=$(read_project_id_from_change_or_prompt)

# Invoke execute-workflow with for_project binding
echo "About to walk release-train canonical for Project: $PROJECT_ID"
echo "(LLM token budget: ~6k input + ~3k output per the SRD's NFR-001)"
# The agent invocation is via Claude Code's slash command:
#   /sulis-brain:execute-workflow plugins/sulis/instances/release-train/
# with for_project context propagated via env (SULIS_FOR_PROJECT=$PROJECT_ID)
\`\`\`

The agent reads workflow.jsonld + steps.jsonld + triggers.jsonld +
failuremodes.jsonld + tools.jsonld + projects.jsonld, walks the Steps
in order, and produces a per-Step preview. The founder reviews the
preview + confirms; non-dry-run then ships via the imperative path
(unchanged).

**Fallback:** if `instances/release-train/` doesn't exist (e.g. older
marketplace fork), the skill falls back to today's imperative-only
preview. No regression.
```

### Token budget

The skill records the dry-run's actual token cost in a session log
(append-only). NFR-001 sets the budget at ≤ Xk; X is measured on
the first run and recorded; subsequent runs exceeding 1.25× the
baseline trigger a warning surfaced to the founder.

## Definition of Done

### Red — Failing tests written
- [ ] `tests/test_release_train_skill_md_has_dry_run_section.py` — reads SKILL.md + asserts the new section is present with the right invocation pattern
- [ ] Manual smoke: invoke `/sulis:release-train` against a marketplace plugin Project; verify the dry-run preview reflects the canonical Step list (not the imperative YAML)

### Green — Implementation makes tests pass
- [ ] `plugins/sulis/skills/release-train/SKILL.md` extended per Contract
- [ ] The dry-run path correctly invokes `/sulis-brain:execute-workflow` with the canonical dir
- [ ] for_project binding propagates (env var or arg) per ADR-001's UC-001
- [ ] Fallback path works when `instances/release-train/` is absent
- [ ] No regression in non-dry-run path (today's ship flow unchanged)

### Blue — Refactor complete
- [ ] Skill prose stays under 30 lines added (target; minor overage acceptable)
- [ ] Section composed under existing structure (not bolted-on)
- [ ] References ADR-001 + the SRD's NFR-001 token budget

## Sequence

- **dependsOn:** WP-001 (Workflow), WP-002 (Steps) — both must exist for execute-workflow to walk
- **blocks:** —
- **Parallelisable with:** WP-007, WP-008, WP-009, WP-011

## Estimated Token Cost

- **Input:** ~4k (current SKILL.md ~440 lines + Workflow + Steps for context)
- **Output:** ~2k (~30 lines of new prose; possibly one Bash snippet)
- **Total:** ~6k

## Notes

- Founder-mode framing: the dry-run preview names each Step in plain
  English, says what it will do, what FailureModes guard it, and
  what the human gate (Step 8) requires. The Step.agent_instructions
  field carries that prose; execute-workflow renders it.
- Brain's execute-workflow already handles human-mechanism Steps
  (Step 8) — pauses for input, doesn't auto-skip.
- This WP is `kind: docs` because it's a skill prose addition; the
  actual LLM runtime work is the brain's execute-workflow agent (not
  this WP's scope).
