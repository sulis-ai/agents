---
id: WP-001
title: Interactive agy pty adapter + additive provider registration
kind: backend
primitive: Create
group: expand
status: pending
dependsOn: []
blocks: []
change: CH-M7WSQ4
source-tdd: TDD.md §Form, §Armor, §Proof
platform-contract: platform-contracts/PC-001-google-antigravity-agy.md
adrs: [ADR-001, ADR-002, ADR-003]
estimated-token-cost: "input: ~25k / output: ~10k"
verification:
  adapter: backend
  artifact: plugins/sulis/scripts/tests/unit/test_agy_pty_adapter.py
  deferred-to-follow-on: agy-real-session-driver-google
---

# WP-001 — Interactive agy pty adapter + additive provider registration

## Context

TDD §Form/§Armor/§Proof. Adds `InteractiveAgyPtyAdapter` (mirroring the **shape** of
`InteractiveClaudePtyAdapter`) and registers it additively under provider keys
`"agy"` + `"antigravity"` in the daemon composition root. EXPAND-Create against the
owned `ProviderAdapter` Protocol — **not** a wrap of the agy CLI (the CLI is *called
by* `spawn_argv`; the Protocol is the public face, §2.4). Phase 1 only: makes agy a
selectable target; the failover trigger is Phase 2.

Grounded in PC-001 (real `agy` v1.0.11 behaviour). The adapter and registration ship
together — the registration is inert without the adapter, and the tests are this WP's
own Red/Green gates, so this is one atomic WP, not three.

## Contract

New file `plugins/sulis/scripts/_session_manager/adapters/agy_pty.py`:

```python
class InteractiveAgyPtyAdapter:
    capabilities = Capabilities(
        supports_resume=True, supports_tools=True, supports_partial_streaming=False
    )
    def spawn_argv(self, spec: SessionSpec) -> list[str]: ...   # see token order below
    def encode(self, command: str) -> bytes: ...               # raises NotImplementedError
    def decode(self, line: bytes) -> Event | None: ...         # returns None
    def turn_complete(self, event: Event) -> bool: ...          # returns False
    def classify_failure(self, error: EventError) -> RecoveryClass | None: ...  # returns None
    def reauth(self) -> ReauthTicket: ...                       # raises (Phase-2 seam)
```

`_BASE_ARGV = ("agy", "--prompt-interactive")`. `spawn_argv` appends, in order
(PC-001 §4):

1. `--add-dir <spec.cwd>`
2. permission posture (ADR-003): default `["--sandbox"]`; if `SULIS_AGY_SKIP_PERMISSIONS`
   is truthy → `["--dangerously-skip-permissions"]` instead (no `--sandbox`).
3. optional `["--model", <SULIS_AGY_MODEL>]` when the env var is set.
4. resume (ADR-002): `spec.resume_ref` set → `["--conversation", spec.resume_ref]`;
   else nothing (no pre-spawn pin — agy has no `--session-id`).
5. brief trailing positional: read the CH-GJ9KQR sidecar
   (`~/.sulis/changes/{spec.brief_change_id}/{_terminal_launcher._PRE_PROMPT_SIDECAR}`,
   import the constant — EP-03) iff `spec.brief_change_id` is a valid change ULID
   (`validate_change_ulid`, defence-in-depth before path join) AND the file exists;
   append its text as ONE argv element. Else no positional.

Registration — `session_manager_daemon.py::_build_server`, additive (ADR-001):

```python
agy_adapter = InteractiveAgyPtyAdapter()
manager = SessionManager(
    {
        "pty": _build_pty_adapter(),     # UNCHANGED
        "agy": agy_adapter,              # NEW
        "antigravity": agy_adapter,      # NEW alias
    },
    start_maintenance=True,
)
```

Reuse, don't reinvent: import `Capabilities`, `SessionSpec` from
`_session_manager.adapter`; `Event`, `EventError`; `RecoveryClass`; `ReauthTicket`;
`validate_change_ulid` from `_wpxlib`; `_terminal_launcher._PRE_PROMPT_SIDECAR`. Do
NOT import `_change_session` (no session-id pin) and do NOT add Remote Control (ADR-002).

## Definition of Done

### Red (failing tests first)

New `plugins/sulis/scripts/tests/unit/test_agy_pty_adapter.py` (mirror
`test_claude_pty_adapter.py`); all fail before the adapter exists:

- `test_conforms_to_provider_adapter_protocol` — `isinstance(adapter, ProviderAdapter)`.
- `test_capabilities_declared` — resume+tools True, partial_streaming False.
- `test_spawn_argv_is_interactive` — `argv[0]=="agy"`, `--prompt-interactive` present,
  `--add-dir` present with cwd as its value; no `-p`/`--print`/`--prompt`.
- `test_default_posture_is_sandbox` — default argv has `--sandbox`, NOT
  `--dangerously-skip-permissions`.
- `test_skip_permissions_optin_knob` — `SULIS_AGY_SKIP_PERMISSIONS=1` →
  `--dangerously-skip-permissions` present, `--sandbox` absent.
- `test_appends_brief_when_present` — brief sidecar present → brief text is the
  trailing positional, one token, not `$(cat …)`.
- `test_briefs_from_spec_not_env` — ambient `SULIS_CHANGE_ID`=CH_A, spec=CH_B → CH_B wins.
- `test_omits_positional_when_brief_absent_or_malformed` — missing sidecar / non-ULID
  id → no positional, no crash.
- `test_resume_maps_to_conversation` — `resume_ref` set → `["--conversation", ref]`;
  unset → no `--conversation`.
- `test_optional_model` — `SULIS_AGY_MODEL` set → `--model <value>`; unset → absent.
- `test_encode_raises` / `test_decode_returns_none` / `test_turn_complete_returns_false`.
- `test_reuses_launcher_sidecar_constant` — relocate `_PRE_PROMPT_SIDECAR`, brief read
  from the relocated path (EP-03).

Integration `plugins/sulis/scripts/tests/integration/test_agy_binary_introspection.py`
(READ-ONLY; skip when `shutil.which("agy")` is None):

- `test_agy_version_contract_compatible` — `agy --version` parses; assert major/minor
  is `1.0` (the contracted surface; patch bumps OK — v1.0.12 confirmed identical),
  warn/xfail on a different major/minor so PC-001 §10 re-grounding is triggered.
- `test_agy_help_lists_emitted_flags` — `agy --help` lists `--prompt-interactive`,
  `--add-dir`, `--sandbox`, `--conversation`, `--model`. (Does NOT run agy with a prompt.)

### Green (make them pass — boring code)

- Implement `InteractiveAgyPtyAdapter` exactly to the Contract above.
- Add the additive registration to `_build_server`; import `InteractiveAgyPtyAdapter`
  at the daemon top alongside `InteractiveClaudePtyAdapter`.
- Export `InteractiveAgyPtyAdapter` from `_session_manager/adapters/__init__.py` and
  `_session_manager/__init__.py` (mirroring how `ClaudeAdapter` is exported) so it is
  importable on the same path as its sibling.

### Blue (refactor / no-regression)

- `test_claude_path_registration_intact` — after the edit, the daemon registry still
  maps `"pty"` → `InteractiveClaudePtyAdapter` (assert on `_build_server`'s manager or a
  small helper that returns the adapter dict). Add a `_build_agy_adapter()` helper
  mirroring `_build_pty_adapter()` only if it removes duplication; otherwise inline the
  one instance (don't manufacture a factory — tier S, boring beats clever).
- Run the FULL existing session-manager + adapter suite; `test_claude_pty_adapter.py`
  and all manager/socket tests stay GREEN, byte-unchanged (Claude path unaffected,
  acceptance #4).
- Confirm no shared primitive was duplicated: the sidecar-read + ULID-validation logic
  is structurally parallel to the Claude adapter's. If the two `_read_pre_prompt` bodies
  are byte-identical, extract a shared helper (EP-02 REFACTOR step) into a small module
  both adapters import; if they diverge (they will if agy's path differs), leave them
  and note why. Decide in Blue, not by guessing now.

## Verification

Concrete (Shape 1): `tests/unit/test_agy_pty_adapter.py` +
`tests/integration/test_agy_binary_introspection.py` ship with the WP.
Deferred (Shape 2): `agy-real-session-driver-google` — the real authenticated
prompt-bearing round-trip, observed at verify time / Phase 2 (needs real Google auth;
not a CI fixture). The brief-as-prompt seeding is observed via the argv contract in CI
and driven for real at verify time.

## Acceptance Evidence

- Branch: wp/create-antigravity-agy-adapter/wp-001-agy-pty-adapter-and-registration (deleted post-merge)
- Completed: `2026-06-25T17:26:07Z` (Step 12 by calling session)
