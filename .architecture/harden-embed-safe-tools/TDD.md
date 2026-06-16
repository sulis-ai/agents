# Technical Design — Embed the safe tools into the governed action-surface

> **Change:** CH-522P6P · `harden` · tier **M** · base SHA `2da4d842`
> **Sourced from:** `.changes/harden-embed-safe-tools.SPEC.md` +
> `.changes/harden-embed-safe-tools.WORKING-SET.md` (decisions **D1–D8 LOCKED**)
> **Builds on:** `.architecture/harden-agent-execution-boundary/TDD.md` (the
> shipped L1 safe-fetch + L2 scoped file-tools this change embeds).
> **Sizing:** see `SIZING.md` (sFPC 13 → M; ASR 17 → low-L; **taken M**).

This change makes the shipped L1 + L2 **actually used and enforced** via the
Claude Code harness, not prose. The model is a **CLI-majority action-surface +
one governance hook + a small typed-MCP carve-out** — explicitly **NOT** a
CLI→MCP migration (D8). Every rule is labelled by its **enforcement-locus**
(i model / ii harness / iii OS) and **threat-scope** (accidental-closed-now /
adversarial-deferred), so nothing claims more safety than its locus delivers.

The harness contracts below are **verified against the live Claude Code docs**
(hooks, permissions, sandboxing — June 2026), not assumed.

---

## Form — Structural Integrity

The seams already exist; this change adds three thin adapters over them and
extends one resolver. Per the prior TDD's §Form, the domain owns its ports
(`FetchGateway`, `OutboundFetcher` in `_safe_fetch/ports.py`) and its scope
resolver (`_file_scope`); infrastructure adapters implement them. **No
hexagonal re-derivation here** — see the prior TDD §Form.

### New components

| Component | File(s) | Shape | Wraps |
|---|---|---|---|
| **safe-tools MCP server** | `scripts/_safe_tools_mcp.py` + launcher `scripts/sulis-safe-tools-mcp` | EXPAND-**Create** adapter (Stripe-rule: the public face is the MCP transport over *our* tool functions; the `mcp` SDK is *called by* the adapter, not re-exported) | `_safe_fetch.tool.safe_fetch/safe_search` + `_file_tools.{read,write,move,remove}_file` |
| **PreToolUse hook** | `scripts/_safe_tools_hook.py` + registration in `hooks/hooks.json` | EXPAND-**Create** (a new harness adapter) | the write-roots resolver (`_file_scope`) |
| **write-roots resolver extension** | `scripts/_file_scope.py` (extend) | REORGANISE-**Abstract** + EXPAND (add brain root + sandbox-emit) | `brain_base_dir` (#127) + the existing `AllowedRoots` |

Dependency direction stays inward: MCP server → tool functions → ports; hook →
resolver; resolver → `brain_base_dir` + `_change_state`. Nothing new imports
the daemon, the manager, or a vendor CLI. The MCP server reimplements **no**
fetch/scope logic (D6) — it marshals MCP args to the existing functions and
serialises their typed results.

**Tool shape (ADR-001):** the server exposes **three** tools —
`safe_fetch(url, format)`, `safe_search(query)`, and ONE parameterised
`scoped_file(op, path, content?, dst?)` (op ∈ `read|write|move|remove`). One
`scoped_file` (not four) avoids the name-collision / selection-bloat trap D8
names. Names: `mcp__sulis-safe-tools__{safe_fetch,safe_search,scoped_file}`.

**Scope is server-resolved, not agent-supplied:** `scoped_file` reads
`change_id` + `repo_root` from its launch environment and builds the roots via
the resolver — the agent cannot widen scope by passing a different `change_id`.

---

## Armor — Operational Hardening (the heart of this change)

### Enforcement-locus tiering (the honesty primitive)

| Locus | Mechanism | What it catches | Threat-scope |
|---|---|---|---|
| **i — model** | prose nudge ("prefer safe-fetch for clean output") in agent defs / skills | nothing; advisory only | quality, not safety |
| **ii — harness** | permission deny-rules + the PreToolUse hook | recognised direct tool calls (WebFetch, Write/Edit out-of-scope, raw curl/wget in a Bash call the hook can parse) | **accidental over-reach — CLOSED NOW** (GAP-α) |
| **iii — OS** | the shipped Seatbelt/bubblewrap sandbox (enabled + configured by the Phase-4 recipe) | ALL processes incl. spawned subprocesses (`python -c 'urllib…'`, obfuscated curl) | adversarial subprocess bypass — **consumer-enabled**; TLS-exfil (GAP-β) **deferred** |

**Rule:** every embedded rule names exactly one locus + its threat-scope. The
standard (Phase 5) asserts this; a test (SC-E6) asserts no rule claims a locus
it does not hold.

### Layer 1 — the safe path exists + is denyable (locus ii, identity)

- The MCP server (ADR-002) registers the three safe tools as distinct,
  enumerable identities. The L1 tools carry their existing armor unchanged:
  secret-scrub-before-DNS + untrusted-data framing + bounded timeouts live in
  the wrapped proxy (prior TDD §Armor). The MCP layer adds no network.
- Narrow the Sulis agent's `tools: "*"` to an explicit allowlist that includes
  `mcp__sulis-safe-tools__*` and the built-ins the agent legitimately needs,
  and **excludes** `WebFetch` (denied at the permission layer too).

### Layer 2 — the unsafe path is blocked (locus ii, governance)

- **The PreToolUse hook (ADR-003).** On `Write`/`Edit`/`Bash`:
  - Resolve `tool_input.file_path` (Write/Edit) canonically; deny if outside
    the write-roots, defer if inside.
  - Allow (defer) the `Bash(sulis-*:*)` / `Bash(wpx-*:*)` CLI family.
  - Flat-deny raw `Bash(curl …)` / `Bash(wget …)` and aliases.
  - **Decompose compound Bash** (`&&`, `||`, `;`, `|`, `|&`, `&`, newline,
    `$(…)`, backticks) and deny if ANY sub-command's argv[0] is a raw network
    tool — the hook reads the raw command string, so it must split it itself.
  - Best-effort Bash file-write scope check (`>`, `>>`, `tee`, `mv/rm/cp`
    dst); explicitly labelled best-effort because full subprocess file I/O is
    locus iii's job (SC-E7).
  - **Decision channel:** JSON `permissionDecision:"deny"` + reason on exit 0;
    exit 2 only on internal hook error (fail-closed). Deny — never `allow` —
    so a managed deny rule always wins (deny-first precedence).
- **Permission deny-rules (belt to the hook's braces).** Deny `WebFetch`
  (removes it from context); deny `Bash(curl:*)` / `Bash(wget:*)` (kept though
  documented-fragile — the hook is the real control); allow
  `mcp__sulis-safe-tools__*`. Bash arg-matching fragility is why the hook
  exists; neither is claimed sufficient alone.

### Layer 3 — the OS backstop (locus iii, consumer-enabled)

- Phase 4 (doc/config) provides the **sandbox-enable recipe**: `sandbox.enabled`,
  `sandbox.filesystem.allowWrite` = `sandbox_write_roots(...)` output (ADR-004),
  `denyRead` for creds (`~/.aws`, `~/.ssh`), `allowedDomains` = the proxy
  egress host only, and the consumer-managed `failIfUnavailable` +
  `allowUnsandboxedCommands:false` for strict mode. **Honesty:** the sandbox
  proxy does **not** inspect TLS (verified in docs) → a broad allowedDomains
  permits domain-fronting exfil. GAP-β (a TLS-aware safe-fetch-only egress
  proxy) is **deferred**, named, not built.

### Single source of truth (locus ii, no drift — ADR-004)

ONE resolver (`_file_scope`, extended) computes the canonical, narrowest-root
write-roots from `brain_base_dir` + change-state + git-common-dir + ro entries.
The file-tools scope check **and** the sandbox `allowWrite` emit both derive
from the same `AllowedRoots` value — structurally un-driftable. The brain root
is added only when the resolved brain is *outside* the worktree (a relocated
brain); the default in-worktree brain needs no extra root. Never all of
`~/.sulis/`.

---

## Proof — Verification Protocol

Existing L1/L2 contract + scenario tests stay green (`test_safe_fetch_*`,
`test_file_*`). New tests, all via `uv run pytest` (hypothesis available):

| Test artifact | Proves | Scenario |
|---|---|---|
| `tests/unit/test_safe_tools_mcp_contract.py` | the server starts; the three tools enumerate with the right names/schemas; `scoped_file` dispatches each op to the right wrapped function; no logic reimplemented (delegates to the real functions / a fake gateway) | **SC-E1** |
| `tests/unit/test_safe_tools_hook.py` | hook returns `deny` for out-of-scope Write/Edit (incl. `/tmp`→`/private/tmp` + a sibling change dir) and defers in-scope; allows the sulis-*/wpx-* family; flat-denies raw curl/wget; decomposes `a && curl …` and denies on the sub-command; fail-closed on bad input | **SC-E3, SC-E4** |
| `tests/unit/test_permission_rules.py` | the shipped permission config denies `WebFetch` + raw net tools and allows `mcp__sulis-safe-tools__*` (asserted against the config file) | **SC-E2** |
| `tests/unit/test_write_roots_resolver.py` | relocated-brain root allowed; sibling change `~/.sulis/changes/{OTHER}/` refused; never all of `~/.sulis/`; the file-tools root set == `sandbox_write_roots(...)` set (the single-source assertion) | **SC-E5** |
| `tests/unit/test_locus_honesty.py` | every rule in the standard + config carries an enforcement-locus + threat-scope label; no rule claims a locus it does not hold | **SC-E6** |
| `tests/integration/test_embed_scenarios.py` | the SC-E1..E6 happy/refuse paths end-to-end over the registered server + hook | SC-E1..E6 |

**Deferred / attested (labelled, NOT faked):**

| Scenario | Testable-now half | Deferred half (owner) |
|---|---|---|
| **SC-E7** subprocess bypass | the bypass **succeeds** without the sandbox — automated (`python -c 'urllib…'` reaches out; the hook never sees it) | the sandbox **blocks** it — sandbox-enabled run, human-attested / CI-where-available (locus iii) |
| **SC-E8** real session inside sandbox | — | a real `claude --agent sulis` trivial change end-to-end inside the enabled sandbox; driven/attested |
| **SC-E9** operator-proof | — | needs consumer-applied managed settings; Sulis ships defaults + recipe only; documented, not claimed |

The SC-E7 automated half **asserts the bypass succeeds** and names the OS
sandbox as the owner of the fix — no false green.

---

## Verification Plan
<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->

1. **User-observable behaviour.** After load: the three safe tools are
   callable; a `WebFetch` is blocked; an out-of-scope write is refused with a
   reason; raw `curl` in a Bash command is refused; the agent's legitimate
   work (in-scope writes, sulis-*/wpx-* CLIs, safe_fetch research) is
   unimpeded.
2. **Environments.** Local + CI via `uv run pytest` for SC-E1..E6 and the
   SC-E7 bypass-succeeds half. The sandbox-blocks half of SC-E7 + SC-E8/E9
   require a sandbox-enabled host (macOS Seatbelt / Linux bubblewrap) —
   attested, CI-where-available.
3. **Bootstrap-from-zero.** A fresh clone at the merge SHA + `uv sync --frozen`
   (which now installs `mcp>=1.0`) → the server launches, the hook runs, the
   tests pass. The dependency chain (`mcp`, existing `_safe_fetch`/`_file_tools`)
   resolves.
4. **Per-integration strategy.**
   - **agent → MCP server:** in-process contract test — start the server,
     enumerate tools, call `scoped_file`/`safe_fetch` against the real wrapped
     functions (file ops on a tmp tree; `safe_fetch` against a `FakeGateway`,
     reusing the prior L1 contract fake). `existing` seam: `FetchGateway`.
     Concrete — `tests/unit/test_safe_tools_mcp_contract.py`.
   - **harness PreToolUse → hook:** drive the hook with crafted stdin JSON
     fixtures (the documented `{tool_name, tool_input}` shape); assert the
     stdout decision / exit code. Concrete —
     `tests/unit/test_safe_tools_hook.py`.
   - **resolver → {file-tools, sandbox emit}:** unit-assert the two outputs
     derive from one `AllowedRoots`. Concrete —
     `tests/unit/test_write_roots_resolver.py`.
   - **sandbox enforcement:** deferred — need `sandbox-enabled-host` (canonical
     need id). Attested.
5. **Per-kind adapter.** `kind: backend` for WP-001/002/003 → pytest nodeids
   (above). `kind: docs` for WP-004/005 → no runtime surface; verified by
   doc-section assertions + the locus-honesty test (SC-E6) reading the standard.
6. **Infrastructure needs surfaced (deferred):**
   - `sandbox-enabled-host` — a Seatbelt/bubblewrap host to run the SC-E7
     sandbox-blocks half + SC-E8.
   - `mcp-sdk-dependency` — `mcp>=1.0` added to `pyproject.toml`/`uv.lock`
     (landed in WP-001, not a standing gap; named for traceability).

**Contradiction with SRD/SPEC:** none. The SPEC's verifiable-now /
deferred-to-L3 split maps 1:1 onto the table above; this TDD concretises it
without overriding it.

---

## Sizing Report

- **Tier:** M (computed sFPC 13 → M; ASR 17 → low-L; **taken M** per SIZING.md
  rationale — ASR inflated by honesty-labelling + deferred bookkeeping riding
  locked decisions, build surface is genuinely M).
- **TDD length:** within the M target (~150–250 lines). Form is short
  (references the prior TDD's seams); Armor + Proof carry the new design.
- **ADRs:** 4 produced (file-tool shape; MCP packaging; hook decision +
  decomposition; resolver single-source) — within the M maximum (≤6). Each
  affects >1 component or rejects a viable alternative AND is not covered by
  the prior change's ADRs.
- **Authoritative sources referenced (not restated):** the prior change's TDD
  §Form/§Armor (the L1/L2 seams); `_file_scope` ADR-004 (the multi-root
  allowlist extended here); the live Claude Code hooks/permissions/sandboxing
  docs (the harness contracts).
- **Circuit breakers:** none fired.
