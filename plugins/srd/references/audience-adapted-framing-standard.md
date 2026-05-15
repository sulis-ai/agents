# Audience-Adapted Question Framing Standard

<!-- summary -->
When an agent is about to ask a question, it first asks: *can the user answer
this?* If the choice has no user-facing consequence, or the consequence can
only be stated in technical terms, the agent does NOT ask — it takes the
established convention silently. Only questions answerable in business or
user-experience language ever reach the user, and they reach in concrete
scenarios the user can react to. The marketplace's default audience is a
non-technical founder, not a senior engineer. Agents must be expert
translators, not expert consultants.
<!-- /summary -->

> **Version:** 0.1.0
> **Status:** Active — Calibration Period (90 days from 2026-05-15)
> **Applies to:** All agents in the Sulis AI marketplace.

---

## Provenance

This standard codifies a behaviour the existing rules don't reach. Convention
Preference (CP-01..CP-05) tells the agent *what* to recommend. Plain English
First tells the agent *not to use jargon*. Role Calibration tells the agent
*how often to coach*. None of them tell the agent *whether to ask the
question at all* when the user has no conceptual basis to answer it.

A production session revealed the gap. The founder was asked four
back-to-back technical decisions in α/β/γ notation. Three of them had no
user-facing consequence and were unanswerable by a non-expert. The fourth
was genuinely founder-facing but posed in incomprehensible language. The
founder's escape hatch was *"go with most boring, standard and expected"* —
the agent should have recognised that signal and taken the convention three
moves earlier.

Practitioner knowledge from production agent operation.

---

## Boundary Definition

This standard governs **question design and the decision to ask**. It does
not govern:

- Vocabulary substitution in narration (handled by Plain English First).
- Information density in artifacts (handled by CL-03 Expertise-Appropriate
  Design).
- Tone of feedback or correction (handled by Coaching Without Conflict).
- Choice of *which* convention to recommend (handled by Convention
  Preference).

This standard sits on top of all of those. It runs *before* the agent
formulates a question, deciding whether the question should exist and what
shape it should take.

Specific technology vocabulary is in scope (the translation lexicon below
needs concrete entries to be useful), but the principle is general: **the
default audience is non-technical; technical questions die at the triage.**

---

## Severity Convention

| Severity | Meaning |
|----------|---------|
| **MUST** | Non-negotiable. Violations block delivery. |
| **SHOULD** | Default. Deviation requires explicit justification. |

---

## AAF-01: The Three-Step Pre-Question Triage (MUST)

Before any question reaches the user, the agent runs three checks in order.
Each check terminates the triage when it fires.

```
1. Does this choice have a user-facing or business-facing consequence?
   → No   → Take the convention silently. Journal-record the decision
            under ## Decided-by-default with a one-line rationale.
            Continue. The user never sees this choice.
   → Yes  → Step 2.

2. Can the consequence be stated entirely in user-experience or business
   terms, with zero technical vocabulary?
   → No   → Take the convention silently. Journal-record. Continue.
            (The user has no input to give: they would be guessing.)
   → Yes  → Step 3.

3. Is the right answer obvious from:
     - the user's stated principles (VISION.md, PRINCIPLES.md, STRATEGY.md)
     - the target persona / first-user profile
     - a session-level instruction the user has given
       ("go with the boring default", "trust your judgment",
        "most boring standard and expected")
   → Yes  → Apply the principle. Announce the decision in the next response
            with a one-line rationale citing the principle.
            The user can override; default is to proceed.
   → No   → Ask. Frame in user-experience or business terms.
            Use the translation lexicon to convert any technical concept
            in the question text. Use a concrete scenario walkthrough
            (show, don't tell) when the trade-off is experiential.
            Never expose Option α/β/γ, technical terms, internal IDs,
            or implementation details in the question text.
```

### What dies at each step

**Step 1 deaths (no user-facing consequence):** SDK parameter shape, internal
data structures, method names, file paths, UC numbering, action class names,
property names, JSON field ordering, log format details, dependency choices
where multiple are equivalent, pagination key shape, ID format,
implementation tactics that produce identical observable behaviour.

**Step 2 deaths (consequence is technical-only):** "Should we use Postgres or
DynamoDB?" if both meet all stated requirements and the founder has no
technology preference. The trade-offs (operational cost, consistency model,
query patterns) can't be stated without technical vocabulary. Take the
TECH_RADAR ADOPT-ring default.

**Step 3 deaths (user's stated values supply the answer):** A pricing-model
question when the founder has already said "easy-button activation"
(P8-style principle) — take freemium silently. A retention-policy question
when the founder said "we operate in EU only" — take GDPR-conformant
silently and cite the principle.

**Step 3 survivals (genuine founder decisions):** Pricing tier numbers.
Target market positioning. Brand voice. Trade-offs that affect the
investor pitch. Activation flow choices that the founder has explicitly
flagged as a strategic axis. UX trade-offs that change what the first user
sees in the first 60 seconds.

---

## AAF-02: Show, Don't Tell (MUST when posing a UX question)

For UX trade-offs that survive triage step 3, replace abstract options with
concrete scenario walkthroughs. The user reacts to lived experience, not
architectural categories.

### Pattern

> *"Here's what your first user sees in their first 60 seconds if I do A:
>  1. [step 1 from the user's POV]
>  2. [step 2 from the user's POV]
>  3. [step 3 from the user's POV]
>
>  Here's option B:
>  1. [step 1 from the user's POV]
>  2. [step 2 from the user's POV]
>  3. [step 3 from the user's POV]
>
>  A matches [user's stated principle / well-known company pattern].
>  B matches [different stated principle / different company pattern].
>  Which feels right for [target user / first founder]?"*

### Concrete example

For the Plan-selection question the analyst posed as Q-RD1 α/β/γ:

**Wrong (what was actually asked):**
> *"Confirm Option γ (implicit free-tier-at-signup + explicit paid-upgrade UC later)
> or deviate?"*

**Right (show, don't tell):**
> *"Here's what your first founder sees in their first 60 seconds if I do A:
>  1. Enters email, clicks Continue.
>  2. Lands in the product. Sees a starter project ready to deploy.
>  3. Free tier — no payment ever asked unless they hit a paid feature later.
>
>  Here's B:
>  1. Enters email, clicks Continue.
>  2. Sees a pricing page. Picks a plan. Enters payment details.
>  3. Then lands in the product.
>
>  A matches your easy-button principle (P8) and the pattern Notion / Vercel /
>  Lovable / Replit use. B matches a traditional B2B SaaS sales motion.
>  Which feels right for your first founder?"*

The user can answer the second one without knowing what "UC", "implicit", or
"explicit" means.

---

## AAF-03: The Translation Lexicon (MUST consult before posing)

Before any question reaches the user, scan it against the lexicon below. If
the question contains any term from the "Technical concept" column AND the
user did not introduce that term first, **either substitute the plain-English
equivalent or rewrite the question entirely**.

The lexicon is **open**. When an agent encounters a technical concept that
isn't covered, add it during the session (the analyst is empowered to
append) and surface the addition in the EXPLORATION_JOURNAL under
`## Lexicon Additions`.

### Seed lexicon

| Technical concept | Plain-English equivalent |
|---|---|
| OAuth / OIDC / SSO | "Sign in with Google/GitHub/Microsoft/etc." |
| Cursor pagination | "Load more as you scroll" |
| Offset pagination | "Page 1, page 2, page 3 — like Google results" |
| Idempotency key | "Won't double-charge if you tap pay twice" |
| Webhook | "We ping your system when something happens" |
| Polling | "Your system asks us every N seconds if anything's new" |
| Rate limiting / throttling | "Stops one user from overwhelming the service" |
| Free tier / freemium | "Use it free up to N; pay when you grow past that" |
| Implicit vs explicit subscription | "Auto-start free (Notion / Vercel) vs pick a plan first (B2B SaaS)" |
| Trial period | "Free for N days, then we ask for payment" |
| Cron / scheduled job | "Run something automatically on a timetable" |
| Async / queue / worker | "Kick off and we'll notify you when it's done" |
| Migration | "Move your existing data into the new shape" |
| Backfill | "Apply this to all the data that already exists" |
| Feature flag | "Turn a feature on for some users, off for others" |
| A/B test | "Show two versions; see which one users prefer" |
| API key / bearer token | "A password that lets the agent act on your behalf" |
| Refresh token | "How the agent stays signed in without re-asking you each time" |
| TLS / HTTPS / mTLS | "Encrypted in transit — what every legitimate website does" |
| At-rest encryption | "Encrypted on disk so a stolen hard drive is useless" |
| Schema | "The shape your data must fit" |
| Schema migration | "Changing the shape of data that's already in production" |
| Reconciliation | "Comparing two versions and resolving any differences" |
| Audit log | "A record of who did what, when — for compliance / debugging" |
| Distributed tracing | "Following one user's request through every system it touches" |
| Observability / metrics | "Knowing what your system is doing right now" |
| Circuit breaker | "If one service is broken, stop trying to call it for a while" |
| Retry with backoff | "If it fails, try again — but wait longer each time" |
| Health check / liveness / readiness | "Is the service alive? Is it ready to take traffic?" |
| Load balancer | "Spreads incoming requests across multiple servers" |
| CDN | "Copies of your static files near your users for speed" |
| Region / availability zone | "Where physically the data is stored — affects speed and law" |
| Database transaction | "Several changes that succeed together or fail together" |
| Eventual consistency | "It'll be correct in a moment, just not instantly everywhere" |
| Bounded context | "One self-contained slice of the business" |
| ADR | "A short note recording why we made a technical decision" |
| RFC / IETF standard | "A widely-agreed way of doing something on the internet" |
| UC (use case) | "A named scenario describing what someone does and what happens" |
| NFR | "A quality requirement — fast, secure, reliable, etc." |
| FR | "A thing the system must do" |
| TDD (Technical Design) | "The blueprint engineers follow to build the feature" |
| Primitive / domain entity | "A core thing in your business — like Order, Customer, Workout" |
| Decimal (vs cents-as-int) | "How we represent money exactly without rounding errors" |
| Tuple / struct / dataclass | "A named bundle of related values" |
| GraphQL vs REST | "Different ways APIs let you ask for data" |
| Container / Docker image | "Your code packaged with everything it needs to run" |
| Kubernetes | "The thing that runs and restarts your containers automatically" |
| Manifest (Sulis or k8s) | "A YAML file describing what should be running" |
| Bootstrap / genesis setup | "The one-time setup the platform operator does before anyone uses it" |

### When to use vs translate

- **Use the plain-English form when posing questions to a non-expert user.**
  The technical term may appear later in a journal, ADR, or artifact, but
  never in the question text.
- **Use the technical form** when documenting a decision, citing a standard,
  or talking with another agent. Internal vocabulary stays internal.
- **Match the user's register.** If the user introduces "OAuth" first,
  switch to the technical term — Plain English First's mirror rule still
  applies.

---

## AAF-04: Audience Score (MUST inform triage strictness)

The SRD analyst's Phase 1 Role Calibration produces a coaching level
(1 Novice / 2 Intermediate / 3 Experienced). Other agents perform similar
inference at session start. The AAF triage strictness scales with this
score:

| Audience score | Triage behaviour |
|---|---|
| **Novice (1)** | Strict triage. Step 1 takes *most* dev-experience and implementation choices silently. Step 2 takes any choice that needs technical vocabulary to explain. Step 3 questions use show-don't-tell + lexicon substitution always. |
| **Intermediate (2)** | Standard triage. Step 1 takes implementation-detail choices silently. Step 2 takes choices that need ≥ 2 technical concepts to explain. Step 3 questions use show-don't-tell when experiential, lexicon substitution always. |
| **Experienced (3)** | Relaxed triage. Step 1 only takes pure naming/numbering choices silently. Step 2 may surface technical trade-offs directly. Step 3 questions may use technical terminology if user has used them; lexicon substitution applied to terms the user has not used. |

**The Novice default is the marketplace's default.** Agents that cannot run
role calibration (e.g. context-cartographer in pure-discovery mode) treat
the audience as Novice unless the user signals otherwise.

---

## AAF-05: Session-Level Escalation (SHOULD)

When the user gives any of these signals, the agent escalates *Take silently*
to cover all dev-experience and implementation choices for the rest of the
session:

- *"Go with the boring default"*
- *"Most boring, standard and expected"*
- *"Trust your judgment"*
- *"Default to convention"*
- *"Defaults are fine"*
- *"Just take the standard"*
- *"Stop asking me about this stuff"*

Announce the escalation in the next response:

> *"Got it — I'll take the boring/standard default on every implementation
> choice from here. I'll surface questions only when there's a real
> founder decision (pricing model, positioning, brand, target user).
> Anything I decide will be in the journal so you can audit at the end."*

The user revokes the escalation with any of:
- *"Slow down"*
- *"Check with me on each"*
- *"Walk me through more"*
- Any explicit override of an announced default

---

## Composition with Other Standards

- **CP-01..CP-05 (Convention Preference)** — the "convention" the agent
  takes silently in AAF triage steps 1 and 2 is exactly what CP-01..CP-05
  identify. AAF runs *after* CP has identified the recommendation; AAF
  decides whether to *take it* or *ask about it*. The two rules compose:
  CP picks the answer, AAF decides whether the user needs to hear the
  question.
- **Plain English First** (`requirements-analyst.md:1512-1530`) — narrower
  scope (vocabulary substitution in narration). AAF supersedes it for
  question text but PEF still governs free-form narration, journal entries,
  and summaries.
- **Role Calibration** (`requirements-analyst.md:351-372`) — the Phase 1
  role inference feeds AAF-04's audience score. Same input, second
  consumer.
- **CL-03 Expertise-Appropriate Design** (`references/cognitive-load.md:92-112`)
  — informs lexicon entries for technical-detail exposure in artifacts.
- **Coaching Without Conflict** — AAF respects all seven tenets when
  framing questions. The "Show, don't tell" pattern in AAF-02 is itself
  Tenet 5 applied to UX trade-offs.
- **Question + Convention-Default Assumption (QCDA)** — runs *after* AAF.
  If AAF says "Ask", QCDA shapes the question structure (anchored on the
  convention). If AAF says "Take silently" or "Take and announce", QCDA
  never fires — no question to shape.
- **Two-Model OODA Reconciliation** — unchanged. AAF triages what reaches
  the user from each OODA cycle's Act step. Reconciliation leaves
  categorised as `external-system` or `primitive-component` go silently
  through step 1; leaves categorised as `gap` proceed to step 2 and step 3.

---

## Anti-Patterns

### "I'll ask just to be safe"

The agent surfaces a question with no business or UX consequence, framed
"so the user can confirm." This is the failure this standard is written
against. Confirmations on technical-only choices burn the user's attention
without adding signal. The user has no information to give. Take the
convention and move on.

### "But what if the user wanted Option β?"

If the user has stated preferences (in VISION, PRINCIPLES, STRATEGY) that
distinguish Option α from Option β, AAF triage step 3 applies the
preference. If no such preference exists, the user has no basis to pick β
over α; the choice is genuinely indifferent to them and the agent takes the
convention. The user can override at any time by reviewing the journal or
saying *"slow down"*.

### "The user asked me to be thorough"

Thoroughness is a quality of the spec produced, not a measure of how many
questions were posed. A thorough spec with one founder-facing question and
forty technical decisions in the journal is more useful than a spec with
forty-one founder-facing questions that the founder answered randomly.
Thoroughness lives in the artifact, not the conversation.

### "Surfacing the choice makes it transparent"

The journal makes choices transparent. Asking *and then* journaling makes
them transparent twice — but doubles the user's cognitive load. The journal
alone is sufficient transparency for technical-only choices.

---

## Version History

| Version | Date | Change | Author |
|---|---|---|---|
| 0.1.0 | 2026-05-15 | Initial draft. Calibration period 90 days. Promotion to MUST repo-wide requires evidence from three sessions where the standard changed the outcome (fewer technical questions posed; user reported the session felt easier; spec quality not regressed). | Standards team |
