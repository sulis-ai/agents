# Handover: Auto Codebase Mapping

## Key Decisions

| Decision | Chosen | Alternative Considered | Rationale |
|----------|--------|----------------------|-----------|
| Staleness detection method | Filesystem mtime | Git log --since | User needs uncommitted WIP detected, not just committed changes |
| Overlay timing | Next reflection checkpoint | Immediately on completion | Interrupting facilitation adds extraneous cognitive load |
| Greenfield handling | Silent skip | Inform user no codebase found | Announcing absence adds no value and creates noise |
| Depth model | Two-level (broad map + on-demand deep dive) | Single comprehensive scan | Full deep scan is slow; broad map is fast and sufficient until conversation narrows |
| Overlay language | Domain capabilities | Infrastructure/technology | "A service that handles payments" is useful during facilitation; "Express with PostgreSQL" is not |

## Assumptions

| Assumption | Validation Method | Impact if False |
|------------|-------------------|-----------------|
| Agent reliably follows MUST-level Phase 1 instructions | Test across multiple sessions | Mapping may not trigger; would need SessionStart hook |
| Filesystem mtime is reliable across OS/filesystem types | Test on macOS, Linux with common filesystems | Staleness check may produce false negatives, causing stale index reuse |
| Agent tool's run_in_background works within agent sessions | Test with the requirements-analyst agent active | Mapping would block facilitation |

## Known Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Agent skips mapping instruction on first turn | Low | Medium — facilitation proceeds without grounded context | MUST-level instruction; consider SessionStart hook in future |
| Large codebase mapping takes longer than reflection checkpoint window | Low | Low — overlay happens at next available checkpoint | Mapping runs in background; agent checks for completion at each checkpoint |

## Implementation Targets

Two files need changes (already implemented):

1. **`srd/agents/requirements-analyst.md`**
   - New MUST rule: "No Implementation Without Artifacts"
   - Phase 1: Auto-trigger replaces opt-in offer
   - Section 4: Two-level depth model, overlay timing, domain language focus

2. **`srd/skills/codebase-mapping/SKILL.md`**
   - Execution model: Auto-trigger, staleness check, greenfield detection
   - New sections: Staleness Check procedure, Greenfield Detection criteria

## Artifact Reading Order

1. [GLOSSARY.md](GLOSSARY.md) — Understand terms
2. [SRD.md](SRD.md) — Full specification
3. [diagrams/process-flows.md](diagrams/process-flows.md) — Decision and overlay flows
4. [diagrams/state-diagrams.md](diagrams/state-diagrams.md) — Mapping task lifecycle
5. [NFR.md](NFR.md) — Performance and reliability constraints
