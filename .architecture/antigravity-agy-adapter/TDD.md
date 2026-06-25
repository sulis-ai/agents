---
id: ARCH-CH-M7WSQ4
title: Technical Design — Antigravity (`agy`) provider adapter
status: designed
tier: S
change: CH-M7WSQ4
sourced-from: .changes/create-antigravity-agy-adapter.SPEC.md + .RECON.md
platform-contract: platform-contracts/PC-001-google-antigravity-agy.md
---

# Technical Design — Antigravity (`agy`) provider adapter

Phase 1 of the Claude↔agy failover capability: make `agy` a **selectable execution
target**, seeded by the CH-GJ9KQR portable-context brief. Phase 2 (the automatic
failover trigger) is a separate, deferred change.

This is a tier-S, one-adapter change. The design is intentionally short: the
structural seam already exists and is **referenced, not restated**.

## Form — Structural Integrity

**The seam is already owned and tested.** The `ProviderAdapter` Protocol,
`SessionSpec`, and `Capabilities` live in
`plugins/sulis/scripts/_session_manager/adapter.py` (SESSION_MANAGER_CONTRACT §2.4).
The manager touches providers *only* through the `{provider: adapter}` dict (MEA-01,
dependency-inward). A new provider is **one new file** — that guarantee is the
contract.

This change is **EXPAND-Create**, not SUBSTITUTE-Wrap: the public face is the
`ProviderAdapter` Protocol *we* own; the agy CLI is *called by* `spawn_argv`
(§2.4 Stripe-rule discriminator). The agy CLI is not the architecture seam.

Components this change introduces:

| Component | What | Where |
|---|---|---|
| `InteractiveAgyPtyAdapter` | the new adapter; mirrors `InteractiveClaudePtyAdapter`'s **shape** | `_session_manager/adapters/agy_pty.py` (NEW) |
| provider registration | `"agy"` + alias `"antigravity"` → the adapter, additive | `session_manager_daemon.py::_build_server` (MODIFIED, +3 lines) |

What the adapter mirrors from the Claude pty adapter (reuse, per spec constraint):
the brief-as-trailing-positional read from the **same** CH-GJ9KQR sidecar
(`~/.sulis/changes/{brief_change_id}/pre_prompt.txt`, reusing
`_terminal_launcher._PRE_PROMPT_SIDECAR` — imported, not duplicated, EP-03); the
`spec.brief_change_id` (not ambient env) source with ULID validation before the path
join; unused `encode` (raises) / `decode` (returns `None`) / `turn_complete` (returns
`False`) on the pty path; `classify_failure → None` (defer to neutral classifier).

What the adapter does **NOT** mirror (ADR-002, grounded in PC-001): Remote Control
(agy has no such flag) and the deterministic pre-spawn `--session-id` pin (agy has no
such flag; its conversation id is agy-owned). Faking either would be speculative
over-build over a flag the platform does not accept.

`_BASE_ARGV = ("agy", "--prompt-interactive")`. `spawn_argv` then appends, in order:
`--add-dir <spec.cwd>`; the permission posture (`--sandbox` by default, ADR-003);
optional `--model <SULIS_AGY_MODEL>`; the resume flag (`--conversation <resume_ref>`
when `resume_ref` set); and the brief as the trailing positional when its sidecar
resolves. See PC-001 §4 for the exact token table.

`Capabilities(supports_resume=True, supports_tools=True, supports_partial_streaming=False)`
— identical honest flags to the Claude pty adapter (agy resumes and runs tools; a pty
is a raw terminal, not a chunk stream).

## Armor — Operational Hardening

The one genuine hardening decision is the **permission/sandbox posture** (ADR-003,
PC-001 §5): default `--sandbox`, **never** blanket `--dangerously-skip-permissions`;
a default-OFF / opt-in `SULIS_AGY_SKIP_PERMISSIONS` knob lets an operator loosen it
deliberately. Inverse polarity to the Claude adapter's default-ON Remote Control knob,
because a permission-loosening knob must be opt-in.

Inherited (unchanged) Armor primitives from the Claude pty path: the brief's bytes are
passed as **one execv token**, never shell-parsed (the manager spawns argv directly,
no `shell=True`, §2.12 — apostrophes/quotes/backticks safe, MUC-2 / #86);
`brief_change_id` is validated as a real change ULID before the filesystem path join
(defence-in-depth, on top of `SessionSpec.__post_init__`'s leading-`-`/control-char
guard); `resume_ref` inherits the same `__post_init__` shape guard (no leading `-`, no
control chars) → safe to place after `--conversation`.

Auth precondition (operational, not code): agy must be **pre-authenticated** (Google
Sign-In). Auth does not transfer at outage time; the failover is only viable if signed
in ahead of time. Documented in PC-001 §intro and the WP.

Observability/failover detection: `classify_failure → None` (defer to neutral) in
Phase 1 — provider-specific raw-failure detection is the Phase-2 failover seam,
exactly as the Claude pty adapter deferred its own detection.

## Proof — Verification Protocol

Posture: **unit conformance + argv-shape, driving the REAL agy binary for read-only
introspection where feasible, plus a no-regression assertion on the Claude path.**
This is backend plumbing, not a user-facing surface — authored journey Scenarios are
not required by the scenario gate (SPEC verification posture). A solid unit/integration
test posture is.

Mirrors `tests/unit/test_claude_pty_adapter.py`. Tests:

1. **Conformance** — `isinstance(adapter, ProviderAdapter)` (runtime-checkable): proves
   agy slots into the same seam.
2. **Capabilities** — `supports_resume is True`, `supports_tools is True`,
   `supports_partial_streaming is False`.
3. **`spawn_argv` shape** — `argv[0] == "agy"`, `"--prompt-interactive"` present,
   `--add-dir <cwd>` present; none of the headless `-p`/`--print`/`--prompt` flags.
4. **Permission posture (ADR-003)** — by default `--sandbox` present AND
   `--dangerously-skip-permissions` absent; with `SULIS_AGY_SKIP_PERMISSIONS=1`, the
   inverse (`--dangerously-skip-permissions` present, `--sandbox` absent).
5. **Brief-as-prompt seeding** — with `brief_change_id` set + sidecar present, the
   brief TEXT is the trailing positional, one token, not a `$(cat …)` literal (reuses
   the launcher sidecar constant — the EP-03 relocate-the-constant test).
6. **Brief from spec, not env** — the ADR-001-of-CH-GJ9KQR regression: ambient
   `SULIS_CHANGE_ID` = CH_A, `spec.brief_change_id` = CH_B → briefs CH_B; env ignored.
7. **Malformed/absent brief** — invalid ULID or missing sidecar → no positional,
   degrade-don't-crash.
8. **Resume mapping** — `resume_ref` set → `--conversation <ref>` present;
   `resume_ref` unset → no `--conversation` (and `--continue` documented as the
   most-recent fallback).
9. **Optional model** — `SULIS_AGY_MODEL` set → `--model <value>` present; unset →
   absent.
10. **Unused pty methods** — `encode` raises, `decode` returns `None`,
    `turn_complete` returns `False`.
11. **Real-binary introspection (integration, READ-ONLY)** — assert
    `agy --version` reports a contract-compatible version and `agy --help` still lists
    the flags the adapter emits (`--prompt-interactive`, `--add-dir`, `--sandbox`,
    `--conversation`, `--model`). This is the grounding-stays-true guard; it does NOT
    run agy with a prompt. Skips cleanly when `agy` is not on PATH (CI without the
    binary), exactly the WP-009 "real binary can't always run in CI" lesson.
12. **No-regression on the Claude path** — the daemon registry, after the additive
    edit, still resolves `"pty"` → `InteractiveClaudePtyAdapter`; and the existing
    `test_claude_pty_adapter.py` suite stays green untouched.

Real interactive `agy` (running an actual agent session) cannot run in CI — the
prompt-bearing round-trip is observed-done at verify time, not asserted in CI (the
WP-009 `--verbose`-required lesson). CI carries the unit + read-only-introspection
tests above.

## Verification Plan

<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->

Concretion of the SPEC's Verification Plan, per the canonical design-time
verification questions (read at design time; not inlined). Change `kind: backend`
→ per-kind adapter = pytest nodeids.

1. **User-observable behaviour** — Sulis can open an interactive agent session
   through the agy adapter, seeded by the portable-context brief, and resume it;
   the Claude path is unaffected. (Backend plumbing — observed via the adapter's
   argv contract + a real driven session at verify time, not an authored Scenario.)
2. **Environment(s)** — unit + read-only-introspection tests in CI
   (`plugins/sulis/scripts/tests/unit/`, `…/tests/integration/`); the prompt-bearing
   round-trip is verify-time only (real binary, real Google auth) — deferred from CI.
3. **Bootstrap-from-zero** — a fresh clone at the merge SHA runs the unit suite green
   with no agy binary present (introspection test skips cleanly); with agy installed +
   authenticated, the introspection test asserts contract compatibility.
4. **Per-integration strategy** — agy CLI: **real binary, read-only introspection**
   (`existing`, classification `existing`). No recording mock — the binary is installed
   and introspection is non-state-changing. Prompt-bearing session: **deferred-to-verify**
   (real Google auth required; not a CI fixture). The brief-sidecar seam is tested
   in-process with a fake `$HOME` (existing pattern from `test_claude_pty_adapter.py`).
5. **Per-kind adapter** — `kind: backend` → pytest nodeids (named in WP-001 DoD).
6. **Infrastructure needs (deferred)** — `agy-real-session-driver-google` — a
   verify-time driver that runs a real authenticated agy session and observes the
   brief-as-prompt round-trip. Deferred to the verify step / Phase 2 failover work;
   not shippable as a CI fixture (requires real Google auth).

WP verification shapes (for `/sulis:plan-work` frontmatter): the adapter WP ships
**Shape 1 — concrete** (real test artifacts the moment it lands:
`tests/unit/test_agy_pty_adapter.py`); the real-session round-trip is **Shape 2 —
deferred** (`agy-real-session-driver-google`).

## Sizing Report

- **Tier:** S (computed sFPC 4 / ASR 4; confirmed). See `SIZING.md`.
- **TDD length:** within the ≤120-line tier-S target (this section excluded). No
  circuit breaker triggered.
- **ADRs:** 3 produced (ADR-001 registration, ADR-002 don't-mirror-Claude-only,
  ADR-003 permission posture) = tier-S maximum; each affects more than one component
  or rejects a viable alternative. No ADR-rationale paragraph required.
- **Authoritative sources referenced (not restated):** `adapter.py` seam
  (SESSION_MANAGER_CONTRACT §2.4); `claude_pty.py` as the mirror template;
  `test_claude_pty_adapter.py` as the test posture. PC-001 carries the platform
  grounding rather than the TDD restating flag tables.
- **Sections that referenced rather than restated:** Form (seam + sidecar reuse),
  Armor (inherited primitives), Proof (test posture).
- **Canonical Identifiers recipe:** deferred-need ids use `{noun}-{noun}-{vendor-or-scope}`
  → `agy-real-session-driver-google`.
