# Sulis AI Standards

This repo is **Sulis AI's Claude Code plugin marketplace**. It serves two purposes:

1. **Custom marketplace** — point Claude Code at this repo via `extraKnownMarketplaces` to discover and install plugins.
2. **Plugin source** — contains the `srd` plugin (and any future plugins) with skills, agents, hooks, and reference standards.

## Repo Structure

```
standards/
├── CLAUDE.md                              # This file — project instructions
├── CONTRIBUTING.md                        # Contribution & release guide
├── README.md                              # Marketplace + SRD plugin overview
├── LICENSE
├── .claude-plugin/
│   └── marketplace.json                   # Marketplace registry manifest (Claude Code reads from here)
├── docs/
│   ├── skill-authoring-guide.md           # Best practices for writing skills
│   └── rollout-plan.md                    # Staged principle introduction
├── plugins/
│   └── srd/
│       ├── .claude-plugin/
│       │   ├── plugin.json
│       │   └── hooks/                     # Experimental background hooks
│       ├── README.md                      # Plugin documentation
│       ├── settings.json
│       ├── agents/                        # Agent definitions
│       ├── skills/                        # Slash-command skills
│       ├── references/                    # Shared reference standards
│       └── docs/
│           └── specifications/            # Self-referential development specs
```

## Required Reading

Before creating or modifying any skill, read `docs/skill-authoring-guide.md` and `CONTRIBUTING.md` in full.

## Adding a New Skill

1. Create a directory under `plugins/srd/skills/` named after the skill.
2. Add a `SKILL.md` file inside that directory. This is the skill's prompt entrypoint.
3. Include `references/`, `scripts/`, or `examples/` subdirectories as needed.
4. Test locally by running the skill from a project that has the plugin installed.
5. Open a PR and get it reviewed.

## Testing Locally

To test a plugin skill without publishing:

1. In the project where you want to test, add this repo's path to your local Claude Code settings:
   ```json
   {
     "extraKnownMarketplaces": ["/path/to/standards"]
   }
   ```
2. Or run directly:
   ```bash
   claude --plugin-dir ./plugins/srd
   ```
3. Run the skill via its slash command (e.g. `/srd:critical-thinking`).

---

## Non-Negotiables

Six rules. If a plan would violate any of these, the plan is wrong.

1. **New code: no implementation without a failing test first.** Write the test, see it
   fail, then write code. The REFACTOR step is not optional — it is where shared
   primitives get extracted. (EP-02)

2. **Check before building new.** Before creating any component, verify that no existing
   component can be extended or adapted. Search the codebase first. When you find two or
   more components implementing the same pattern — stop and extract the shared primitive
   before continuing. Do this in the same PR, not "later." (EP-03)

3. **Existing code: leave every file better than you found it — but prove behaviour
   first.** When you touch a file, review what's already there. For structural changes
   (extracting functions, splitting classes, changing interfaces), follow Fowler's
   refactoring discipline: write a characterisation test, confirm it passes, refactor,
   confirm it still passes. Mechanical changes (renames, dead code removal, import
   cleanup) do not require a characterisation test. (EP-07)

4. **Scope your improvements.** Boy Scout improvements apply to the file you are working
   in. If an improvement requires changes across multiple files, capture it and plan it
   as a separate piece of work — not an unbounded side-quest from your current PR. (EP-07)

5. **Default to the established convention.** When you recommend a protocol, format,
   library, pattern, schema, or implementation approach, default to the most established
   convention that meets the requirement. IETF / W3C / ISO / OCI standard exists →
   recommend it. Dominant industry convention (Stripe, GitHub, Kubernetes, OpenTelemetry,
   AWS, the SRE book) exists → recommend it. Two conventions both qualify → recommend the
   older, more boring, more widely-adopted one. The bespoke approach is the position
   requiring defence, not the convention. Never go neutral; never recommend novelty by
   silence. (CP-01..CP-05)

6. **The default audience is non-technical.** The marketplace's primary user is a
   non-technical founder. They don't know what RFC 9421, cursor pagination, "Option α
   vs β", `tuple[Decimal, Decimal]`, or UC modelling mean. Before posing any question,
   run the three-step pre-question triage: (a) does this choice have a user-facing or
   business-facing consequence? if no — take the convention silently; (b) can the
   consequence be stated in user-experience or business terms with zero technical
   vocabulary? if no — take the convention silently; (c) is the right answer obvious
   from the user's stated principles, vision, or persona? if yes — apply and announce.
   Only questions surviving all three reach the user, and they reach in concrete
   scenarios using plain-English equivalents from the translation lexicon. Never expose
   internal IDs, technical jargon, or `α/β/γ` to a non-technical user in question text.
   (AAF-01..AAF-05)

For full detail on these principles, see `plugins/srd/references/engineering-principles.md`,
`plugins/srd/references/security-standard.md`,
`plugins/srd/references/convention-preference-standard.md`, and
`plugins/srd/references/audience-adapted-framing-standard.md`.

### Quality Gates

Before every commit, verify:
- All tests pass
- No linting errors
- No type errors
- No known issues deferred
- A plan with no test strategy is incomplete regardless of how detailed the implementation is

### Conscious Deferral

If deferral is genuinely necessary (production incident, insufficient context to refactor
safely, time-critical delivery), add a comment in the code at the point of deferral.
Adapt the syntax to your project's language:

```
// TODO(deferred): Extract shared validation logic from OrderService and PaymentService
// REASON: Insufficient test coverage on PaymentService to refactor safely
// RESOLVE_BY: 2026-03-25
// PR: https://github.com/org/repo/pull/142
```

Undocumented deferral is not acceptable. A documented deferral is a decision; an
undocumented one is negligence.

---

## Severity Convention

Used consistently across all standards files:

| Severity | Meaning |
|----------|---------|
| **MUST** | Non-negotiable. Violations block delivery. |
| **SHOULD** | Default behaviour. Deviation requires explicit justification documented in the plan. |
| **MAY** | Permitted option. Use judgement. |

---

## Standards Authorship & Evolution

Standards are living documents. When a principle proves wrong, incomplete, or impractical
in practice, raise it — don't work around it silently.

New principles start at SHOULD with a 90-day calibration note. Promotion to MUST requires
evidence from 3+ executions. Demotion or removal requires documented rationale.

All changes to standards files are tracked in the version history section of the relevant file.
