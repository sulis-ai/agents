# Decision Records — Comprehensive Spec & Two-Surface Journey Walk

Technical decisions (ADRs) and business decisions (BDRs) for CH-CQRWWR. Each is
emitted as a `decision` brain entity (this change dogfoods FR-17 — note the
BDRs' `kind: bdr` frontmatter is not yet persisted because the `decision`
schema has no `kind` field; closing that is ADR-006's own subject).

## Technical Decisions (ADRs)

| ID | Title | Phase | Drives |
|----|-------|-------|--------|
| ADR-001 | Depth decouples from doc-existence by removing the doc-shape branch | P1 | FR-03, FR-04 |
| ADR-002 | One comprehensive-document structure, emitted always, modelled on the canonical | P1 | FR-01, FR-05, FR-06, FR-11 |
| ADR-003 | Tool surface is a second walk pass with the generalised binding-EXISTS bar | P2 | FR-08, FR-09 |
| ADR-004 | UC-flow-coverage is a third companion gate, not a rewrite | P2 | FR-12, FR-13 |
| ADR-005 | Tool scenarios reuse the #98 substrate; add only a `surface` tag | P2 | FR-10, FR-14 |
| ADR-006 | ADR vs BDR is a `kind` discriminator on the existing `decision` entity | P3 | FR-17 |
| ADR-007 | The interface contract is a mandatory doc section the tool-walk reads operations from | P3 | FR-18, FR-19 |

## Business Decisions (BDRs)

| ID | Title | Subject |
|----|-------|---------|
| BDR-001 | Ship the three phases in sequence (P1 → P2 → P3) | Sequencing |
| BDR-002 | Three distinct gates, one founder-facing verdict rollup | Founder experience / scope |

## Notes

- No External ADR Registry exists for this change (`.context/` absent for this
  slug); these ADRs start fresh at ADR-001.
- The `sulis-emit-decision` emitter derives a decision's `@id` from the ADR's
  `change_id` frontmatter — which **collides** when a change emits more than one
  decision. These records omit `change_id` (falling back to fresh ULIDs) so all
  nine emit distinctly. The collision is a real emitter limitation surfaced by
  this design; the WP that implements ADR-006 (emitter changes for BDR support)
  should fix the multi-decision ID strategy in the same pass.
