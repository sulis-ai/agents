# Changelog — sulis-business-strategy

This file holds the cumulative version history that previously lived in
`plugin.json`'s `description` field. The description is now a one-sentence
summary (per HD-004); historical detail lives here.

For the marketplace-facing summary, see `plugin.json`.

---

## Cumulative history (through v0.1.0)

> Migrated from `plugin.json` description, 2026-05-23.

Business Strategy studio (Kind-schema variant). Drives business-context intake, identity, brand positioning, voice, principles, and strategic foundation work through Kind-schema workflows. v0.1.0 ships two Kinds wired end-to-end: BusinessContext (entry point — 9 domains × 34 questions of conversational intake with V/A/U scoring and SHA-256 provenance, producing BUSINESS_CONTEXT.md; replaces the legacy business-context-intake outcome's Domain Expert / Assumption Challenger / Completeness Monitor triad) and Identity (first consumer — articulates organisational identity via Golden Circle WHY→HOW→WHAT, producing IDENTITY.md; replaces the legacy identity-articulation outcome's Belief Crystallizer / Authenticity Validator / Expression Architect triad). Identity declares BUSINESS_CONTEXT.md as a prerequisite via spec.find.prerequisite_inputs — invoking :identity without BUSINESS_CONTEXT.md present halts cleanly with a prerequisite message rather than degrading silently. The two-Kind sequence tests both the schema's stage primitives AND the cross-Kind dependency pattern that all future Kinds will use. Each Kind: replaces its legacy triad with a single evaluate stage + rubric + structured Verdict + reason-class routing (content_deficient → regenerate, context_deficient → re-find, technical_transient → retry, technical_fatal → stop). Until the platform engine wires Slices 2-4, the business-strategist agent drives all four stages (find → generate → evaluate → decide) manually; when the engine catches up, the agent simplifies to invoking each Kind via KindHandler with no Kind YAML change. Sibling Kinds (Brand, ToneOfVoice, Principles, Vision, Strategy, Commercial, GTM) follow once these two validate the pattern. Coexists with the established sulis-strategy plugin.
