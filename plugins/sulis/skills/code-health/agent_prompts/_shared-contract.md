# Per-tier agent contract (shared across all 7 tier prompts)

Every tier agent dispatched by code-health DEEP / AUDITED mode follows this
output contract. Templates per-tier inherit the contract by reference.

## What each agent receives in its prompt

- `{repo_root}` — absolute path to target repo
- `{scope}` — `auto | pr | codebase`
- `{project}` — project slug (defaults to repo basename)
- Tier-specific tool stack + interpretation lenses

## What each agent MUST return (markdown)

```markdown
## Per-tier verdict
{PASS | NEEDS_ATTENTION | FAILED | NOT_YET_CHECKED}

## Primitive coverage
| Primitive | Status |
|-----------|--------|
| {ID} | {PASS | ADVISORY | CONCERN | CRITICAL | HYPOTHESIS | NOT_ASSESSED | NOT_APPLICABLE} |

## Findings (capped per MUC-F4)
- {file:line} — {severity} — {message}
- ... (≤ 10 entries; if more exist, append "and N more")

## Hypotheses (if any)
- {primitive_id}: {statement}
  - Evidence: {list}
  - Confidence: {VALIDATED | SUPPORTED | EMERGING | UNVALIDATED}

## Founder-mode summary
{1-3 sentences for the CHECKUP aggregator}
```

## Interpretation lenses every agent MUST apply

These are the contextual judgments that subprocess-only fast mode can't do
but agent-mediated deep mode can:

1. **NOT_APPLICABLE for non-web repos.** If the repo has no HTTP routes /
   auth surfaces / persistent data stores, mark SEC-01 / SEC-02 / DAT-01
   as NOT_APPLICABLE rather than PASS. Check by: greppin'g for
   `flask|fastapi|express|django|rails|@router` / `requirements\.txt|package\.json`
   with web frameworks / `\.sql|migrations/`.

2. **Test-fixture recognition.** Findings inside `tests/`, `__tests__/`,
   `fixtures/`, `mocks/`, `*_test.py`, `test_*.py` that look like
   credentials (Gitleaks) or insecure patterns (Semgrep) are likely
   deliberate test fixtures. Mark severity = `informational` rather than
   `critical`; do NOT include in primary findings list unless metadata
   explicitly says they're real.

3. **Documentation-example recognition.** Findings inside markdown files
   (`.md`) with surrounding text describing the pattern (e.g., "the
   AWS key looks like AKIAIOSFODNN7EXAMPLE") are documentation examples.
   Mark as informational; do NOT include in primary findings list.

4. **Re-routing.** A Semgrep finding for `use-defused-xml` (XXE) is
   semantically INF-04 (verbose-error / unsafe-stdlib) — not raw SEC.
   A SHA1 finding for a non-cryptographic dedup signature with
   `# noqa: S324` annotation is informational, not high severity.

5. **MUC-F4 presentation cap.** ≤ 10 findings per category in the
   per-tier output. If more exist, append "and N more" + suggest the
   raw script for full list.

## What agents must NOT do

- Run any tool the tier's scanner script doesn't already invoke
- Modify any code or write files outside `agent_prompts/_output/` (if at all)
- Reach across tier boundaries — each agent's scope is its own tier only
- Apply contextual judgment that contradicts the scanner output (e.g.,
  marking a CRITICAL semgrep finding as PASS — only re-route severity,
  don't invert)
