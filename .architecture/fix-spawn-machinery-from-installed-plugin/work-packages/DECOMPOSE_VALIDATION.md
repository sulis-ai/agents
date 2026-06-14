# Decompose Validation — fix-spawn-machinery-from-installed-plugin

> **Change:** CH-3FNT33 · fix
> **Source of record:** `.changes/fix-spawn-machinery-from-installed-plugin.SPEC.md`
> **Design:** `../DESIGN.md` (lightweight design note in place of a full TDD —
> right-sizing: one located root cause, one resolver, two call-site redirects).
> **WP set:** 1 (WP-001)
> **INDEX lint (#60/#335):** `wpx-index lint --project fix-spawn-machinery-from-installed-plugin`
> → `{"ok": true, "header": "canonical", "round_trip": "ok"}` (exit 0).
> **Verdict:** **PASS** — single-WP set; atomicity, contract, and DoD complete;
> several rubric phases trivially satisfied or N/A for a contained single-kind fix.

## Rubric

### P1 — Atomicity (each WP independently implementable)

**PASS.** WP-001 is implementable from the SPEC + `../DESIGN.md` + the named
source/test files without reading any other WP (there is none). The decision
**not** to split into two WPs (resolver / call-site redirect) is the load-bearing
atomicity call (DESIGN DD-4):

- The redirect cannot land without the resolver, and the characterisation test
  (`test_explicit_scripts_dir_equals_install_on_single_version_machine`) gates
  both.
- Splitting would yield a WP that adds a resolver nothing calls (no behaviour
  change, no green AC) plus a wholly-dependent second WP — manufacturing a
  dependency edge for one indivisible change.

One WP is correct.

### P2 — Contract completeness (interfaces / types / files named)

**PASS.** WP-001's Contract names:

- The new function `_resolve_installed_scripts_dir() -> Path` with its full
  three-tier resolution order, the exact reused primitives
  (`_prune_cache.default_cache_root()`, `_prune_cache._SULIS_SUBPATH`,
  `_version_pick.max_version()`), and the import mechanism (existing
  `sys.path.insert` + sibling import).
- The exact env-var name decision (`SULIS_SPAWN_SCRIPTS_DIR`, DD-1) and why not
  `SULIS_SCRIPTS_DIR`.
- Both call-site edits by line (303 viewer, 350 origin-hook) and the unchanged
  `hooks_dir = scripts_dir / "hooks"`.
- The three modified files, the preserved public-surface invariants (signatures
  of `_build_launch_script` / `_build_viewer_exec_line` unchanged; quoting
  unchanged), and an explicit "What this WP is NOT" (no viewer/daemon
  self-location edit; no #102 logic).

### P3 — DoD is TDD-first (Red → Green → Blue, named tests)

**PASS.** Red lists 7 named tests with nodeids, written first against the **pure**
builders + resolver with a **fake cache under `tmp_path`** and `monkeypatch`
(never the real `~/.claude`) — the green-but-broken guard (assert the resolved
path in the emitted script, not just that the function ran):

- characterisation (single-version install → explicit == install),
- AC-3 numeric-newest, AC-4 override (incl. set-but-missing fall-through),
- AC-5 graceful fallback, AC-1 viewer exec line, AC-2 origin-hook exports,
  AC-6 shlex-quote + `bash -n` parse.

Green maps the resolver + two redirects to the tests they green and lists the
existing launcher tests that must stay green (incl. the bash-parse/run-to-exec
regression tests). It also reconciles the pre-existing
`test_build_viewer_exec_line_targets_colocated_viewer` (stays valid because
`_build_viewer_exec_line` keeps its `scripts_dir` parameter). Blue requires the
two `__file__.parent` call sites to be **gone** (grep gate), the resolver
docstring to carry the DD-1 rationale, ruff clean, and the full launcher unit
suite green. `verification:` frontmatter is Shape 1 (concrete), adapter
`backend`, artifacts = the AC-1 + AC-2 nodeids.

### P4 — Sequence / dependency graph (no cycles, correct ordering)

**PASS (trivial).** Single node, no edges. `dependsOn: []`, `blocks: []`. No
cycle possible. RGB ordering inside the WP is documented; INDEX round-trip lint
confirms the graph parses.

### P5 — Change-primitive correctness (per change-primitives.md)

**PASS.** Primitive `fix`; group `REINFORCE` with `composite_of: [REORGANISE-
Refactor, REINFORCE-Harden]`. Justified:

- The dominant move is **REINFORCE-Harden** — adding a resolver that points the
  spawn at the installed copy, hardening an existing path against the
  fork-the-running-code failure mode, pinned test-first.
- The **REORGANISE-Refactor** component is collapsing the two duplicated
  `Path(__file__).resolve().parent` call sites into one named resolver — a
  behaviour-preserving structural move, so the
  **Characterisation-Tests-Before-Refactor MUST** applies and is satisfied by
  `test_explicit_scripts_dir_equals_install_on_single_version_machine`, named in
  the `characterisation_test` frontmatter.
- **No Wrap.** The resolver is new code the launcher *owns and calls*; it wraps
  nothing. The Ports-vs-Wrappers and No-Band-Aid-Wrappers MUSTs are satisfied —
  an internal script is extended/refactored in place, no wrapper layer over
  internal code.
- **EP-03 reuse** honoured: the resolver composes `_prune_cache` + `_version_pick`
  rather than re-deriving cache paths or version ordering (Generate/Create
  rejected at the cross-group walk in favour of compose).

### P6 — Cross-kind / contract-first wiring (CF-05)

**N/A.** Single-kind `backend` set. No `frontend`/`async` kind, no cross-kind
data contract → no data-contract WP, no contract-first routing,
`audit-contracts` not triggered.

### P7 — Verification-plan concretion (TDD §Verification Plan → WP frontmatter)

**PASS.** DESIGN §4 names the design-time concretions; WP-001's Verification Plan
resolves each AC to a concrete pytest nodeid in the two **existing** suites
(Constraint: extend, don't fork), names the test seam (pure builders + resolver
with a tmp_path fake cache + monkeypatched `default_cache_root`), the strategy
(real-tmp/in-memory, classification `existing`, hermetic — no vendor mock, no
network), and the shape (concrete — ships its own RED→GREEN tests). The
bootstrap-from-zero case is a single `pytest` invocation needing only stdlib +
pytest.

### P8 — Right-sizing / restraint

**PASS.** Tier-S work: lightweight DESIGN.md (no full TDD), zero ADRs (a
single-resolver fix following established in-repo composition does not warrant
one — DD-1..DD-4 are recorded in DESIGN.md, not promoted to ADRs), one WP, 3-file
touch surface. Journey-walk recorded `exempt` (internal build machinery, no user
round-trip). No circuit breakers triggered.

## Decisions surfaced (→ Working Set / Design)

- **DD-1** env var `SULIS_SPAWN_SCRIPTS_DIR` (not `SULIS_SCRIPTS_DIR`) — accepted.
- **DD-2** resolution order override → cache → `__file__.parent` — accepted.
- **DD-3** do not touch viewer/daemon self-location — accepted (spec non-goal).
- **DD-4** one WP, not two — accepted.
- **NFR-5** stdlib-only held; **NFR** no-behavioural-change-on-single-version-
  install held + pinned by the characterisation test.
