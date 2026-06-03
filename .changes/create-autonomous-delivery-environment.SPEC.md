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

## Scope (six things)

1. **Stage Kanban board** — in-flight changes as cards in lifecycle-stage columns.
2. **Per-change plain-English stage progress + status** read-out.
3. **Brain / entities view** in a change (read-only, grouped).
4. **Rendered previews** of `.md`/`.html` (with a raw-source toggle).
5. **Search + filter** of changes (by content; by stage; by "needs attention").
6. **Two-way chat** — send a message to a change and stream the reply; if no
   session is live it resumes the change's last one, or starts a fresh one
   grounded in the change's saved context ("it just works").

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

## Full requirements

`.specifications/autonomous-delivery-environment/` — SRD.md (29 requirements),
NFR.md, GLOSSARY.md, diagrams/ (board navigation; chat send/stream flow).
Verification Plan: PASS.
