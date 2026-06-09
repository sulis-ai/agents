# Misuse Cases & Negative Requirements: Comprehensive Spec & Two-Surface Journey Walk

**Change:** CH-CQRWWR · primitive `harden` · slug `comprehensive-spec-and-journey-walk`

## Summary

This is a hardening change, so its "attackers" are not malicious users — they are
the **bypasses** by which a change advances while skipping the discipline. Each
misuse case below is a way the old (backwards) behaviour or a careless agent
could let an incomplete change through, and the **system response** that closes
it. The bypasses named in the brief — skip use cases, one-surface walk,
happy-path-only scenarios — map to MUC-01, MUC-05, and MUC-03/04. The
contract-as-afterthought bypass (a tool surface designed with no reviewable
interface contract) is MUC-07.

The "abusive actor" is usually the **agent under shortcut pressure** (token
budget, time, or the path of least resistance) or the **founder who doesn't know
to ask** for completeness. The methodology must make completeness the default, so
neither can bypass it by inaction.

---

### MUC-01: Skip use cases (and other sections) because the change is "small"

**Abusive actor:** Agent under token/time pressure on a lite/standard change.
**Targets:** UC-01, UC-02; FR-01, FR-02, FR-11.
**Misuse flow:**
1. A change is classified lite.
2. The agent (old behaviour) emits a three-line `SPEC.md` and skips use cases, NFR, threat model, diagrams.
3. The change advances with no flows, no measurable NFRs, no threat model.

**System response (REQUIRED):** The system MUST produce every mandatory section
regardless of depth (NR-01). Depth sizes the interview only; doc-existence is
never gated on depth (FR-02, FR-03). A document missing a mandatory section MUST
NOT pass the structure check / P-VER (the design stage does not complete).

**Related NFRs:** NFR-02 (bounded cost makes always-on affordable), NFR-R01
(degrade detail, never section existence).

---

### MUC-02: False EXISTS — claim a hop is wired when it is not

**Abusive actor:** Agent walking the journey who cites a serving endpoint as proof without the binding.
**Targets:** UC-03, UC-04; FR-07, FR-08, FR-09.
**Misuse flow:**
1. A tool operation serves an interface (the handler responds).
2. The agent classifies the hop EXISTS on the strength of the serving endpoint.
3. In reality the operation has no ServiceSpec binding — it is the "looks-built-but-isn't-wired" case (the MCP-Apps lesson).

**System response (REQUIRED):** For a tool hop, EXISTS MUST require BOTH the
tool/handler AND its ServiceSpec binding cited (NR-02, FR-09). A serving
interface without a binding is a GAP, not EXISTS, and blocks the gate. For a
host-rendered hop, EXISTS requires the binding on both sides + a real-host
round-trip (sharper bar, retained from #85).

**Related NFRs:** NFR-S02 (0 EXISTS without binding citation), NFR-D02 (both
tables persisted with every hop classified).

---

### MUC-03: Happy-path-only scenarios — cover the main flow, leave exceptions naked

**Abusive actor:** Agent deriving scenarios who authors one scenario for the main flow and stops.
**Targets:** UC-05, UC-06; FR-10, FR-12.
**Misuse flow:**
1. A use case has a main flow plus exception flows (e.g. UC-06 3a).
2. The agent authors a scenario for the main flow only.
3. The exception flows have no covering scenario; failure paths are unverified.

**System response (REQUIRED):** The UC-flow-coverage gate MUST enumerate ALL
flows — main, alternate, AND exception — and require a covering scenario (or
recorded out-of-scope) for each (NR-03). An uncovered exception flow ⇒ verdict
`gaps`; the gate blocks (FR-12, UC-06 3a).

**Related NFRs:** NFR-S04 (fail closed), NFR-03 (gate is fast enough to always run).

---

### MUC-04: Silent flow drop — make a flow disappear so no scenario is owed

**Abusive actor:** Agent who removes or omits a flow from the use case so coverage looks complete.
**Targets:** UC-06; FR-12, FR-13.
**Misuse flow:**
1. A flow is awkward to cover.
2. The agent drops it from the use-case spec entirely.
3. The coverage gate sees fewer flows and passes — the dropped flow is unverified and unrecorded.

**System response (REQUIRED):** A use-case flow MUST NOT be dropped silently
(NR-05). An out-of-scope flow MUST be RECORDED as an explicit out-of-scope
decision (and, where it is a product/scope decision, captured as a BDR per
FR-17). The coverage gate treats recorded out-of-scope as covered-by-decision;
an unrecorded absence is a gap.

**Related NFRs:** NFR-D01 (coverage sourced from the brain, not agent claim — a
dropped flow cannot be hidden if it was ever emitted).

---

### MUC-05: One-surface walk — walk the UI, ignore the tool surface (or vice versa)

**Abusive actor:** Agent who walks only the human journey and never the machine consumer's path.
**Targets:** UC-03, UC-04; FR-07, FR-08.
**Misuse flow:**
1. A behavioural change exposes both a screen and a set of tool operations.
2. The agent walks the UI journey, classifies its hops, and stops.
3. The tool surface — the agent/SDK consumer's path — is never walked; its
   unwired operations go undetected (the generalised MCP-Apps lesson).

**System response (REQUIRED):** For a behavioural change that has both surfaces,
the system MUST walk BOTH (NR-04, FR-08). The produced `## Journey Walk` MUST
carry a UI table AND a tool table (NFR-D02). A change with a tool surface and no
tool-surface walk does not complete the design stage. (Pure docs/infra remains
explicitly exempt with a recorded reason.)

**Related NFRs:** NFR-S01 (bounded extra cost so two-surface is affordable),
NFR-D02 (both tables persisted).

---

### MUC-06: Fake-green tool scenario — mark a tool scenario passing without driving it

**Abusive actor:** Agent who records a tool scenario green from inspection, not from a real round-trip.
**Targets:** UC-05; FR-10, FR-14.
**Misuse flow:**
1. A tool scenario is authored.
2. The agent asserts it works by reading the code rather than driving it.
3. It is recorded green; in reality the round-trip was never exercised.

**System response (REQUIRED):** A tool scenario MUST NOT report green without a
real driven round-trip (NR-06). Green requires a deposited passing TestResult
from the #98 substrate (observed) or an explicit attestation (NFR-S03). An
undrivable tool scenario is recorded as a deferred infrastructure need
(NFR-R02), never marked green.

**Related NFRs:** NFR-S03 (no green without a real drive), NFR-R02 (deferred, not
dropped).

---

### MUC-07: Contract-as-afterthought — describe the solution but ship no reviewable interface contract

**Abusive actor:** Agent that designs the solution and walks the tool surface but
treats the contract as something to discover at integration time — or emits a
schema-only contract that two engineers could integrate against but a founder
cannot review.
**Targets:** UC-02, UC-04; FR-18, FR-19.
**Misuse flow:**
1. A change exposes a tool surface (a producer/consumer seam — the thing Phase 2 is fundamentally about).
2. The agent writes the Solution Design and even walks the tool operations, but ships no interface-contract section — or a schema-only contract (operations + types + errors) with none of the CF-10 founder-facing dimensions (auth, audience, plain-language guide, error fixes).
3. The seam is built backwards: the backend is written, then the consumer is "designed" against whatever it returned (the CF-01 anti-pattern). The founder who has to greenlight the work cannot review the seam — it is integratable but not reviewable. Gaps a contract would have caught (a missing `list` behind a list view, an unflagged auth requirement) surface only at integration.

**System response (REQUIRED):** For a change with a tool surface, the system MUST
produce an interface-contract section carrying the schema layer AND all four CF-10
dimensions (NR-07, FR-18); the contract MUST be authored first for cross-kind
seams and referenced by both producer and consumer (NR-08, FR-19, CF-01/CF-05);
the tool-surface walk's operations MUST be a subset of the contract's operations
(NR-08, FR-19). A tool surface with no contract section, or a contract missing the
founder-facing dimensions, MUST NOT complete the design stage (the structure check
/ P-VER blocks it). Where the project already produces ServiceSpecs, the
ServiceSpec IS the contract (CF-10).

**Related NFRs:** NFR-D02 (the contract section, like both walk tables, is
persisted in the design document, not transient), NFR-S02 (the ServiceSpec
binding cited for tool EXISTS is the wiring of a contract operation).

---

## Pre-mortem (top failure scenarios, 6 months live)

1. **Cost backlash.** The always-comprehensive document makes lite changes feel
   heavy; founders start avoiding `/sulis:specify`. → Mitigated by NFR-02 (bounded
   cost) and keeping the *interview* small at lite depth.
2. **Tool-walk theatre.** Agents cite ServiceSpec bindings that exist but are
   stale/wrong, satisfying the letter of FR-09 without the substance. → Surfaced
   as a risk in HANDOVER; the real-drive scenario (NFR-S03) is the backstop.
3. **Gate fatigue.** Three coverage gates (#103, #86, UC-flow) overlap and
   produce confusing multi-block verdicts. → HANDOVER recommends a unified verdict
   surface; the three gates stay distinct in logic but report as one founder-facing
   result.
4. **Hollow contracts.** Agents emit a contract section to satisfy the structure
   check but fill the CF-10 founder-facing dimensions (audience, plain-language
   guide, error fixes) with thin boilerplate — the letter of FR-18 without the
   substance, so the founder still can't really review the seam. → The Lovable Test
   (CF-10) is the substantive bar; SEA's decompose-validation P7 will enforce it
   mechanically. Until then it is a HANDOVER risk + a hand-held review bar.

## Coverage check

| Security-sensitive use case | Misuse coverage |
|-----------------------------|-----------------|
| UC-02 (always-produce doc) | MUC-01 |
| UC-03 (UI walk) | MUC-02, MUC-05 |
| UC-04 (tool walk) | MUC-02, MUC-05 |
| UC-05 (scenario derivation) | MUC-03, MUC-06 |
| UC-06 (coverage gate) | MUC-03, MUC-04 |
| UC-02 (always-produce doc) / UC-04 (tool walk) | MUC-07 |
