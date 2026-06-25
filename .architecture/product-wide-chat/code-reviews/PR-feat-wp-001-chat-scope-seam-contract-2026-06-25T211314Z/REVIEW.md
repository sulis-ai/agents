# Code Review: WP-001 — Per-product chat-scope seam contract

> **Timestamp:** 2026-06-25T211314Z (ISO 8601 UTC)
> **Author:** executor (autonomous)
> **Branch:** wp/create-product-wide-chat/wp-001-chat-scope-seam-contract → change/create-product-wide-chat
> **Files changed:** 7
>
> **Outcome:** Ready to merge

---

## At a glance

This change defines the shared "wire shape" for the new per-product chat — the
agreed set of fields the chat's front end and back end will both build against,
plus a small safety check that rejects bad inputs. It ships no behaviour yet (by
design — this is the contract both sides build against in parallel). The build is
clean, every new piece is covered by a test, and the input-safety check is tested
against six malicious-input cases. Nothing needs attention before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 416 lines across 7 files, single concern (one contract seam).

**Scope — clean.** One purpose: the chat-scope contract. The small touch to the
product switcher is the same change — moving the "all products" marker to its
single home so the chat and the board share one word for it.

**Safety — clean.** No database changes, no infrastructure changes, no secrets.

**Completeness — clean.** Four new code files, all covered by the new contract
test. No source shipped without a test.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all
files >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..04 all low)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | — (dependency direction holds; CF-07 conformance present) |
| Security | 0 | 0 | — (parseChatScope rejects traversal, 6 cases) |
| Quality | 0 | 0 | — (full test coverage; SSE reuses existing union) |

### Build Verification (CR-01)

`npm run typecheck` (`tsc --noEmit -p server && -p client`): 0 errors.
`eslint` on the 7 changed files: 0 errors. Raw logs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):  commit_type_spread {feat}; module_fan_out 2 (shared, client) → low
Size  (PH-02):  +416 / -11; files 7; generated 0.0                          → low
Safety(PH-03):  migrations 0; schema/idl 0; infra 0; secret hits 0          → low
Completeness(PH-04): new_source_without_test 0; api_change_without_schema false → low
```

### Findings in the Changes

None.

### Lens output

**Architecture lens: nothing surfaced.** Checks run: dependency direction
(shared/ imports nothing from client/ or server/ — the sentinels live in
`shared/chatScope.ts` and `client/src/lib/productCounts.ts` re-exports them, so
the low layer stays dependency-free); no new singletons; no circular imports;
CF-07 conformance — the contract test (`chatScope.contract.test.ts`) exercises
two consumers (`chatScope.client.stub.ts` producer-side, `chatScope.route.stub.ts`
consumer-side) of the same shared shapes, so producer/consumer agree by
construction (HD-02 `contract-test` gap closed, not open).

**Security lens: nothing surfaced.** Primitives checked: SEC-04 (input
validation), SEC-05 (path traversal), SEC-07 (secrets exposure). `parseChatScope`
is a wire-level traversal guard: it rejects `..`, `/`, `\`, embedded newlines,
whitespace, empty id, and non-`product:` prefixes — 6 explicit reject cases in
the test plus 3 accept cases. No secret-shaped strings in the diff. No injection
vector (type-only additions + a pure string validator).

**Quality lens:**
1. Build Verification follow-up: none (CR-01 clean).
2. JSX identifier scan: `ProductSwitcher.tsx` — the only introduced identifier is
   `ALL_SCOPE`, imported on the same diff hunk; in scope. (`jsx-ident-scan`: clean.)
3. Dead-surface: none. The one initially-unexercised export
   (`stubChatProviderRequest`) was given a contract-test assertion in this WP, so
   no dead export ships.
4. Contract-drift: none. The `POST /message` SSE reuses the existing
   `ChatStreamEvent` union rather than declaring a parallel one (no second source
   of the stream vocabulary); `messages` reuses `TranscriptMessage`; chat→card
   reuses `StartFromIntentRequest` verbatim (ADR-004).
5. Test-coverage: 12 contract assertions cover all four route shapes, the closed
   provider union, the validator (9 cases), and the CF-07 round-trip. No
   source-only files.
6. Style: comments are proportionate and cite the governing ADRs; no TODO/FIXME.
7. CR-10 performance: no anti-pattern matches (the diff contains no loops over IO;
   the validator is O(1) regex + substring checks).

### Findings in the Neighbours

None. The neighbour ring (`ProductControl`, the board scope consumers of
`productCounts`) was checked via the consolidation's downstream tests — 720/720
client + 906/906 server green, confirming no neighbour breakage.

### Watch List

None.

### Cross-Reference

- No prior `.security/product-wide-chat/` viability report to cite.
- No existing hardening deltas to cite.
- No neighbour pattern suggesting a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `npm run typecheck`; `eslint` on 7 changed files. Head: 0 errors. Coverage gap: none.
- [✓] **CR-02 Dispatch.** Single-reader pass justified: 416 lines but a homogeneous contract-first diff (type defs + 1 test + 2 stubs + a 9-line refactor) authored and read end-to-end this session; perf/JSX/secrets/import scans run mechanically over the full diff.
- [✓] **CR-03 Full-file reads.** All 7 changed files read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** Findings: none; the lens notes cite file paths + the governing ADR/CF rule.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical / 0 high / 0 medium / 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired.
- [✓] **CR-07 Lens completion.** Architecture: 0 findings + dependency/CF-07 check. Security: 0 findings + traversal-guard verification. Quality: 0 findings + jsx-ident-scan + dead-surface + contract-drift + test-coverage + CR-10 perf scan.
- [✓] **CR-09 PR Hygiene applied.** PH-01 low / PH-02 low / PH-03 low / PH-04 low. PH-03 high: not present → no auto-downgrade.

#### Run details

- **Diff source:** `git diff --cached` (staged WP branch vs change/create-product-wide-chat).
- **Neighbour expansion:** git grep + full downstream test run (sentinel consumers).
- **Neighbour cap:** not reached (well under 20).
- **Scanners run:** tsc, eslint, regex-based secret/perf/import scans.
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not invoked (no secret-shaped strings in a type-only + pure-validator diff; recorded as the coverage scope).
