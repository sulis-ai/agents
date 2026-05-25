# sulis-security: Security & Viability Reviewer for Claude Code

A Claude Code plugin that runs evidence-based viability assessments against
any codebase. 25 primitives across 5 categories (Security, Data Protection,
Code Quality, Supply Chain, Infrastructure), executed through an OODA-spiral
methodology that adapts depth based on what it finds.

Part of the **Sulis agent fleet** — composes with `srd` (requirements
analyst), `sea` (engineering architect), and the broader marketplace.

---

## Why This Exists

Most security tooling is a flat checklist run: scan, list findings, exit.
A senior application-security engineer does something different. They form
a hypothesis, gather evidence, follow the threads that surprise them, and
end with a defensible verdict.

`sulis-security` is that engineer, encoded as an agent. It uses the OODA
spiral (Observe-Orient-Decide-Act) to adapt cycle-by-cycle — running
broad-spectrum tools first, then targeted follow-ups, then cross-primitive
chaining, then deployed-surface checks, then hypothesis formation for the
primitives that don't fully automate.

The output is an evidence-backed report — every finding cites a file, a
line, a tool output, or a git log entry. Primitives that can't be tooled
become **hypotheses** with explicit confidence levels, ready for a human to
confirm or reject.

---

## Quick Start

```bash
# Install
/plugin marketplace add sulis-ai/agents
/plugin install sulis-security@sulis-ai-agents

# Start a review session
claude --agent sulis-security:security-reviewer --dangerously-skip-permissions

# Or run the assessment directly
/sulis-security:codebase-assess my-project owner/repo
/sulis-security:codebase-assess my-project owner/repo https://staging.example.com
/sulis-security:codebase-assess my-project https://github.com/owner/repo.git
```

### Commands

| Command | What It Does |
|---|---|
| `claude --agent sulis-security:security-reviewer` | Conversational security reviewer — drives assessments, answers ad-hoc questions |
| `/sulis-security:codebase-assess <project> <repo> [url]` | Run the 25-primitive viability assessment, produce `viability-report-{YYYY-MM-DDTHHMMSSZ}.md` (ISO 8601 UTC timestamp, prevents same-day collisions) |

---

## How It Works

### The 25 Primitives (5 categories)

| Category | Prefix | Count | Coverage |
|---|---|---|---|
| **Security** | SEC | 7 | Access control, auth, injection, validation, XSS, SSRF, sensitive data exposure |
| **Data Protection** | DAT | 5 | Encryption at rest/transit, PII/PHI, secrets, audit logging |
| **Code Quality** | CQ | 5 | Complexity, test coverage, duplication, technical debt, review practices |
| **Supply Chain** | SC | 4 | CVEs, freshness, SBOM/licence, transitive depth |
| **Infrastructure** | INF | 4 | Container security, deploy-config secrets, HTTP headers, error handling |

Full catalogue: [`skills/codebase-assess/references/primitives.md`](skills/codebase-assess/references/primitives.md)

### The OODA Spiral

Each cycle deepens understanding. Typical run: 3-5 cycles code-only, 5-7
with a deployed URL.

| Cycle | Purpose |
|---|---|
| **1. Reconnaissance** | Detect stack, map applicable primitives, plan tool order |
| **2. Triage & Depth** | Prioritise critical/high findings, run targeted follow-ups |
| **3. Cross-Primitive Chaining** | Find findings that combine into attack paths |
| **4. Deployed Surface** | Non-invasive header/TLS/exposure checks (if URL provided) |
| **5. Hypothesis Formation** | Evidence-backed statements for primitives that don't tool |

Framework detail: [`references/viability-framework.md`](references/viability-framework.md)

### Evidence Discipline

Every finding cites specific evidence: file:line, tool output snippet,
git range, or response header. Findings without evidence are `UNSUPPORTED`
and excluded from scoring. Hypotheses must state evidence base and
confidence level (high/medium/low).

### Tools

Preferred via Docker (no local install needed):

| Tool | Covers |
|---|---|
| **Gitleaks** | SEC-07 (secrets in code/history), DAT-04, INF-02 |
| **Trivy** | SC-01..SC-04 (CVEs, SBOM, freshness), INF-01 (containers) |
| **Semgrep** | SEC-01..SEC-06 (SAST patterns), INF-04 (error handling) |
| **lizard** | CQ-01 (cyclomatic complexity) |
| **hadolint** | INF-01 (Dockerfile lint) |
| **testssl.sh** | DAT-02 (TLS analysis on deployed URL) |
| **curl** | INF-03 (HTTP headers), exposure probes |

Tool unavailable → primitive gets `NOT ASSESSED` (not a failure — a coverage
gap, documented in the report's Methodology section). Tool commands:
[`skills/codebase-assess/references/tool-commands.md`](skills/codebase-assess/references/tool-commands.md)

---

## Output Layout

Reports land under `.security/{project}/` in the user's working directory,
parallel to SRD's `.specifications/` and SEA's `.architecture/`:

```
.security/{project}/
├── SEC.yaml                              # metadata, scores, related SPEC/ARCH IDs
├── viability-report-{YYYY-MM-DDTHHMMSSZ}.md  # ISO 8601 UTC timestamp; main report
├── tool-outputs/                         # raw outputs
│   ├── gitleaks.sarif
│   ├── trivy.json
│   └── semgrep.sarif
└── hypotheses.md                         # hypotheses for manual primitives
```

### Report sections

- **Executive Summary** — overall score, category scores, narrative
- **Critical Findings** — only `CRITICAL` items, each with evidence and recommendation
- **Attack Chains** — cross-primitive combinations into exploitable paths
- **Specification Drift** — findings that contradict NFRs (if SRD is present)
- **Category Detail** — full primitive table per category
- **Hypotheses** — manual primitives with confidence + verification question
- **Recommendations** — immediate / near-term / ongoing
- **Methodology** — cycles run, tools used, tools unavailable, paths excluded

---

## Where sulis-security Fits in the Fleet

```
srd:requirements-analyst   →   sulis-security   →   sea:engineering-architect
(What & Why)                   (Audit & Findings)    (Hardening & Decomposition)
   SRD.md                        viability-report.md   TDD.md
   NFR.md                        critical findings  →  hardening-deltas/HD-*.md
   PRIMITIVE_TREE                attack chains          work-packages/WP-*.md
```

- **With SRD** — when `.specifications/{project}/NFR.md` exists, the agent
  reads it and flags **specification drift** (findings that contradict
  documented NFRs). Bridges what was promised with what was built.
- **With SEA** — Critical and Concern findings can be converted to SEA
  Hardening Deltas via `/sulis:harden-codebase`. The report cross-references existing
  deltas to avoid double-counting.
- **Standalone** — the assessment runs without either plugin, on any
  codebase that has no prior specification or architecture.

---

## GitHub App Authentication (Optional)

For org-controlled, revocable access to private repos, configure a generic
GitHub App and set three environment variables:

```bash
export GITHUB_APP_ID="123456"
export GITHUB_APP_PRIVATE_KEY="/path/to/private-key.pem"
export GITHUB_APP_INSTALLATION_ID="78901234"
```

Permissions needed (minimal):
- `contents: read`
- `metadata: read`

If env vars aren't set, the skill falls back to direct clone with your
existing git credentials. This is the default mode.

---

## Who It's For

**Teams shipping to production.** Pre-launch viability check before
go-live. Critical findings flagged with file paths and recommended fixes.

**Compliance preparation.** SOC2, ISO 27001, HIPAA assessments need
evidence. The report's category scores, evidence trail, and hypotheses
give an auditor a defensible starting point.

**Code reviewers.** Senior engineer reviewing a teammate's PR or a
third-party codebase you're about to integrate. Get evidence quickly.

**Consultants doing engagement-level assessments.** The plugin handles
the heavy lifting; the consultant adds context, validates hypotheses,
and produces the client-facing narrative.

---

## Installation

### From marketplace

```bash
/plugin marketplace add sulis-ai/agents
/plugin install sulis-security@sulis-ai-agents
```

### From local clone

```bash
claude --plugin-dir ./plugins/sulis-security
```

### Recommended companions

```bash
/plugin install srd@sulis-ai-agents             # requirements-traceable findings
/plugin install sea@sulis-ai-agents             # findings → hardening deltas
```

---

## Boundaries

**What this plugin does not do:**

- **Active vulnerability scanning** — no OWASP ZAP, no Nuclei, no SQLi
  probes. Only non-invasive code review, static analysis, and passive
  deployed-surface checks (headers, TLS, common file exposure).
- **Penetration testing** — by definition out of scope. Active testing
  requires explicit per-engagement authorisation.
- **Production telemetry analysis** — no log forwarding, no runtime
  instrumentation. The assessment is point-in-time against source and
  deployed surface only.
- **Compliance certification** — the report is evidence for an auditor or
  consultant, not a certification itself.

---

## Gotchas

- Tokens are short-lived (10 min JWT, 1 hr installation token) and never
  written to the report. Don't change that.
- A primitive marked `NOT ASSESSED` is a coverage gap, not a failure.
  Document why in Methodology so the reader can judge trust.
- Lead the report with Critical Findings, not the score. A 75/100 driven
  by one critical is worse than a 75/100 evenly distributed.
- The PII pattern scan (DAT-03) has high false-positive rates from test
  fixtures. Verify findings before flagging as critical.
- Don't double-count with SEA Hardening Deltas — the skill cross-references
  `.architecture/{project}/hardening-deltas/` when present.

---

## License

MIT
