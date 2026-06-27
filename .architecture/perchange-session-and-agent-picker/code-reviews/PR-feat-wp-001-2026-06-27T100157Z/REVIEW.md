# Code Review: WP-001 — Fix per-change session connection + add per-change agent picker

> **Timestamp:** 2026-06-27T100157Z (ISO 8601 UTC)
> **Author:** executor (autonomous)
> **Branch:** wp/fix-perchange-session-and-agent-picker/wp-001-session-and-agent-picker → change/fix-perchange-session-and-agent-picker
> **Files changed:** 16 (apps/cockpit)
>
> **Outcome:** Ready to merge

---

## At a glance

This change does three things in the cockpit and does them cleanly: it fixes the silent failure where the per-change live session never started, it shows a clear "can't reach the session" message when the terminal can't connect, and it adds the Claude/Antigravity picker to the per-change view. There are no build errors, the security-sensitive parts (the connection allow-list and the new save-the-choice paths) hold up under scrutiny, and every new behaviour ships with tests. Nothing needs fixing before merge.

## What to fix

No issues that need attention.

One minor point for awareness (not blocking): in the per-change view, the agent picker's "currently running" label reflects your just-made choice immediately (optimistic), then settles on the server's confirmed value a moment later. That's the intended, responsive behaviour and it rolls back if the server rejects the choice — no action needed.

## How this pull request is shaped

**Size — worth looking at.** ~770 lines across 16 files. Mid-sized, but it's a single coherent concern (the three fixes all serve "make the per-change session work + let me pick the agent"), and roughly half the lines are tests. No split needed.

**Safety — clean.** No database migrations, no schema changes, no new secrets, no infrastructure changes.

**Completeness — clean.** Two new test files plus additions to existing suites; every new behaviour is covered.

---

## Technical detail

> Below this point uses internal taxonomy (CR-NN, lens IDs) for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all changed files >50 lines read end-to-end by the dispatched lenses; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01: tsc server+client exit 0, eslint exit 0).
- **PR Hygiene:** size medium (731+/39-, 16 files); scope/safety/completeness clean (CR-09 / PH-01..04).
- **In the changes:** 1 finding (0 critical, 0 high, 0 medium, 1 low).
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (no failing-characterisation-test-grounded delta; the one low is a design preference).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 (3 low notes) | 0 | Origin normalization verified fail-closed; path-traversal doubly guarded |
| Security | 0 | 0 | Every origin-bypass candidate verified refused or genuinely-loopback |
| Quality | 0 (1 low note) | 0 | GET/PUT wire contracts agree; hooks-rules clean; tests thorough |

### Build Verification (CR-01)

No PR-introduced errors. `npm run typecheck` (tsc -p server && tsc -p client) exit 0 on HEAD; `eslint` on changed files exit 0. Logs in `tool-outputs/`.

### Findings in the Changes

**[LOW] ThreadView.tsx — picker `running` prop reflects the optimistic pending value (lens: quality + architecture).**
`running={runningProvider}` where `runningProvider = pendingProvider ?? providerQuery.data ?? "pty"`. After an optimistic switch the AgentPicker's `running` label (and its `next === running` no-op guard) compares against the pending value, not the server-confirmed one, until the post-PUT refetch lands. Harmless given the new-work semantics + the `.catch(rollback)` path. If strict "running == server-confirmed" is desired, pass `running={providerQuery.data ?? "pty"}` and keep `selected={runningProvider}` — the two distinct props exist for exactly this. Not blocking; intentional responsiveness trade-off.

### Findings in the Neighbours

None.

### Watch List (low-severity, design-intentional — no delta)

1. **Loopback subset is intentionally narrow.** `normaliseLoopbackOrigin` rewrites only `{localhost, 127.0.0.1, [::1]}`; the rest of `127.0.0.0/8` and bare `::1` are refused (fail-closed, stricter — not a widening). By design.
2. **Origin-refusal log carries changeId, not the rejected origin** (NFR-SEC-03). The `origin-refused` structured log line already fires (TerminalSidecar.ts:211); it deliberately omits the attacker-controlled origin string to avoid logging untrusted input. By design — adding the origin would be a regression.
3. **Dual LocalChatScopeStore instances** (route store + boot resolver store) agree by the on-disk file contract under the default chatRoot. Established pattern; both use the default root in boot. Pin/share only if either is ever parameterised.

### Security verification (CR-07 — nothing surfaced)

`normaliseLoopbackOrigin` cannot widen the allow-list beyond loopback. Verified against: `localhost.evil.com`, `127.0.0.1.evil.com`, `localhost@evil.com`, `localhost:5173@evil.com` (userinfo stripped → hostname `evil.com` → refused), `[::ffff:127.0.0.1]` (→ `[::ffff:7f00:1]` → refused), and IPv4-alternate forms (`0x7f.0.0.1`, `2130706433`, `0177.0.0.1`, `127.1` → canonicalised by WHATWG URL to genuine `127.0.0.1`, real loopback). Comparison on full `url.origin` (scheme+host+port). `Origin` is a browser-forbidden header — a cross-site page cannot forge a loopback value it didn't load from. Change-id path: decode-before-validate route guard `/^[A-Za-z0-9_-]+$/` + independent store backstop; no traversal reaches disk. Provider validated to closed union {pty,agy}. No secret/PII added to logs.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** tsc (server+client) + eslint on changed files. Base: clean. Head: 0 new errors. Coverage gap: none.
- [✓] **CR-02 Parallel dispatch used.** Three lenses dispatched concurrently as sub-agents. Diff 731 lines / 16 files — above carve-out threshold, dispatch required.
- [✓] **CR-03 Full-file reads.** Each lens read every changed file >50 lines end-to-end. Unread: none.
- [✓] **CR-04 Evidence discipline.** Findings cite file:line + quoted code.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 1 low.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; all files read; all lenses produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: 0 findings + 3 notes. Security: nothing surfaced (SEC access-control/injection/traversal/validation/SSRF/secrets checked). Quality: 0 findings + jsx-ident scan + dead-surface + contract-drift + test-coverage + logic + CR-10 perf all clean.
- [✓] **CR-09 PR Hygiene applied.** Scope low; Size medium (731+/39-, 16 files); Safety none (0 migrations/schemas/secrets/infra); Completeness none (2 new test files). No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** git diff change/fix-perchange-session-and-agent-picker -- apps/cockpit (working tree)
- **Neighbour expansion:** lenses read callers/callees (AgentPicker, ChatScopeStore port, client funnel, route mount); within 20-file cap.
- **Lenses dispatched in parallel:** yes (3 concurrent sub-agents).
