---
founder_facing: true
status: SPEC — deep; requirements + verification journeys authored and emitted
---
# Spec — the Sulis app: first lifecycle-cockpit slice

**Change:** CH-01KT50 · create

## Intent

Bring the **Sulis app** (the paid "Cursor for Product Development" tier — see
`plugins/sulis/docs/sulis-product-ladder.md`) up to the spine of its vision: a
non-technical founder reads and drives a *change* as a navigable lifecycle
thread, without ever touching a worktree. This change also serves as the first
real end-to-end road-test of the testable-state verification loop (author a
plain-English journey → emit it into the brain → resolve at design → run it
straight from the graph).

Built by **extending the existing app at `apps/cockpit/`** (EP-03), reaching all
data through one API seam ("design the seam, not the cloud").

## Scope (eight things)

1. **Stage Kanban board** — in-flight changes as cards in lifecycle-stage columns.
2. **Per-change plain-English stage progress + status** read-out.
3. **Brain / entities view** in a change (read-only, grouped).
4. **Rendered previews** of `.md`/`.html` (with a raw-source toggle).
5. **Search + filter** of changes (by content; by stage; by "needs attention").
6. **Two-way chat** — send a message to a change and stream the reply; if no
   session is live it resumes the change's last one, or starts a fresh one
   grounded in the change's saved context ("it just works").
7. **Chat concierge — discovery, setup + navigation** — a conversational front
   door modelled on the **`sulis:sulis` concierge**, backed by a **headless
   agent** (the same stream bridge as #6). **It coordinates only — it never does
   the work itself.** It can:
   - **navigate** — find changes, report status, answer questions about the
     founder's world, read-only over the brain + change store (concierge help,
     like sulis:sulis).
   - **bootstrap the entity graph from a conversation** — when no Product/Project
     exists yet, the agent does the setup *for* the founder: it asks which
     product they're working on, then asks where the repo(s) are and **branches**
     — **no repo? it creates one** (a consequential, possibly-external act —
     behind the confirm gate); **repos exist? it hunts/configures them** from the
     founder's pointer. It searches the chosen folder, asks clarifying questions,
     and **mints the Tenant / Product / Project** (orchestrating
     `discover-project` / `discover-context` + the spine emitters). The completed
     **Product + Project config persists**, so next time the founder just says
     "make a change on Product X" — setup happens once. A form can't pick from an
     empty graph; a discovery conversation creates it.
   - **start a change from plain-English intent** — resolve intent → primitive +
     slug and run `sulis-change start` against the Project's repo
     (`Project.source = {repo, path, primary_branch}`); the change lands at Recon
     on the board. Local-first: clone from `Project.source.repo` if absent.
   - **contain ALL real activity in a change — including investigation.** The
     concierge does no work inline; even an *investigation* (exploring, looking
     into something) **triggers a change** to hold it, so it's self-contained,
     audited, and can evolve straight into a build without losing context. The
     concierge's only direct consequential acts are (on the founder's confirm)
     minting setup entities, **creating a repo**, and **creating a change** —
     everything else happens inside one.

8. **Multi-product navigation — the board is per-Product.** A Tenant has one or
   many Products; the board shows **one Product's** in-flight changes at a time
   (changes roll up via Project → Product), never a soup of everything. A
   **Product switcher** lets the founder switch Products; switching re-scopes the
   board. This **supersedes the single-implicit-product board** in #1 — the board
   mockup gains the switcher + per-product scoping in the design pass.

## Non-goals

Live-product monitoring/observability (Platform tier); the agent
*auto-publishing* checkpoints every few turns (read-time status is in; the
periodic beat is later); deep brain Q&A; the admin/defaults area; the cloud
deployment modes (the data seam is designed-for, not built).

## How we'll know it's done

Six plain-English **verification journeys** are authored and emitted into the
brain (durable bundle:
`.changes/create-autonomous-delivery-environment.scenarios.jsonld`): see work at
a glance · understand where a change is · talk to the agent · find a change ·
read a doc rendered · see what's been created. When the work is built, these
exact journeys are run straight from the brain graph
(`sulis-verify-acceptance --scenario <id>`) — no hand-built test bundle.

## Constraints / design-stage notes

- A dedicated **UX + visual design pass** over the whole surface as one coherent
  thing (design stage) — the experience is currently lumpy.
- The **data contract (API) + UI/visual contract** are rendered and surfaced for
  founder review at design time — a review gate, not buried YAML.
- **Two-way chat is the only sanctioned write/act path**; every other surface
  stays strictly read-only. Resume/spawn must act only on the targeted change's
  session.
- **The chat-driven discovery agent (scope #7) reads directories and writes
  entities** (mints Tenant/Product/Project; starts changes). It sits in the
  agent-driven / founder-confirms model — the "ask before consequential" gate
  covers the entity writes and the change creation.
- **The onboarding/discovery chat surface earns its own rigorous UX + Mobbin
  pass** (founder-directed) — it is NOT covered by the cockpit visual contract
  already signed; treat it as an additional surface designed alongside.

## Full requirements

`.specifications/autonomous-delivery-environment/` — SRD.md (29 requirements),
NFR.md, GLOSSARY.md, diagrams/ (board navigation; chat send/stream flow).
Verification Plan: PASS.
