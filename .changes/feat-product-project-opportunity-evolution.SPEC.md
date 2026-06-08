---
founder_facing: false
---

# Spec — Product / Project / Opportunity: properly emitted + evolving, with their cross-repo home built

**Change:** CH-01KT61 · feat

## Intent

Make the top-of-hierarchy brain entities — the founder's **Product**, its
**Projects** (the multi-repo anchors), and the **Opportunity** (the "why") —
properly **emitted AND evolving**, with their cross-repo / Platform-store home
**built**, not merely decided. This turns the brain's evolution machinery ON
for living entities for the first time: today the bitemporal fields exist on
~26 entity schemas but no emitter writes history. These are the entities the
founder actually builds and will pay to see and steer (the ADE explores them;
the Platform operationalises them) — so they must be living memory, not
once-only snapshots.

Full scope, by founder decision (2026-06-03): the whole arc in this one
change, not a carved first slice.

## Scope

1. **LifecycleRun v1.0.0 → v2.1.0 migration (the PROV spine).** Change
   `step_name` (string) to a required `step` **ref** to a Step entity
   (BREAKING). Migrate `_brain_emit_helper` and `sulis-emit-lifecyclerun` in
   lockstep. Make the modelling call: what Step does a change-start / change-ship
   LifecycleRun point at. Migrate existing v1.0.0 instances.

2. **PROV vocabulary added to the grammar (greenfield).** Recon confirmed PROV
   is absent entirely — not just `wasRevisionOf`. Add the Activity-generates-
   Entity idiom: `wasGeneratedBy` / `used`. `wasRevisionOf` is deliberately NOT
   added (not in the grammar).

3. **The evolve mechanism.** On a living entity's change:
   read-current-version → close the prior valid-window (set `valid_to`) → open
   a new window (`valid_from` + `confidence` + `sys_status`) → record PROV
   `wasGeneratedBy` the generating Activity (+ `used` inputs). Bitemporal
   as-of-time and PROV which-activity are **complementary**, both written.

4. **Apply evolve to the living top-of-hierarchy entities.** Product,
   Opportunity, and Project (the living multi-repo anchor) write history when
   they change. Decision and LifecycleRun **stay events** (append-only; their
   supersedes chain is their lineage) — the retrofit is NOT applied to them.

5. **Build the Platform-store / multi-repo home (#51 / #30).** Product and
   Opportunity are Tenant-scoped / cross-repo — stand up their real central
   store (the Storage Service / SQLite global store). The current repo-local
   `.brain/instances` per-repo emission + flat-file query swaps for the real
   backend, readable cross-repo for a Tenant.

6. **Reconcile Project's home (#64).** `discover-project` today mints Project
   to `.sulis/projects/<slug>.jsonld` (via `minter.py`), NOT the brain store —
   reconcile this so Project lands in the reconciled brain home, preserving its
   multi-repo anchor role (`belongs_to_product_ref` string ref,
   `depends_on` / `consumed_by` inter-repo edges).

## Non-goals

- **Ontology v0.7 upstream.** `belongs_to_product_ref` stays an unresolved
  plain string ref until v0.7 lands; we do not resolve it here.
- **Retrofitting evolve onto event entities.** Decision and LifecycleRun stay
  append-only events. Don't over-apply the bitemporal retrofit.
- **The founder-facing "see / steer your living product" UI.** That's the ADE /
  Platform tier, downstream of this change.
- **Re-doing CH-01KT60's basic capture-path emit** for Opportunity/Product —
  the basic emit to `.brain/instances` is already in main (CH-01KSWZ #118);
  this change evolves and re-homes it, it does not re-create it.

## Acceptance

- A living **Product** that changes produces: a closed prior valid-window
  (`valid_to` set) + a new open window + a PROV `wasGeneratedBy` edge to the
  generating Activity. History is written and queryable as-of-time. Same proven
  for **Opportunity** and **Project**.
- **LifecycleRun** emits at v2.1.0 with a real `step` ref; pre-existing v1.0.0
  instances are migrated; `_brain_emit_helper` + `sulis-emit-lifecyclerun`
  emit the new shape.
- **Product + Opportunity** persist to the central Platform store and are
  readable cross-repo for a single Tenant (the multi-repo home works).
- **`discover-project`** writes Project to the reconciled brain home, not the
  divergent `.sulis/projects` path; the multi-repo anchor fields survive.
- Full test suite green + new tests covering: the evolve close/open-window
  cycle, PROV emission, the LifecycleRun migration (incl. instance migration),
  and the Platform-store read/write path.

## Constraints

- **LifecycleRun v2.1.0 is BREAKING.** The schema bump, `_brain_emit_helper`,
  `sulis-emit-lifecyclerun`, and existing-instance migration move in lockstep —
  no half-migrated state.
- **PROV idiom is Activity-generates-Entity** (`wasGeneratedBy` / `used`).
  `wasRevisionOf` does NOT exist in the grammar and must not be introduced.
- **Bitemporal + PROV are complementary**, not redundant: as-of-time answers
  "what did we believe when"; PROV answers "which activity generated this".
- **Read the landed design docs first** (on main): `docs/plugin-evolution-
  context-brief.md`, `docs/sulis-distribution-and-deployment-design.md`,
  `docs/trunk-based-release-workflow-remodel.md`, `docs/claude-code-plugin-
  distribution-brief.md`. They are the prior design thinking for exactly this
  work.
- **Platform store touches a storage backend** (SQLite global store, #30) — a
  Platform/Storage contract should be grounded at design time rather than
  assumed (gated third-party/storage touch → surface at `draft-architecture`).
- **Default to established conventions** (CP-01) for the storage layer and the
  PROV vocabulary (W3C PROV-O is the canonical reference for the idiom).
- This is a large change by design — the size is absorbed by decomposition into
  a Work Package set at the design stage, not by reducing scope.

## Notes

- Coordination (recon-verified): no evolve work is in flight elsewhere.
  CH-01KT60's branch sits at main with no unique commits; the
  `living-emitters-write-history` branch is a stale pointer at the already-
  merged design-docs commit. This change has clear air.
- The LifecycleRun migration is the natural first piece of the build order (the
  PROV spine everything else hangs off), even though the change's *scope* is the
  full arc.
