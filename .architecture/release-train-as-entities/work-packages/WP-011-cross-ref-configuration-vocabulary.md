---
id: WP-011
title: Cross-reference Configuration Vocabulary from marketplace plugin README
status: pending
kind: docs
primitive: extend
group: EXPAND
sequence_id: WP-011
dependsOn: []
blocks: []
estimated_token_cost:
  input: 2k
  output: 1k
tdd_section: FR-016; UC-004 (fork-and-adapt)
adrs: [ADR-004]
---

## Context

Adds a cross-reference in `plugins/sulis/README.md` pointing
fork-consumers at the SRD's Configuration Vocabulary section as the
authoritative manual reference for populating their own Project entity.

Per MUC-010 + the SRD's "Future: discovery sibling" section, the
manual Configuration Vocabulary is the v1 onboarding fallback until
`project-discovery` Workflow ships.

No dependencies on other WPs in this set — pure docs addition.

## Contract

### plugins/sulis/README.md addition

A new section (or addition to existing "For downstream consumers" if
present) at the bottom:

```markdown
## Customising the release-train for your own marketplace fork

The release-train Workflow is the per-Project release pipeline used by
this marketplace. Its canonical specification lives at
`plugins/sulis/instances/release-train/` — Workflow + Steps + Triggers
+ FailureModes + Projects + Tools as JSON-LD entity instances.

If you fork this marketplace and want to use the release-train against
your own plugins, you need to author a Project entity instance for
each of your plugins. The Project entity declares your repo's source
path, version files, branch policy, etc.

**The authoritative reference for what a Project entity must contain
is the SRD's "Configuration Vocabulary" section:** see
[`.specifications/release-train-as-entities/SRD.md#configuration-vocabulary`](../../.specifications/release-train-as-entities/SRD.md#configuration-vocabulary).

The marketplace's own Project instances at
`plugins/sulis/instances/release-train/projects.jsonld` serve as
worked examples — `sulis`, `sulis-brain`, `plugin-builder`, and
`investor-coach` each demonstrate a typical fill pattern.

**Future:** a `project-discovery` Workflow will automate this
interactively. Until then, hand-author your Project instance using the
Configuration Vocabulary as your template.
```

## Definition of Done

### Red — Failing tests written
- [ ] (No new tests; docs prose. Verified by review.)

### Green — Implementation makes tests pass
- [ ] `plugins/sulis/README.md` has the new section
- [ ] Cross-reference link to SRD's Configuration Vocabulary section resolves correctly
- [ ] Worked examples (`sulis`, `sulis-brain`, etc.) named
- [ ] Future discovery sibling referenced (sets expectation; reduces fork-consumer anxiety)

### Blue — Refactor complete
- [ ] Section integrates with existing README structure (not bolted-on)
- [ ] Tone matches founder-facing prose (plain English, no jargon)
- [ ] Link uses relative path that resolves both on GitHub + locally

## Sequence

- **dependsOn:** —
- **blocks:** —
- **Parallelisable with:** all other WPs

## Estimated Token Cost

- **Input:** ~2k (current README + SRD's Configuration Vocabulary)
- **Output:** ~1k (~25 lines of new prose)
- **Total:** ~3k

## Notes

- Can be authored at any time; ideally lands after WP-005 (Projects)
  so the worked examples are real.
- If `plugins/sulis/README.md` doesn't have a "For downstream
  consumers" section yet, this WP creates a "Customising the
  release-train for your own marketplace fork" section directly.
