# Sulis — the product ladder (north star)

> **Status:** north-star / founder-authored vision (2026-06-03). Captured with
> the founder during change CH-01KT50. This is the fixed picture the
> change-centric product is built against; specific designs and slices cite it.

## The ambition (one sentence)

Give **non-technical founders** a **Product Development Platform** that takes
them from an idea to a released, operating product — where an autonomous agent
drives the whole lifecycle and the founder steers in plain English.

This is **not an IDE.** An IDE is about *editing code*. Sulis is about
*managing the whole product lifecycle* — specify → design → build → test →
verify → deploy → release → operate — driven by the founder, executed by the
agent.

## The ladder (three tiers, one audience, one on-ramp upward)

A founder climbs a single ladder. Nothing is re-entered on the way up.

| Tier | What it is | Where it runs | The value it adds |
|---|---|---|---|
| **Open-source plugin** | The terminal on-ramp. Reduced functionality, free. | The terminal (Claude Code plugin) | **The engine** — creates changes and runs the lifecycle. How a founder first meets Sulis. |
| **Sulis** ("Cursor for Product Development") | The cockpit, graduated into a real app you work *in*. | A local app | **Legibility + steering** — see and drive the same changes as plain-English threads. |
| **Sulis Platform** | Operationalising: running and watching the live product. | Hosted / cloud | **Operations** — deploy targets, monitoring, observability, the live runtime. |

## The core primitive — the *change*

The unit that drives everything is the **change**: a lifecycle thread that
*is* the product's state moving forward. Underneath each change sits the
**brain** — the entities, workflows, requirements, designs, and artifacts the
agent creates as the change progresses.

This is the deliberate contrast with Cursor: Cursor's unit is a *file*; Sulis's
unit is a *change*. The "Cursor for Product Development" line sells the
category leap (familiar app, AI-native, you work *in* it) — but the discipline
is to stay change-centric and never drift into rebuilding a code editor.

## The moat — continuity across tiers

The reason the ladder is frictionless: **all three tiers read and write the
same changes and the same brain.**

- The terminal plugin *creates* a change.
- The Sulis app *shows and steers* that exact change.
- The Platform *operationalises* that exact change.

No export, no migration, no rewrite when a founder graduates. The artifact
lineage travels with them up the ladder. **Protecting this single shared data
model (changes + brain) across all three tiers is the most important
architectural rule of the whole platform.** It is already true today (the
change store and brain are shared); it must stay true.

## The value boundary — what's free, paid, platform

| Boundary | Tier | Rationale |
|---|---|---|
| The **engine** that runs the lifecycle in the terminal | Open-source (free) | The on-ramp. Lowers the cost of meeting Sulis to zero. |
| **Seeing and steering** — plain-English threads, rendered previews, the brain explorer, search | Sulis app (paid) | A non-technical founder can barely use the terminal-only version. **Legibility is exactly what they pay to graduate for** — healthy upgrade pressure, not a paywall. |
| **Operating** the live product — deploy, monitor, observe | Platform | The runtime a shipped product needs. |

**Caution (founder-stated):** don't let the open-source tier get so capable
there's no reason to climb, nor so thin no one starts. "Engine free, legibility
paid, operations platform" is the cut that holds.

## The Sulis app — the signature experience

The Sulis app makes a change a **navigable thread** a non-technical founder can
actually read and drive. Everything below is the north-star scope for the app
tier (built incrementally, one slice per change):

- **The board (landing)** — in-flight changes as a **Kanban** across the stages
  (recon → specify → design → implement → review → ship); cards move left to
  right as work progresses. The instant-read overview; the way in to any thread.
- **Lineage / audit history** — what happened, in order; a live chat with the
  agent driving the change.
- **Stage-by-stage progress** — specify done, design done, building… — and
  where the change sits in **release** (which environment it has reached).
- **What changed, in plain English** — added / removed / changed, **tied back
  to the requirements and designs they serve**, with a plain-language summary —
  not raw diffs. Raw files available for those who want them.
- **Rendered previews** — read the rendered `.md` / `.html` (and similar), not
  the source. Source is there on request.
- **The brain, explorable** — the entities and workflows created for the
  change, grouped, with detail, and **interrogable** ("what does this
  requirement mean?").
- **The worktree, browsable** — all the files in the change, without the
  founder ever touching a confusing sibling folder on disk (worktrees already
  live tucked away under `~/.sulis/changes/`; lean into that — keep them
  invisible).
- **Search and filter** — find a change by content; filter by stage, by
  status, by what needs attention.

## The checkpoint — status report as lineage

The change thread's "what's happening" content is not a one-off render. The
agent **publishes a plain-English status report every few turns** (≈ every 3–5).
It earns its keep twice:

- **Confidence for the founder** — a steady, readable account of where the
  change is, in plain English, without reading the raw transcript.
- **Discipline for the agent** — the checkpoint forces the agent to stop and
  state the change's state plainly; a self-correcting beat in the loop.

These checkpoints accumulate into the **lineage** the founder scrolls back
through. The thread = the chat + the files + the entities + this spine of
checkpoints.

## Delivery shape — local first, one data seam

The founder's intended progression of how Sulis runs:

1. **Local** — the app runs on the founder's machine, agent on the same machine
   (where we are now / next).
2. **Cloud UI, local agent** — the app is served from the cloud, the agent
   still executes on the founder's machine.
3. **Fully cloud** — app and agent both hosted.

**Architectural rule (decided CH-01KT50):** *design the seam, not the cloud.*
The app reaches its data — changes + brain — **only through one narrow API
boundary**, never the filesystem directly. Today that boundary is served by a
local process; later the same boundary is served from the cloud. The three
modes above are then just *where the seam is served from* — not a rewrite. This
seam **is** the continuity moat (one data model up the ladder), expressed as an
API.

We do **not** build cloud infrastructure prematurely. We start as a **local web
app → installable binary → web**, and the only discipline that makes each step
cheap is refusing to let the app cheat past the data seam. The existing local
app already serves changes through a small server — the seam exists in embryo;
we extend it, we don't invent it.

## Principles

1. **Agent-driven, always.** The founder never hand-edits a file or a setting.
   They open a **change**; the change governs the process. This includes
   project / product **defaults and an admin area** — those are changed through
   changes too, not through a settings form.
2. **Plain English is the default surface.** Technical detail is available on
   request (the dual-register pattern), never the front door.
3. **The change is the unit of everything** — work, audit, state, release.
4. **One data model up the ladder** — see "the moat" above.

## In progress now (CH-01KT50)

- **Two-way chat** — interacting with the agent from the app (send a prompt to
  a change's session, stream the reply). Turns the app from read-only review
  into *driving* the agent. The live bridge was validated by an earlier spike.
- **A thorough end-to-end UX + visual design** of the app tier — the experience
  is currently "lumpy". This change runs a dedicated UX + visual design pass at
  its design stage, over the whole surface (board, thread, chat, brain view,
  rendered previews, search) as one coherent thing.
- **Contracts surfaced through the process** — the data contract (the API the
  app speaks) and the UI/visual contract are rendered and surfaced for founder
  review at design time, before build — a review gate, not buried YAML.

## Explicitly later

- **Monitoring and observability of the live product** — this is the Platform
  tier's heart; named here so it has a home, not built yet.
- **The agent publishing checkpoints every few turns as a live mechanism** —
  the read-time status is in scope now; the periodic auto-publish beat comes
  later.
- **Deep brain Q&A, the admin/defaults area, and the cloud modes** — north-star
  scope; the cloud modes are *designed for* (the data seam) but not built.

## Naming (resolved)

The product is **Sulis**. "Cockpit" was our internal codename for the app tier
and is retired in favour of **the Sulis app**. The three tiers are the
open-source plugin, Sulis, and Sulis Platform.

## See also

- `plugins/sulis/docs/local-ui-design.md` — the app-tier UI design notes.
- `plugins/sulis/docs/scenario-authoring-source-design.md` — the testable-state
  verification loop this change dogfoods.
- `.changes/create-cockpit-mvp.SPEC.md` — earlier read-only app-tier MVP
  thinking (dashboard, thread view, file browser, diff).
- `.changes/cockpit-contract-preview.SPEC.md` — "see the contracts before you
  go" preview (founder-legible-first decisions).
