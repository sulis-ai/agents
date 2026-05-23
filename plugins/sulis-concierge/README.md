# sulis-concierge — DEPRECATED

> **Moved to `sulis` plugin at v0.2.0 (2026-05-23).**

The concierge agent and the start/handoff/status skills that used to live here
have been absorbed into the canonical `sulis` plugin. This directory is
retained as a deprecation shim so that anyone with `sulis-concierge`
installed gets a clear migration message rather than a hard error.

## What to do

| Was | Now |
|---|---|
| `claude --agent sulis-concierge` | `claude --agent sulis` |
| `/sulis-concierge:start` | `/sulis:start` |
| `/sulis-concierge:handoff` | `/sulis:handoff` |
| `/sulis-concierge:status` | `/sulis:status` |
| `plugins/sulis-concierge/agents/concierge.md` | `plugins/sulis/agents/concierge.md` |
| `plugins/sulis-concierge/references/journey-model.md` | `plugins/sulis/references/journey-model.md` |
| `plugins/sulis-concierge/references/subagent-dispatch.md` | `plugins/sulis/references/subagent-dispatch.md` |

Same persona. Same JOURNEY.md location (`.concierge/{project}/JOURNEY.md`).
Same behaviour. Just a different plugin home.

## Why it moved

Sib's original feedback: the marketplace's core plugins should collapse into
one front door — the founder shouldn't have to know there are many plugins.
Rather than literally merge every plugin, the cleaner fix is to make `sulis`
the canonical front-door plugin and keep the others (`srd`, `sea`,
`sulis-execution`, etc.) as operator-facing internals.

The concierge + journey skills were already the founder-facing surface;
moving them into `sulis` makes the brand-name match the surface. See
`plugins/sulis/CHANGELOG.md` v0.2.0 for the full rationale.

## When can this directory be removed?

Whenever convenient. The shim exists so the migration is detectable; once
all known installs have moved over, the entire `plugins/sulis-concierge/`
directory can be deleted in a future commit. There is no functional
dependency on it; the plugin.json description here just tells the marketplace
loader that the plugin is deprecated.
