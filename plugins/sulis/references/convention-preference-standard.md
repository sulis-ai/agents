# Convention Preference Standard

<!-- summary -->
When an agent makes a recommendation — protocol, format, library, pattern,
schema, or implementation approach — the default is the established
convention. Boring beats novel. Standardised beats bespoke. Battle-tested
beats clever. Novelty is the position requiring defence, not convention.
Agents pattern-match; recommending the canonical answer makes downstream
work load less context, run faster, and fail in well-understood ways.
<!-- /summary -->

> **Version:** 0.1.0
> **Status:** Active — Calibration Period (90 days from 2026-05-15)
> **Applies to:** All agents in the Sulis AI marketplace.

---

## Provenance

This standard codifies a practice observed during real production agent
sessions — when an agent recommends an established standard (RFC 9421 for
HTTP signing, JSON Schema 2020-12 for schemas, UUID v4 for IDs, Kubernetes
CRD shape for dispatch) the downstream design compresses dramatically;
when an agent improvises, the downstream design grows novel surface that
future agents (and humans) must reason about from scratch. Worse: novelty
hides in the gaps — the bespoke choice looks simple until the third
integration discovers an unspecified edge case.

This is practitioner knowledge, not peer-reviewed research.

---

## Boundary Definition

This standard contains **universal decision-making bias only**. Content
belongs here if and only if it passes the **ProjectX test**: replacing
every project name, file path, and technology-specific example with a
fictional "ProjectX" equivalent requires zero semantic changes to the
principle statement.

Specific technology choices are NOT in scope. The principle is the bias
toward conventions; specific conventions evolve over time.

---

## Severity Convention

| Severity | Meaning |
|----------|---------|
| **MUST** | Non-negotiable. Violations block delivery. |
| **SHOULD** | Default. Deviation requires explicit justification (an ADR or equivalent decision record). |

---

## CP-01: Default to the established convention (MUST)

When recommending a solution, the default answer is the most established
convention that meets the requirements. The priority order is precise:

0. **Internal prior art** — if the project already implements the
   capability in code, that is the strongest possible default. A working,
   shipping component outranks every external convention, because it is
   not just a preferred pattern, it is the system's existing reality.
   Specifying around it (or duplicating it) creates downstream collisions
   that are more expensive than any deviation from external standards.
   Discover internal prior art via:
   - `.context/{project}/INDEX.md` authoritative sources
   - `.architecture/{project}/probe-raw/1_2_capabilities.json` capability
     inventory (produced by `/sulis:analyse-codebase`)
   - Direct codebase grep for cross-cutting concern names (rate limiting,
     auth, caching, retries, secrets management, observability, feature
     flags, audit, idempotency — see the Prior-Art Check rule in the SRD
     analyst's Facilitation Rules)
1. **An IETF, W3C, ISO, or comparable standards-body document exists.**
   Recommend that.
2. **A dominant industry convention exists** (≥ 70% adoption in the
   relevant ecosystem). Recommend that.
3. **A widely-cited reference work covers the case** (e.g. the SRE book
   for SLOs, the Stripe API design notes for idempotency). Recommend per
   that reference.

**Two bespoke approaches must be defended, not one.** The first is
reinventing what an external standard already covers. The second — more
common, often invisible — is reinventing what the project already has.
Both are bespoke deviations. Both require explicit justification under
CP-03. An agent that respects external conventions but happily duplicates
internal implementations has only half-applied this principle.

**Operationalisation in the SRD analyst.** When the SRD analyst's Two-Model
OODA Reconciliation rule fires (see `plugins/sulis/agents/requirements-analyst.md`
→ Section 2), the four-priority order above IS the Outside-In escalation
ladder during the Observe step: internal prior art first (via the v1.9.1
Prior-Art Check), then standards-body documents, then dominant conventions,
then reference works. Bounded web research fires at priorities 1-3 only when
the slice names a regulated domain or a published standard — see the rule
for the WebFetch budget.

When the choice is between an industry standard and a bespoke approach,
**the recommendation defaults to the standard, even when the bespoke
approach appears simpler.** The cost of "simpler-now" is paid forever in
every downstream conversation that has to understand why the bespoke
choice was made.

---

## CP-02: Recommend boring (SHOULD)

When two established conventions both meet the requirements, recommend the
older, more boring, more widely-adopted one. Examples of the bias:

- HTTP/1.1 over HTTP/3 unless HTTP/3 features are required.
- PostgreSQL over a newer database unless requirements demand otherwise.
- TLS 1.3 over a custom encryption layer.
- Polling over webhooks unless real-time is required (webhooks add
  operational complexity).
- Library code over a custom implementation, unless library introduces
  unwanted dependencies.

Boring = battle-tested = well-understood failure modes = libraries in
every language = fewer surprises during security review or onboarding.

---

## CP-03: Novelty requires defence (SHOULD)

When recommending a non-conventional approach (custom format, bespoke
protocol, ad-hoc library choice), the recommendation MUST include:

1. **Why the convention is rejected.** Cite the specific requirement the
   convention cannot satisfy.
2. **What the novel approach buys.** Quantified where possible.
3. **What the novel approach costs.** Operational complexity, new failure
   modes, missing library support, expanded security review surface,
   onboarding friction.

If any of those three is missing, the recommendation defaults back to the
convention. Agents do NOT recommend novelty by inference, by silence, or
by "this is just one project."

---

## CP-04: Pattern-match to the dominant player (SHOULD)

When recommending a domain-specific pattern, identify "what does Stripe /
Kubernetes / GitHub / AWS / OpenTelemetry do here?" and default to that.
Reasons:

1. The dominant player has already paid for the obscure failure modes.
2. Engineers know the pattern from prior work — no new mental model.
3. Future agents (and humans) reading the TDD or ADR pattern-match
   immediately.

This applies most strongly when:
- Designing public APIs (look at Stripe / GitHub / AWS).
- Defining resource dispatch (look at Kubernetes CRDs).
- Choosing pagination, idempotency, rate-limiting (look at Stripe).
- Designing CLI affordances (look at Git, kubectl).
- Wiring observability (look at OpenTelemetry semantic conventions).

---

## CP-05: Surface the convention even when the user proposed otherwise (MUST)

If the user proposes a bespoke approach, the agent's first response names
the established convention that addresses the same need, with a one-line
summary. Phrasing template:

> "You mentioned {bespoke approach}. The established convention for this
> case is {convention} ({standard reference}). Want to use {convention},
> or do you have a reason to prefer {bespoke}?"

This is NOT an agent overriding the user; it is the agent ensuring the
user is making the trade-off knowingly. Many bespoke proposals are made
because the user doesn't know a standard exists. Surfacing it is the
agent's job.

When the user has stated a reason for the bespoke choice and the reason
holds up under CP-03 (justification), the agent proceeds with the bespoke
approach AND records the rejected convention in the relevant ADR or
decision record.

---

## Worked Examples

Common problems and their canonical answers. This table is not exhaustive;
the decision rule (when in doubt, "what is the published standard?") is
more important than the table itself.

| Problem | Recommended convention | Standard |
|---|---|---|
| HTTP message signing (auth) | RFC 9421 | IETF |
| JSON schemas | JSON Schema 2020-12 | JSON Schema Org |
| API versioning | URL path (`/v1/`) or Accept-header | dominant |
| Pagination (paged) | Offset + limit | dominant |
| Pagination (infinite scroll) | Opaque cursor | Stripe / GitHub |
| Idempotency | `Idempotency-Key` header | Stripe / IETF draft |
| Timestamps in APIs | RFC 3339 (ISO 8601 subset) | IETF |
| Time-zone names | IANA tzdata | IANA |
| UUIDs | v4 (random) or v7 (sortable) | RFC 4122 / draft-peabody |
| Errors in JSON APIs | RFC 7807 Problem Details | IETF |
| HTTP status codes | RFC 7231 + extensions | IETF |
| Auth (web) | OAuth 2.1 + OIDC | IETF |
| Auth (service-to-service) | mTLS or RFC 9421 signed requests | IETF |
| Cryptographic signatures | Ed25519 (modern) or RSA-PSS | NIST / RFC 8032 |
| Container images | OCI image spec | OCI |
| Container runtime | OCI runtime spec | OCI |
| Configuration files | YAML (K8s domain) or TOML (Python/Rust) | dominant per ecosystem |
| Cron syntax | Vixie cron or Quartz | dominant |
| Versioning | SemVer 2.0.0 | SemVer |
| Commit messages | Conventional Commits | dominant |
| Structured logs | OpenTelemetry semantic conventions | OTel |
| Distributed tracing | OpenTelemetry | OTel |
| Metrics | OpenTelemetry / Prometheus | OTel / dominant |
| Schema migration | Up + down migrations, sequential | dominant |
| Feature flags | Kill-switch + percentage rollout | dominant |
| Rate limiting (API) | Token-bucket with `Retry-After` | dominant + RFC 7231 |
| Health checks (HTTP) | Two endpoints: `/livez`, `/readyz` | Kubernetes convention |
| Resource dispatch (YAML) | Kubernetes CRD shape (apiVersion/kind/metadata/spec) | K8s convention |
| Deck structure (investor) | Sequoia Capital ten-slide layout | Sequoia |
| Design tokens | W3C Design Tokens Community Group draft | W3C |

When in doubt:
1. Search for "RFC + {topic}" — if a published RFC exists, that is almost
   certainly the recommendation.
2. Ask "what does {Stripe / Kubernetes / Stripe / GitHub / AWS / OpenTelemetry}
   do for this case?" If one of them has a public docs page on it, that is
   the convention.
3. If neither yields a hit, the problem is probably not where you think
   it is — re-examine whether a convention from an adjacent domain applies.

---

## Anti-Pattern: "But this is just one project"

A common defence of bespoke choices is "this is just one project and the
bespoke choice is simpler for our specific case." This defence is rejected
unless the agent (or the user) can name the specific requirement the
convention cannot satisfy.

Every project starts as "just one." The bespoke choice persists into
integrations, third-party SDKs, security reviews, hiring, onboarding docs,
support tickets, and the eventual second project that wants to use the
first one's API. By the time the cost surfaces, the bespoke choice is too
entrenched to undo.

---

## Anti-Pattern: "Novelty by silence"

When an agent presents A/B options and remains neutral on the choice, the
user may infer that both are equally valid. They are not. CP-01 says the
recommendation is the convention; CP-05 says the agent surfaces it
explicitly. Silence is not neutrality — it is a recommendation by default
for whichever option the user mentioned first.

If an agent offers options without recommending one, that is a violation
of this standard.

---

## How to Apply

Whenever an agent does any of the following, apply CP-01..CP-05:

- Presents A/B (or A/B/C/…) options to the user.
- Authors a TDD, ADR, SPEC, NFR, or design document.
- Recommends a library, framework, protocol, or schema.
- Designs a new format, dispatch shape, or API surface.
- Reviews a proposed approach (audit, hardening, code review).
- Facilitates a Q&A that leads to a binding decision.

The pattern of application is the same in every case: name the convention,
recommend it, defend any deviation explicitly.

---

## Relationship to Other Standards

- **`boring-code.md`** (SEA) governs *implementation style* — explicit,
  type-safe, free of magic. This standard governs *decision-making bias*
  — which protocol, format, pattern, or library to recommend. The two are
  complementary: boring choices implemented in boring code.
- **`engineering-principles.md`** governs how software is built (TDD,
  Check Before Building New, Boy Scout scoping). This standard governs
  *what* gets built. EP-03 ("Check before building new") in particular
  shares the same instinct as CP-01: extend an existing thing before
  inventing a new one.

---

## Version History

| Version | Date | Change | Author |
|---|---|---|---|
| 0.1.0 | 2026-05-15 | Initial draft. Calibration period: 90 days. Promotion to MUST requires evidence from three agent sessions where the principle changed the outcome. | Standards team |
