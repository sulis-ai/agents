# TDD — Harden the agent execution boundary: L1 (safe-fetch proxy) + L2 (scoped file-tools)

> **Change:** CH-E22SX6 · harden · tier M
> **ARCH:** [ARCH.yaml](./ARCH.yaml) · **SIZING:** [SIZING.md](./SIZING.md)
> **SPEC:** `.changes/harden-agent-execution-boundary.SPEC.md` (the contract — owns the 14 scenarios)
> **Scope of this TDD:** **L1 + L2 only** — the universal, no-regret pair. **L3 is the next phase** (per-OS sandbox + deferred substrate); referenced as a follow-on, not designed here.

This TDD designs only what is buildable + testable in userland now. The crux
honesty — that L1's "only door" property is enforced by L3, not by L1 — is
resolved in [ADR-001](./adrs/ADR-001-l1-enforcement-vs-l3-dependency.md) and
threaded through every L1 section below.

---

## Form — Structural Integrity

### What already exists (reference, do not restate)

| Seam | Where | Role in this change |
|---|---|---|
| Provider-adapter seam + single spawn path | `_session_manager/adapter.py`, `manager._spawn_process` | The **only** place the agent process is launched (`subprocess.Popen`, inherits parent env). This is where L1's proxy env is injected and where the creds-exclusion (Rule of Two) is configured. EXTEND the spawn env; do not touch the adapter Protocol. |
| `within_change_scope` (#130) | `_worktree_safety.py` | The canonical-resolution + fail-closed scope invariant L2 generalises. **Reuse, don't fork** ([ADR-004](./adrs/ADR-004-file-tool-scope-resolver-and-allowlist-source.md)). |
| Secret-pattern catalogue | `_anonymiser.py` | The secret detector L1's outbound scrub reuses ([ADR-002](./adrs/ADR-002-secret-scrub-mechanism-and-what-is-a-secret.md)). |
| Path / change-id helpers | `_change_state.py` (`change_dir`, `change_worktree_dir`, `changes_base`) | Allowlist-root sources for L2. |

### New components

**L1 — Safe-fetch proxy (out-of-process gateway).**

```
_safe_fetch/                         (new package)
  proxy.py        — the gateway: accepts a fetch/search request on a loopback
                    endpoint, scrubs (ADR-002) → resolves DNS → fetches →
                    frames as untrusted data (ADR-003) → returns. Owns the
                    egress-audit record.
  tool.py         — the agent-facing safe-fetch / safe-search tool: the only
                    sanctioned outbound path the agent is told about. Speaks to
                    proxy.py over the loopback endpoint.
  framing.py      — frame_as_untrusted_data(content, source_url) → envelope
                    (ADR-003). Pure; sentinel-collision escape included.
_secret_patterns.py                  (new — extracted from _anonymiser, ADR-002)
                  — find_secrets(text) -> list[SecretHit]. Pure catalogue.
```

Ports & adapters (Form MEA-01): `tool.py` depends on a `FetchGateway` port;
`proxy.py` is the production adapter; an in-memory `FakeGateway` is the test
adapter. The HTTP-fetch leg inside `proxy.py` sits behind an `OutboundFetcher`
port so the scrub/frame logic is tested with no real network. **These are
EXPAND-Create adapters for ports the domain owns — not Wraps** (the public
face is our `FetchGateway`/`OutboundFetcher` interface; the HTTP client is
*called by* the adapter — Stripe-rule discriminator).

**L2 — Scoped file-tools.**

```
_file_scope.py                       (new — generalises within_change_scope, ADR-004)
                  — within_allowed_scope(target, change_id, *, operation,
                    roots=None) -> (ok, reason). Multi-root, canonical, fail-closed.
                    Shared core lifted from _worktree_safety (REORGANISE-Extract).
_file_tools.py                       (new)
                  — read_file / write_file / move_file / remove_file. Each
                    resolves scope first (move checks BOTH endpoints), then I/O.
```

`_worktree_safety.within_change_scope` becomes the single-root, exclude-cwd
special case expressed via `_file_scope`'s shared helper — its existing callers
(`git_worktree_remove`, `wpx-worktree`) are byte-unchanged.

### Dependency direction (inward)

`tool` → `FetchGateway` port ← `proxy` → `OutboundFetcher` port + `framing` +
`_secret_patterns`. `_file_tools` → `_file_scope` → (shared core) ←
`_worktree_safety`. No new module imports the manager, the daemon, or a vendor
CLI. `_secret_patterns` is pure (no I/O), consumed by both `_anonymiser` and
`proxy`.

---

## Armor — Operational Hardening

### L1

- **Outbound secret-scrub before DNS (ADR-002, SC-L1.3).** `proxy.py` runs
  `find_secrets` over method + URL + every header value + body *before* any DNS
  resolution or socket open. Any hit → **refuse fail-closed**, request never
  leaves the process.
- **Rule-of-Two creds exclusion (SPEC §L1(d)).** The proxy process is launched
  *without* the agent's credential-bearing env in its scope (configured at the
  spawn seam). A credential cannot be read into an outbound request because it
  is not present in the path. The scrub is defence-in-depth on top.
- **Content-as-untrusted-data framing (ADR-003, SC-L1.4).** Every returned
  payload carries `content_is_untrusted_data: true` + the deterministic
  envelope. Content is verbatim — **not** sanitised (SPEC non-goal).
- **No-raw-egress is L3's wall (ADR-001).** L1 ships the safe *door*; the
  *only-door* enforcement is the deferred `l3-os-egress-denial`. Tested now
  under a portable harness shim (ADR-005), honest in the docstring.
- **Timeout on the outbound fetch.** The `OutboundFetcher` adapter sets an
  explicit connect+read timeout (Armor: no unbounded external call). Open-web
  research (SC-L1.1) is preserved — the proxy fetches arbitrary, not-pre-listed
  public URLs.

### L2

- **Fail-closed default (SC-L2.2/2.3/2.4).** Unknown op, missing/invalid
  change-id, unresolvable path, or path outside every allowed root → refuse
  with a clear reason. Deny is the default.
- **Canonical paths everywhere (SPEC constraint).** Every allowlist root and
  every target is `Path.resolve()`-d on both sides of the containment check —
  the `/tmp`→`/private/tmp`, `..`-traversal, and symlink-escape footguns are
  closed by canonicalisation, inherited from `within_change_scope`.
- **Honest limit (SC-L2.5).** A subprocess bypasses the file-tools by design;
  L2 contains *mistakes*, not adversaries. The wall is L3.

---

## Proof — Verification Protocol

- **Contract test per port.** `FetchGateway` and `OutboundFetcher` each have a
  contract test the in-memory fake and the real adapter both satisfy (no
  mock-the-internals; MEA-09).
- **L2 mirrors `test_worktree_safety.py`.** The example-case set + the
  hypothesis safety-invariant property are extended to read/write/move/remove
  and the multi-root allowlist. The cross-worktree-deletion replay (SC-L2.3) is
  a direct port of #130's incident case.
- **Honest-confinement harness (ADR-005).** A portable no-raw-egress pytest
  fixture (monkeypatched sockets, loopback-only) confines the test process so
  SC-L1.2 and SC-L1.4 prove the proxy-correctness half under a *simulated* L3
  denial — with docstrings naming `l3-os-egress-denial` as the production owner.
- **Characterisation-before-refactor (REORGANISE, Non-Negotiable #3).** Before
  extracting `_secret_patterns` from `_anonymiser` and the shared core from
  `_worktree_safety`, a characterisation test pins current behaviour; the
  extract must keep it green.

### Scenario → test map (in-scope: SC-L1.1–1.4, SC-L2.1–2.5)

| Scenario | Proven by | Honest about |
|---|---|---|
| SC-L1.1 open-web research preserved | proxy fetches a fresh arbitrary public URL → non-empty content | real fetch (or recorded fixture in CI) |
| SC-L1.2 no raw egress | direct connect refused under shim; proxy connect succeeds | egress-denial simulated by harness; L3 owns prod (`l3-os-egress-denial`) |
| SC-L1.3 secret scrub on outbound | each catalogued secret shape injected → fetch refused before DNS; no secret in outbound capture | catalogue is format-based; Rule-of-Two exclusion is the real control |
| SC-L1.4 injection lands, can't act | injection page framed as data; zero egress to attacker host | composes with SC-L1.2's shim; framing ≠ sanitisation |
| SC-L2.1 in-scope ops succeed | read/write/move within all allowlist roots succeed | — |
| SC-L2.2 out-of-scope read refused | `~/.ssh` + sibling-worktree + `/tmp`→`/private/tmp` canonical case refused | — |
| SC-L2.3 out-of-scope write/move/remove refused | #130 sibling-worktree replay → refused fail-closed; sibling untouched | — |
| SC-L2.4 traversal/symlink escape refused | `..`-escape + symlink-out refused | mirrors #130 case set |
| SC-L2.5 honest boundary (NOT a wall) | `bash -c 'cat <out-of-scope>'` succeeds; test asserts the bypass + docstrings L3 ownership | the documented limit; L3 (`l3-os-egress-denial` / SC-L3.1/3.2) owns it |

---

## Verification Plan

<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->

This change's `kind:` is **backend** (Python modules + pytest). Per the
canonical kind→adapter table, the verification adapter is `backend` →
pytest nodeids. There is **no SRD Verification Plan** to ingest (this change
is spec-driven via `.changes/…SPEC.md`, which carries its own Verification
Plan as the 14 scenarios); this section concretises those scenarios to
TDD-level test artifacts.

1. **User-observable behaviour verified.** The agent can research the open
   web; a secret never leaves on an outbound request; an injected page can't
   make the agent act; honest file mistakes are refused; a subprocess bypass
   is a known, documented limit.
2. **Environment(s).** Local + CI (pytest). The no-egress confinement is a
   portable in-harness shim — runs identically on macOS/Linux/Windows CI. No
   `sandbox-exec` (that is L3, per-OS, deferred).
3. **Bootstrap-from-zero.** A fresh clone at the merge SHA runs
   `pytest plugins/sulis/scripts/tests/` and the L1+L2 suites pass with no
   external network *required* (SC-L1.1's live fetch uses a recorded fixture in
   CI; a marked live-network test is opt-in locally).
4. **Per-integration strategy.**
   - agent → proxy (`FetchGateway`): **concrete** — in-memory `FakeGateway`
     contract test + a loopback integration test. `tests/unit/test_safe_fetch_gateway_contract.py`.
   - proxy → open web (`OutboundFetcher`): **concrete** for scrub/frame
     (in-memory fetcher, no network); SC-L1.1 live leg **deferred** to an
     opt-in marked test + recorded fixture in CI → need `safe-fetch-live-url`.
   - file-tools → `_file_scope`: **concrete** — `tests/unit/test_file_scope.py`
     + `tests/unit/test_file_tools.py`.
5. **Per-kind adapter.** `backend` → pytest nodeids (named per WP below).
6. **Infrastructure needs surfaced (deferred).**
   - `l3-os-egress-denial` — the OS sandbox that makes the proxy the only door
     (production enforcement of SC-L1.2/1.4; replaces the test shim). **L3.**
   - `safe-fetch-live-url` — a recorded-fixture or opt-in live URL for SC-L1.1
     in CI without flaky real-network dependence.

Each WP below names its verification shape (concrete / deferred / trivial)
inline so `/sulis:plan-work` emits the right `verification:` frontmatter.

---

## Follow-on (NOT designed here)

**L3 — adversarial filesystem wall** (SPEC build-seq 2 & 3): per-OS native
sandbox (Seatbelt / bubblewrap / AppContainer) behind one common policy
(SC-L3.1–3.4), and the deferred remote-Linux/container substrate gated on
SC-L3.5 firing or a funded cloud target. L1's proxy is already the
allow-listed egress that the L3 sandbox will permit; L2's allowlist is the
same per-change scope the sandbox will be configured with. No L1/L2 rework is
implied by L3 — only the wall is added around them. Recorded need:
`l3-os-egress-denial`.

---

## Sizing Report

- **Tier:** M (computed sFPC 13, ASR 10 — agree; see SIZING.md). Confirmed at
  pre-write announcement.
- **TDD length:** within tier-M target (~250–400 lines). No circuit breaker
  triggered.
- **ADRs produced:** 5 (target 4–6). Each locks a decision affecting >1
  component or rejecting a viable alternative; none restate an existing ADR
  (no `.context/` index present for this repo area).
- **Referenced (not restated):** `_session_manager` spawn seam,
  `within_change_scope` (#130), `_anonymiser` catalogue, `_change_state`
  helpers, `test_worktree_safety.py` case set.
