# Sulis

The canonical front-door plugin for the Sulis AI marketplace.

This is the plugin a non-technical founder installs and uses. Everything else
in the marketplace (`srd`, `sea`, `sulis-execution`, `sulis-security`,
`sulis-context`, etc.) is an operator-facing specialist plugin that the
concierge inside sulis spawns at the right time.

## What's in here

| Surface | Purpose |
|---|---|
| `concierge` agent | The single entry point for founders. Owns the journey from idea → requirements → design → implementation → verification → security in plain English. Spawns specialist agents and translates their outputs back into Founder English. |
| `start` skill | Re-enter an existing concierge journey from `.sulis/{project}/JOURNEY.md`. |
| `handoff` skill | Capture state in JOURNEY.md when handing the founder over to a specialist. |
| `status` skill | Read-only plain-English summary of the current journey state. |
| `add-skill` skill | Five-gate methodology for authoring new skills in the marketplace. Used by skill authors (not founders). Grounded in the kinds-and-tools spec's learnings on consistent agent outcomes. |

More founder-facing skills will land here as the canonical experience builds out (next on the roadmap: `inbox`, `next`, status-line config, starter packs).

## How to start a session

```
claude --agent sulis
```

The concierge greets the founder, picks up `.sulis/{project}/JOURNEY.md`
(or starts a new journey), and routes the conversation through whatever phase
they're in.

## Architecture

The marketplace is layered:

```
                        Founder
                           │
                           ▼
              ┌────────────────────────┐
              │      sulis             │  ← canonical front door
              │  (concierge + skills)  │
              └────────────────────────┘
                           │
        ┌──────────┬───────┼───────┬──────────┐
        ▼          ▼       ▼       ▼          ▼
       srd       sea    exec   security   context
   (operator) (operator)(operator)(operator)(operator)
```

Founders never invoke `/srd:*` or `/sea:*` directly. The concierge does it on
their behalf and translates the output back. The operator-facing plugins keep
their existing surface for technical users who want to drive the engine
directly.

## Why "sulis" (unprefixed)

All other plugins carry the `sulis-` prefix. The unprefixed name marks this as
the foundational front-door — the one a founder installs first; the one the
others sit underneath.

## Customising the release-train for your own marketplace fork

The release-train Workflow is the per-Project release pipeline used by
this marketplace. Its canonical specification lives at
`plugins/sulis/instances/release-train/` — Workflow + Steps + Triggers +
FailureModes + Projects + Tools as JSON-LD entity instances.

If you fork this marketplace and want to use the release-train against
your own plugins, you need to author a Project entity instance for each
of your plugins. The Project entity declares your repo's source path,
version files, branch policy, and the other variables the release-train
consumes.

**The authoritative reference for what a Project entity must contain is
the SRD's "Configuration Vocabulary" section:** see
[`.specifications/release-train-as-entities/SRD.md#configuration-vocabulary`](../../.specifications/release-train-as-entities/SRD.md#configuration-vocabulary).

The marketplace's own Project instances at
`plugins/sulis/instances/release-train/projects.jsonld` serve as worked
examples — `sulis`, `sulis-brain`, `plugin-builder`, and `investor-coach`
each demonstrate a typical fill pattern.

**Future:** a `project-discovery` Workflow will automate this
interactively. Until then, hand-author your Project instance using the
Configuration Vocabulary as your template.

## History

- **v0.2.0** (2026-05-23) — Canonical-plugin scope. Absorbed the concierge agent + journey skills from sulis-concierge (which is now a deprecation shim). Plugin description expanded from "meta-skills only" to "canonical front door".
- **v0.1.0** (2026-05-23) — Initial release. Meta-skill home with `add-skill`.

See `CHANGELOG.md` for full history.
