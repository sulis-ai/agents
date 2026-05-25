# Cognitive Load Standard

<!-- summary -->
Six principles (CL-01 through CL-06) for managing cognitive load in user-facing
interfaces, documentation, and communication. Grounded in cognitive psychology research
(Sweller, Kahneman, Miller). All principles are at SHOULD with 90-day calibration notes
— see Version History.
<!-- /summary -->

> **Version:** 1.0.0
> **Status:** Active — Calibration Period

---

## Provenance

These principles encode cognitive psychology research applied to interface and content
design, drawing on: Cognitive Load Theory (Sweller, 1988), dual-process theory
(Kahneman, 2011), working memory capacity limits (Miller, 1956; Cowan, 2001), and the
expertise reversal effect (Kalyuga et al., 2003).

This standard synthesises peer-reviewed research into actionable design principles.

---

## Boundary Definition

This standard contains **universal cognitive load principles only**. Content belongs here
if and only if it passes the **ProjectX test**: replacing every project name, file path,
and technology-specific example with a fictional "ProjectX" equivalent requires zero
semantic changes to the principle statement.

Content that fails the ProjectX test belongs in the project's architecture file, not here.

---

## Severity Convention

| Severity | Meaning |
|----------|---------|
| **MUST** | Non-negotiable. Violations block delivery. |
| **SHOULD** | Default. Deviation requires explicit justification. |

---

## Principles

### CL-01: Working Memory Limit

**Severity:** SHOULD

> **Calibration note (expires 2026-06-10):** New principle — collecting execution
> evidence. Promotion to MUST requires evidence from 3+ executions.

**Rule:** No single view, message, or interaction step presents more than 4 (±1)
independent information chunks simultaneously. When more information is necessary,
use progressive disclosure — reveal detail on demand rather than all at once.

| Attribute | Detail |
|-----------|--------|
| **Verification** | Count the independent information chunks in each view or message. If a user must hold more than 5 unrelated items in working memory to complete a task, the design violates this principle. |
| **In Practice** | Group related items so they form a single chunk. Use headings, whitespace, and hierarchy to signal grouping. Break multi-step processes into discrete stages where each stage requires attention to at most 4 items. Use summaries with expand-on-demand for detailed content. |
| **Anti-Pattern** | Presenting 10+ options in a flat list with no grouping. Showing all configuration fields on a single screen. Long unstructured paragraphs that require the reader to hold many concepts simultaneously. |

**Source:** Miller, G.A. (1956). The magical number seven, plus or minus two. Updated
by Cowan, N. (2001) to 4 ± 1 for independent chunks in the absence of rehearsal.

---

### CL-02: Intrinsic Load Prioritisation

**Severity:** SHOULD

> **Calibration note (expires 2026-06-10):** New principle — collecting execution
> evidence. Promotion to MUST requires evidence from 3+ executions.

**Rule:** Prioritise intrinsic cognitive load (the inherent complexity of the task)
over extraneous load (complexity added by the presentation). If users are struggling,
reduce extraneous load first — simplify the interface, not the underlying task.

| Attribute | Detail |
|-----------|--------|
| **Verification** | For any point of user difficulty, classify the source as intrinsic (task complexity) or extraneous (presentation complexity). If extraneous load has not been minimised first, the design violates this principle. |
| **In Practice** | Use clear, consistent terminology. Eliminate decorative elements that do not aid comprehension. Ensure navigation and layout conventions are consistent across views. Place related information physically close together (spatial contiguity). Present related text and visuals simultaneously, not sequentially (temporal contiguity). |
| **Anti-Pattern** | Adding visual complexity (animations, gratuitous icons, inconsistent layouts) that does not serve comprehension. Using jargon or inconsistent terminology that forces users to translate mentally. Requiring users to flip between pages to compare related information. |

**Source:** Sweller, J. (1988). Cognitive load during problem solving: Effects on
learning. Cognitive Science, 12(2), 257–285.

---

### CL-03: Expertise-Appropriate Design

**Severity:** SHOULD

> **Calibration note (expires 2026-06-10):** New principle — collecting execution
> evidence. Promotion to MUST requires evidence from 3+ executions.

**Rule:** Match information density and scaffolding to the user's expertise level.
Novices need guidance and structure. Experts need efficiency and directness. Providing
expert-level density to novices overwhelms them; providing novice-level scaffolding to
experts wastes their time and creates extraneous load (the expertise reversal effect).

| Attribute | Detail |
|-----------|--------|
| **Verification** | Identify the target audience's expertise level. Verify that the information density and scaffolding match. If novice users encounter expert-density content without scaffolding, or expert users are forced through unnecessary tutorials, the design violates this principle. |
| **In Practice** | For novice audiences: provide step-by-step guidance, define terms on first use, use examples before abstractions. For expert audiences: provide direct access to controls, use standard domain terminology without over-explanation, enable keyboard shortcuts and power-user flows. For mixed audiences: use progressive disclosure — sensible defaults with advanced options available on demand. |
| **Anti-Pattern** | Assuming all users are experts and omitting all guidance. Assuming all users are novices and adding mandatory tutorials that experts cannot skip. Using the same information density for onboarding flows and power-user dashboards. |

**Source:** Kalyuga, S., Ayres, P., Chandler, P., & Sweller, J. (2003). The expertise
reversal effect. Educational Psychologist, 38(1), 23–31.

---

### CL-04: Choice Reduction

**Severity:** SHOULD

> **Calibration note (expires 2026-06-10):** New principle — collecting execution
> evidence. Promotion to MUST requires evidence from 3+ executions.

**Rule:** When presenting choices, limit options to the minimum necessary for the
decision at hand. Provide sensible defaults. Group and categorise options when
more than 4 are required. Every additional option imposes a cognitive cost — justify
each one.

| Attribute | Detail |
|-----------|--------|
| **Verification** | Count the options presented at each decision point. If more than 4 ungrouped options are presented without a recommended default, the design violates this principle. |
| **In Practice** | Provide a recommended default for common decisions. When many options are necessary, group them into categories of 3–4. Use progressive disclosure: show common options first, reveal advanced options on demand. Remove options that are rarely used or can be computed automatically. |
| **Anti-Pattern** | Presenting 15 ungrouped options and requiring the user to evaluate all of them. Providing no default when one option is clearly most common. Showing every possible configuration on first use. |

**Source:** Hick, W.E. (1952). On the rate of gain of information. Quarterly Journal
of Experimental Psychology, 4(1), 11–26. Iyengar, S.S. & Lepper, M.R. (2000). When
choice is demotivating.

---

### CL-05: System 1 / System 2 Awareness

**Severity:** SHOULD

> **Calibration note (expires 2026-06-10):** New principle — collecting execution
> evidence. Promotion to MUST requires evidence from 3+ executions.

**Rule:** Design routine interactions for System 1 (fast, intuitive) processing.
Reserve System 2 (slow, deliberate) engagement for decisions that genuinely require
careful thought. Never bury a critical decision inside a routine flow where the user
is operating on autopilot.

| Attribute | Detail |
|-----------|--------|
| **Verification** | Map each interaction to System 1 (routine) or System 2 (deliberate). If a high-stakes decision is embedded in a routine flow with no friction to trigger deliberate thought, the design violates this principle. If a routine action requires unnecessary deliberation, it creates extraneous load. |
| **In Practice** | For routine actions: use familiar patterns, consistent placement, and predictable behaviour so users can act without deliberation. For high-stakes decisions: introduce appropriate friction — confirmation dialogs, summary screens, distinct visual treatment — to shift the user into System 2. Signal the transition clearly. |
| **Anti-Pattern** | Placing a destructive action (delete, publish, send) in the same visual style and position as routine actions with no confirmation. Requiring deliberation for trivial choices (e.g., forcing users to read a paragraph before clicking "OK" on a routine save). Overusing confirmation dialogs so they become routine and are dismissed without reading. |

**Source:** Kahneman, D. (2011). Thinking, Fast and Slow. Farrar, Straus and Giroux.

---

### CL-06: Coherent Mental Model

**Severity:** SHOULD

> **Calibration note (expires 2026-06-10):** New principle — collecting execution
> evidence. Promotion to MUST requires evidence from 3+ executions.

**Rule:** Present information in a way that builds and reinforces a coherent mental
model. Use consistent metaphors, terminology, and structure. When introducing new
concepts, connect them to the user's existing mental model rather than requiring them
to build a new one from scratch.

| Attribute | Detail |
|-----------|--------|
| **Verification** | Review terminology, metaphors, and structural patterns across the system. If the same concept is referred to by different names, or different concepts share the same name, the design violates this principle. If a new feature contradicts the mental model established by existing features, it violates this principle. |
| **In Practice** | Use a consistent glossary — one name per concept, one concept per name. Structure information hierarchically so the user can navigate by their mental model. When introducing a new concept, relate it to something the user already understands. Use spatial and visual consistency (same type of information appears in the same position across views). |
| **Anti-Pattern** | Using "project", "workspace", and "space" interchangeably for the same concept. Placing navigation elements in different positions on different pages. Introducing a concept that contradicts the metaphor used elsewhere (e.g., "folders" that do not nest). |

**Source:** Sweller, J. (1988). Schema acquisition and the role of coherent mental
models in complex problem solving. Johnson-Laird, P.N. (1983). Mental Models.

---

## Verification Checklist

Before delivering any user-facing interface, documentation, or communication, verify:

- [ ] **CL-01:** No view or message requires holding more than 4–5 independent chunks
  in working memory simultaneously
- [ ] **CL-02:** Extraneous cognitive load has been minimised before simplifying
  intrinsic task complexity
- [ ] **CL-03:** Information density matches the target audience's expertise level
- [ ] **CL-04:** Decision points present grouped options with sensible defaults;
  no ungrouped list exceeds 4 options without justification
- [ ] **CL-05:** Routine interactions are intuitive (System 1); high-stakes decisions
  have appropriate friction (System 2)
- [ ] **CL-06:** Terminology, metaphors, and structure are consistent throughout

---

## Applicability

This standard applies to:

- **User interfaces** — web, mobile, desktop, CLI
- **Documentation** — user guides, API documentation, onboarding materials
- **Communication** — notifications, error messages, system feedback
- **Content design** — any content delivered to end users
- **AI-generated output** — responses, summaries, recommendations

It does not apply to:

- Internal developer tooling where the audience is exclusively domain experts
  (though CL-02 and CL-06 are still recommended)
- Raw data exports or API responses consumed by machines, not humans

---

## Relationship to Other Standards

| Standard | Relationship |
|----------|-------------|
| Engineering Principles (EP) | EP-07 (SOLID and Clean Code) applies cognitive load reduction to code readability. CL principles extend the same thinking to user-facing surfaces. |
| Security Standard (SEC) | SEC-05 (Safe Error Handling) intersects with CL-01 — error messages must be comprehensible without overwhelming the user. CL principles inform how security-relevant information is presented to users. |
| Coaching Without Conflict | CL-04 (Choice Reduction) directly applies to feedback delivery — limit feedback to actionable items rather than overwhelming with every observation. |
| Critical Thinking Standard | EH (Epistemic Humility) and HU (Hierarchy of Evidence) inform how confidence levels are communicated to users without creating false certainty or unnecessary cognitive burden. |

---

## References

- Cowan, N. (2001). The magical number 4 in short-term memory: A reconsideration of
  mental storage capacity. Behavioral and Brain Sciences, 24(1), 87–114.
- Hick, W.E. (1952). On the rate of gain of information. Quarterly Journal of
  Experimental Psychology, 4(1), 11–26.
- Iyengar, S.S., & Lepper, M.R. (2000). When choice is demotivating: Can one desire too
  much of a good thing? Journal of Personality and Social Psychology, 79(6), 995–1006.
- Johnson-Laird, P.N. (1983). Mental Models: Towards a Cognitive Science of Language,
  Inference, and Consciousness. Harvard University Press.
- Kahneman, D. (2011). Thinking, Fast and Slow. Farrar, Straus and Giroux.
- Kalyuga, S., Ayres, P., Chandler, P., & Sweller, J. (2003). The expertise reversal
  effect. Educational Psychologist, 38(1), 23–31.
- Miller, G.A. (1956). The magical number seven, plus or minus two: Some limits on our
  capacity for processing information. Psychological Review, 63(2), 81–97.
- Sweller, J. (1988). Cognitive load during problem solving: Effects on learning.
  Cognitive Science, 12(2), 257–285.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-03-13 | Adapted from cross-cutting standard for general use. Six principles (CL-01 through CL-06), all at SHOULD with 90-day calibration notes. |
