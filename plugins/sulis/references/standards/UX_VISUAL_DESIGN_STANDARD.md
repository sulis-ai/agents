# UX & Visual Design Standard — The Contract With the User

> **Sulis-local v0.2.0 (2026-05-26).** The design-time **contract with the
> user**: the promise a product makes to a human about how it will *look*,
> *behave*, *communicate*, and *respect* them. It is the human-facing sibling
> of the machine-facing data contract (`CONTRACT_FIRST_STANDARD.md`). Just as
> the API contract is agreed before backend/frontend build, **the design is
> agreed before the frontend is built** — so that when a frontend is designed,
> it is **designed well**, not improvised.
>
> This standard defines the **discipline and method**. The **identity values**
> themselves (the WHY, the palette, the type, the look) are **founder-owned**,
> produced through the design flow — see the carve-out.

<!-- summary -->
A product's UI is a contract with its user. This standard makes that contract
rigorous across four layers: **Identity** (the brand flows WHY→HOW→WHAT and is
distinctive, not generic), **Visual** (brand traits translate to *measurable*
visual parameters; three-tier design tokens are the single source of truth;
visual identity is evaluated systematically, not subjectively), **Experience**
(accessibility decided at design time to WCAG 2.1 AA; human-centred design
process; ethical evidence-based behaviour; agentic-interface UX for AI;
honest voice), and **Governance** (cross-artifact coherence; AI provenance;
design-before-build). The frontend then implements this contract (`WP_FRONTEND_STANDARD.md`).
<!-- detail -->

## Severity convention

`MUST` — non-negotiable. `SHOULD` — default; deviation needs a rationale.
`MAY` — judgement.

## The model — two contracts, one frontend

| | Data contract | **Visual / UX contract (this)** |
|---|---|---|
| Standard | `CONTRACT_FIRST_STANDARD.md` | this one |
| Between | producer ↔ consumer (machines) | **product ↔ user (human)** |
| Defines | operations + types + errors | identity + tokens + components + interaction + behaviour + voice |
| Built against by | the frontend's typed client (WPF-02) | the frontend's components + tokens (WPF-06/07/12) |

Both are **design-time artifacts**; both precede the build; the frontend
conforms to both.

> The discipline below is drawn from a full design lifecycle. The whole set
> applies to a *new product's* design; for a *single change* on an existing
> product, the identity/visual layers are usually already settled — apply the
> Experience + Governance layers and conform to the existing tokens.

---

## Layer 1 — Identity (the WHY)

### UXD-01 — Identity before visuals (Golden Circle) · MUST

Visual identity derives from articulated identity in strict order: **WHY**
(beliefs, founding story) → **HOW** (differentiating approach, values) →
**WHAT** (expression: brand, voice, visuals). Never back-rationalise an
identity from a logo that already exists.

> **Anti-pattern:** "we like this colour/logo, let's invent a reason" — a WHAT
> dressed up as a WHY. Produces inauthentic identity that fails UXD-02.

### UXD-02 — Distinctiveness (substitution test + distinctive assets) · MUST

Every identity claim and asset passes the **competitor substitution test**: if
a named competitor can be substituted into the same statement and it stays
true, the articulation is **generic** and must be revised until substitution
makes it false. Name **3–7 distinctive assets** and classify each as
**Convention** (intentionally follows category norms) or **Deliberate
Distinction** (intentionally deviates).

> **In practice:** "Sulis provides certainty" fails ("Notion provides
> certainty" is also true); "structural certainty to turn an idea into a
> viable business end-to-end" passes.
> **Anti-pattern:** an identity that any competitor could also claim.

---

## Layer 2 — Visual (what it looks like)

### UXD-03 — Brand-to-visual translation with *measurable* parameters · MUST

Each brand trait translates to **concrete visual characteristics expressed as
measurable parameters** — pixel values, ratios, percentages, contrast ratios —
not subjective adjectives. "Trustworthy" becomes "visual centre of mass in the
lower 60%; bilateral symmetry; deviation ≤15%", not "feels solid".

> **In practice (Sulis's own):** Expert → uniform 2–4px strokes on an 8px grid;
> Empowering → ≥30% negative space, 8–12px radii; Trustworthy → grounded weight,
> ≤15% asymmetry. (See the exemplar in the carve-out.)
> **Anti-pattern:** a "design principle" that's only an adjective with no
> measurable parameter a builder or reviewer can check.

### UXD-04 — Three-tier design tokens (W3C DTCG) · MUST

Tokens are the single source of visual truth in three tiers: **primitive**
(raw values — never used directly), **alias/semantic** (`color.primary` →
`blue.500` — what components reference), **component** (`button.background` →
`color.primary`). **No component token without an alias parent.** Tokens carry
theming and pre-validated contrast.

> **Anti-pattern:** hardcoded hex/px in components; a component token pointing
> straight at a primitive; a palette with no machine-readable token export.

### UXD-05 — Systematic visual-identity evaluation (not subjective) · MUST

Visual identity is evaluated against **multi-dimensional criteria**, citing at
least three: **distinctiveness, memorability, adaptability** (renders 16px →
hero), **cultural appropriateness, production viability, convention-distinction
balance**. No artifact is approved on "it looks professional".

> **Anti-pattern:** single-criterion approval; aesthetic judgement with no
> documented rationale; a mark that breaks at favicon size.

### UXD-06 — A visual + interaction spec (the HIG) · MUST

A spec defines, per component: **variants, sizes, states**
(default/hover/active/disabled/**focus**), **focus management** (order,
trapping, restoration), the **three UI states** (loading / empty / error), and
the **structural profile** (navigation, layout, density, elevation strategy).
The frontend implements to it.

> **Anti-pattern:** components designed ad hoc per screen; undefined
> loading/empty/error treatment; inconsistent focus behaviour.

---

## Layer 3 — Experience (how it behaves with the user)

### UXD-07 — Accessibility decided at design time (WCAG 2.1 AA) · MUST

WCAG AA is built into the **design**, not retrofitted (3–10× cheaper up front).
At design time: token colour pairs meet contrast (**4.5:1** text, **3:1**
large/non-text), information is **never by colour alone**, **focus is visible**,
interactions are **keyboard-operable**, components carry **name/role/value**.
Each colour's contrast ratio is recorded against its background; colours that
fail (e.g. a gold accent at 2.14:1) are marked **decorative-only** and may
never carry functional meaning. The frontend verifies (WPF-06: axe).

### UXD-08 — Human-centred design process (ISO 9241-210) · MUST for experience work

Experience design follows: (1) understand **context of use**, (2) specify user
**requirements**, (3) produce **design solutions**, (4) **evaluate** against
requirements. Context-of-use evidence MUST exist *before* solutions are
proposed.

> **Anti-pattern:** proposing flows/screens with no evidence of who the user is
> or what they're trying to do.

### UXD-09 — Ethical, evidence-based behavioural design (EAST) · SHOULD

Journeys involving multi-step decisions or progression use evidence-based
behavioural patterns (EAST: **Easy, Attractive, Social, Timely**), citing
sources. Every nudge is **transparent, resistible, and welfare-improving** —
never a dark pattern.

> **Anti-pattern:** engagement-optimisation dressed as UX; confirm-shaming;
> hard-to-cancel flows; nudges with no evidence and no user benefit.

### UXD-10 — Agentic-interface UX (for AI surfaces) · MUST for AI features

AI / chat / autonomous surfaces follow seven evidence-based principles:

- **MUST:** **outcome-oriented** (chat coordinates; purpose-built UI delivers
  the work); **human-in-the-loop gates** (approval before consequential
  actions; start/pause/stop); **failure recovery** (change approach after
  repeated failure; acknowledge + explain + alternative); **transparency**
  (source attribution, honest-confidence vocabulary, label AI output).
- **SHOULD:** **dual-mode input** (suggestion chips + free text + slash
  commands); **progressive autonomy** (earn trust; confidence indicators);
  **category-organised discovery** (group by intent, not flat lists — 5+
  capabilities).

> **In practice (the cockpit):** chat coordinates; the dashboard + file/diff
> views deliver; nuke/ship prompt first; honest confidence, no false certainty.

### UXD-11 — UI voice & tone · SHOULD

Microcopy is design. Errors, empty states, confirmations follow **tone-by-
severity** and the project voice (`TONE_STANDARD.md`): plain, specific, honest;
say what happened and what to do next.

> **Anti-pattern:** `Error: undefined`; jokey copy on a critical failure; a
> blank empty state with no guidance.

---

### UXD-16 — Cognitive load (the burden the surface imposes) · MUST

A surface MUST minimise the cognitive burden it imposes — the load is part of
the contract with the user, not an afterthought. Sourced from the platform
`cognitive-load.md` standard (CL-01..06):

- **CL-01 Extraneous-load elimination (MUST).** Every element must serve the
  user's task or comprehension; decorative / redundant / organisationally-
  convenient-but-user-irrelevant elements are removed. Per-element test: *"does
  this help the user complete their task or understand the content?"* — if no,
  it's extraneous load.
- **CL-02 Intrinsic-load management (MUST).** A surface where the user must hold
  **> 5 simultaneous concepts/decisions** MUST use progressive disclosure /
  staged steps / collapsible sections (working-memory ≈ 4±1).
- **CL-04 Choice reduction (MUST).** ≤ **5 primary options** at any decision
  point; secondary actions visually subordinate or progressively disclosed;
  primary actions visually distinct from secondary.
- **CL-05 Consistency expectation (MUST).** Similar elements behave consistently
  within the product and follow platform conventions the audience already knows
  (Jakob's Law) — don't make them relearn.
- **CL-03 Germane-load optimisation (SHOULD).** Consistent patterns + meaningful
  groupings + explicit relationships help the user build an accurate mental
  model.
- **CL-06 Three-question design review (SHOULD).** The visual-contract review
  (and any design review) explicitly asks: (1) *is this complexity necessary?*
  (intrinsic) (2) *does our presentation add unnecessary burden?* (extraneous)
  (3) *does this help users build a mental model?* (germane). Visual review
  alone misses load issues.

> **Anti-pattern:** a settings screen with 12 equally-weighted controls (CL-04);
> a wizard that shows all 9 fields at once instead of staging them (CL-02);
> a dashboard whose decorative chrome competes with the one number that matters
> (CL-01).

---

## Layer 4 — Governance (cross-cutting)

### UXD-12 — Cross-artifact coherence · SHOULD

When multiple design artifacts exist, verify pairwise coherence with
**mechanistic** (enumerable PASS/FAIL) checks before downstream use: every brand
colour has a semantic token (zero orphans); every interaction pattern named in
the experience spec is defined in the HIG; microcopy conforms to the voice.

### UXD-13 — AI artifact provenance (tri-track) · SHOULD

Design artifacts produced with AI carry a provenance label: **AI-generated →
human-reviewed → production-approved**, advancing only through review (not
time). The founder approves before an artifact is consumed by the build.

### UXD-14 — The visual contract precedes the build · MUST (a hard gate)

Like contract-first for data: the visual/UX contract (identity → tokens → spec
→ experience patterns) precedes the build. It is a **`kind: contract` WP**
(`contract_type: visual`) carrying a real-token mockup; every `kind: frontend`
WP MUST declare `visual_contract: <its id>` and `dependsOn` it. This is
**enforced by the toolchain**, not just doctrine (#45):

- `wpx-index` refuses a `kind: frontend` WP that doesn't declare + depend on a
  visual-contract WP (write-time gate).
- The visual-contract WP reaches `done` only when its mockup is **signed off**
  — `signed_off_at` set + `provenance: production-approved` — refused at
  `flip-status` otherwise (runtime gate).
- Because frontend WPs depend on it, list-ready won't dispatch any frontend
  work until the founder has signed off.

**Sign-off is visual, not value-equality (L-13).** The mockup MUST load the
webfonts its type tokens reference and be approved *rendered* — a real
production failure passed "tokens match" while the founder saw no brand
because the fonts never loaded. "Looks like the brand" is the founder's
judgement at sign-off; token-value matching is necessary but not sufficient.

**The only bypass** is a logged exemption (`visual_contract: exempt —
<reason>` on the frontend WP) or a `prototype: true` WP — rare, explicit,
never silent.

> **Anti-pattern:** building components first and "extracting a design system
> later"; design and build drifting because neither is the source of truth;
> declaring a mockup "matched" on token values without the founder seeing it
> rendered.

---

## Optional inspiration inputs (Mobbin MCP)

### UXD-15 — Inspiration informs patterns, never identity · MUST when MCP connected, MAY otherwise

When the visual-contract producer runs (`draft-architecture` step 3.5(b) — see
UXD-14), it **MUST probe the Mobbin MCP if connected** and persist the
results as a **referenceable doc** the mockup is built against and `review`
later verifies against. When the MCP is not connected the probe is skipped
cleanly (no fabrication); the design flow proceeds without external
references.

**The guardrail is firm: inspiration informs *patterns*, never *identity*.**
The product's own identity, tokens, voice, and distinctive assets
(UXD-01/02/03/04) remain **authoritative**. Mobbin shows *how others
structured a problem*; it never sets *what this product looks like*. Borrowing
a competitor's visual identity would directly violate UXD-02 (distinctiveness).

- **MCP-gated.** Connected → probe MUST run; disconnected → skipped cleanly.
  No fallback fabrication.
- **Account-bound.** Inspiration comes from the founder's connected Mobbin
  account; the MCP runs under their credentials.
- **Persisted referenceable artifact (MUST).** The probe writes
  `.architecture/{project}/contracts/visual/_mobbin-context.md` — per-reference
  (app name, URL, structural observations marked *transferable* and visual
  observations marked *NOT transferable*) plus a 2–4 line synthesis. The
  visual-contract WP's `inspiration:` frontmatter cites the path. Because
  `.architecture/` travels with the change branch (#42), the research is
  durable; `review` reads it post-build to verify the shipped surface honoured
  the cited structural patterns (the loop closes).
- **Scope hard-bound.** *Structural* patterns (section ordering, density,
  spacing rhythm, micro-interactions) are transferable. *Visual* choices
  (palette, type stack, mark) are NOT — they stay bound to the design
  instance. The mockup never embeds Mobbin screenshots; the produced surface
  never adopts a referenced app's identity.
- **Worked-example carve-out.** If the project's design instance already
  covers the surface tightly via `reference/` or `examples/`, log the skip
  and proceed without the probe.

> **In practice:** "show me how shipped apps structure a multi-change
> workspace" → Mobbin returns layout/interaction patterns → they inform the
> HIG's structural profile (UXD-06) → but the cockpit still wears Sulis's
> tokens, voice, and mark.
> **Anti-pattern:** importing a referenced app's colours/type/feel wholesale;
> letting inspiration become imitation; an undistinctive UI that "looks like
> every other tool" (fails UXD-02).

> Connection is documented as an **optional MCP server** (see the plugin's MCP
> config). This standard governs *how* the input is used; connecting the
> account is the founder's choice.

---

## Founder-owned: identity & brand values (the carve-out)

This standard governs the **discipline and method**. It does **not** prescribe
the **identity and brand values** — the WHY, the colour palette, the
typography, the logo, the look-and-feel. Those are **founder-owned product
decisions** (brand is a CEO call), produced through the **design flow**
(`design-system` / `sulis-design` tooling, which emits the identity docs,
tokens, and a visual preview).

So: this standard says *"each brand trait maps to a measurable visual
parameter, and every functional colour meets AA contrast"* (discipline); it
does **not** say *"the primary colour is Deep Wisdom navy"* (identity). The
identity is the conversation to have; its output **populates** the layers this
standard requires.

**Worked exemplar:** Sulis's own `VISUAL_PRINCIPLES.md` (Bath/Minerva heritage
→ abstract qualities; Deep Wisdom #1E3A5F primary at 10.93:1; warm-neutral
foundation; Satoshi/Inter; 70:30 geometric-to-organic; measurable parameters
throughout) is what a *completed* identity looks like when this standard is
applied. Use it as the shape, not the content, for other products.

---

## Tooling (governs vs produces)

This standard **governs**; existing tooling **produces** the artifacts:

- `design-system` skill — generates `DESIGN.md` + a visual preview + token
  exports (CSS/JSON) from a URL or repo.
- `sulis-design` flow — the founder-facing "design the brand" path that
  produces the identity → brand → visual → experience artifacts.

The standard is the contract; the tools fill it in with the founder's identity.

---

## Verification categories (what a reviewer checks)

| Prefix | Checks | Method |
|--------|--------|--------|
| **IDC** | Golden Circle order; substitution test; distinctive assets | LLM-judge + manual + founder approval |
| **TOK** | Three-tier token integrity (W3C DTCG); no orphan colours | automated + manual |
| **VID** | Multi-dimensional visual-identity evaluation; multi-size render | manual + automated SVG/render |
| **CXD** | Context-of-use before solutions; cited behavioural evidence | LLM-judge + manual |
| **DAC** | Design-time WCAG AA (contrast, keyboard, colour-independence) | contrast checker + axe + manual |
| **COH** | Pairwise cross-artifact coherence | automated mechanistic + LLM-judge |
| **GOV** | Provenance labels; governance classification | manual + LLM-judge |

---

## Provenance

Consolidated from the reviewed design documents (2026-05-26):

- platform `methodology/studios/design-lifecycle/STANDARDS.md` — the design
  discipline: Golden Circle + substitution + distinctive assets (UXD-01/02 /
  IDC-01..03); three-tier tokens (UXD-04 / DS-01); systematic visual evaluation
  (UXD-05 / DS-03); ISO 9241-210 HCD (UXD-08 / DS-04); EAST behavioural design
  (UXD-09 / DS-08); cross-outcome coherence (UXD-12 / DS-05); AI provenance
  (UXD-13 / DS-07); the verification categories.
- platform `studios/.../VISUAL_PRINCIPLES.md` (Sulis's own) — the brand-to-
  visual translation method + the measurable-parameters discipline (UXD-03) +
  the worked exemplar.
- platform `accessibility-wcag-aa.md` — the WCAG 2.1 AA baseline (UXD-07),
  sourced to W3C WCAG 2.1; enforced at design time per DS-02.
- platform `agentic-interface.md` v1.0.0 — the seven AI-surface principles
  (UXD-10), sourced to NN/g, Microsoft HAX (CHI 2019), Material Design 3,
  LangChain, ACM IUI.
- platform `cognitive-load.md` (CL-01..06) — the cognitive-load dimension
  (UXD-16), sourced to Sweller (1988), Miller (1956)/Cowan (2001), Hick (1952),
  Iyengar & Lepper (2000), Nielsen heuristics, Jakob's Law.

**Identity/brand values are excluded by design** (founder-owned carve-out).
External platform standards' essentials are inlined for self-containment.

---

## Version history

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-05-26 | Initial 7-requirement draft (tokens, HIG, design-time WCAG, agentic UX, voice, responsive, design-before-build). |
| 0.2.0 | 2026-05-26 | Deepened into "the contract with the user" across four layers (Identity / Visual / Experience / Governance), 14 requirements (UXD-01..14). Adds the identity layer (Golden Circle, substitution test, distinctive assets), measurable-parameters discipline, systematic visual evaluation (Rand criteria), ISO 9241-210 HCD, ethical EAST behavioural design, cross-artifact coherence, AI provenance, and the verification categories — grounded in the design-lifecycle studio standards + Sulis's own VISUAL_PRINCIPLES exemplar. SHOULD-tier items carry 90-day calibration. |
| 0.3.0 | 2026-06-03 | Added UXD-16 (Cognitive load) — the missing dimension, sourced from the platform `cognitive-load.md` standard (CL-01..06: extraneous-load elimination, intrinsic-load via progressive disclosure ≤5 concepts, choice reduction ≤5 primary options, consistency expectation, germane-load, three-question review). Closes the gap where the standard covered identity/visual/experience/agentic but not the burden the surface imposes. Owned end-to-end by the new `ux-designer` specialist agent (which also covers design-system *establishment* when none exists). |
