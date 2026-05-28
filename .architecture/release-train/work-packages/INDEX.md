# Work Package Index — release-train

> **Change:** CH-01KSQN · create · Closes #66
> **TDD:** [../TDD.md](../TDD.md)
> **ARCH:** [../ARCH.yaml](../ARCH.yaml)
> **Source:** `.changes/release-train.SPEC.md` (Option B, founder-chosen) + the
>   WP-001 batch code-review (PR-1fd6d60) + the founder's "cover all 22 primitives" decision
>   + the WP-002/003/004 batch code-review (PR-e858389)
> **Total WPs:** 9 (spec WP-1..WP-7 → WP-001..WP-007; WP-008 keystone remediation from PR-1fd6d60; WP-009 batch-defect remediation from PR-e858389)
> **Critical path:** WP-001 → WP-008 → WP-003 → WP-006 (depth 4); WP-001 → WP-008 → WP-004 → WP-005 → WP-007 (depth 5). WP-009 forks off WP-002+WP-003 (depth 3) and is a release blocker for this change but gates no remaining WP.
> **Peak parallelism:** 3 (WP-002, WP-003, WP-004 all become ready as soon as WP-008 lands)
> **Tier:** M (per TDD Sizing Report; sFPC ~12, ASR ~10)
> **Keystone:** WP-001 (CONTRACT_FIRST — the changeset YAML contract everything reads/writes), **finalised by WP-008**

## Status Summary

| Status | Count |
|---|---|
| pending | 4 |
| in_progress | 0 |
| step-7-complete | 3 |
| done | 2 |
| blocked | 0 |

> WP-001 + WP-008 are `done` (the keystone + its remediation, both merged).
> WP-002/003/004 are `step-7-complete` (merged on the change branch; the batch
> gate PR-e858389 returned Block, so nothing shipped to `main`). WP-009 (pending)
> forward-fixes the two batch-gate defects in WP-002 + WP-003 before the change
> ships; WP-005/006/007 stay pending.

## Primitive Distribution

| Group | Primitive | Count | WPs |
|---|---|---|---|
| EXPAND | Create | 4 | WP-001 (new helper + contract), WP-003 (new GHA), WP-004 (new skill), WP-005 (new CI guard), WP-006 (new protection config) |
| EXPAND | Extend | 2 | WP-002 (extend the `/sulis:change` ship flow), WP-008 (extend the keystone's tier map + writer guard + contract rules) |
| REINFORCE | Document | 1 | WP-007 (standards + docs) |
| REINFORCE | Fix | 1 | WP-009 (harden the keystone to accept `str | Path`; single-quote the Action loop-guard literal) |

> Count note: WP-006 is Create-shaped (net-new config artifact) but its blast
> radius makes it founder-gated; it is listed under Create above. EXPAND-Create
> rows total 5 lines / 4 distinct "new module/file" WPs + the config WP. WP-009 is
> `primitive: fix` / `group: reinforce` — a behaviour-correcting hardening of the
> merged WP-002 + WP-003, not a new surface (REINFORCE runs orthogonally on the
> EXPAND/REORGANISE/SUBSTITUTE/CONTRACT work; a forward fix is a Fix primitive).

All WPs are EXPAND or REINFORCE. **No Wrap, no Strangle, no Refactor.**

## Wrap Audit

| WP | Subject | Ownership | Removal Plan | Status |
|---|---|---|---|---|

**No Wraps proposed.** `_changeset.py` is a new leaf module (EXPAND-Create). The
GHA, the version-check guard, and the release-train skill are net-new
consumers/guards reading the changeset contract — not wrappers over internal
code. The one internal-code edit (WP-002, the ship flow) is a genuine EXTEND of
the SKILL.md body (adds a step), not a wrap. The MECE-3 rule that *"implementing
a new consumer against a contract is Create, not Wrap"* applies.

## Dependency Graph

```mermaid
graph TD
  WP001[WP-001<br/>_changeset.py + .changesets/README.md<br/>KEYSTONE / contract] --> WP008[WP-008<br/>full 22-primitive tier map<br/>+ writer guard + contract rules<br/>KEYSTONE REMEDIATION]
  WP008 --> WP002[WP-002<br/>ship writes a changeset]
  WP008 --> WP003[WP-003<br/>release-on-merge.yml GHA<br/>bump authority]
  WP008 --> WP004[WP-004<br/>/sulis:release-train skill]
  WP003 --> WP006[WP-006<br/>main branch protection<br/>FOUNDER-GATED]
  WP004 --> WP005[WP-005<br/>version-check.yml<br/>ADVISORY-FIRST]
  WP005 --> WP007[WP-007<br/>standards + docs<br/>retire manual bump]
  WP002 --> WP009[WP-009<br/>batch-defect remediation<br/>str|Path keystone + GHA loop-guard<br/>RELEASE BLOCKER, gates no WP]
  WP003 --> WP009
```

Critical paths: **WP-001 → WP-008 → WP-003 → WP-006** (depth 4) and
**WP-001 → WP-008 → WP-004 → WP-005 → WP-007** (depth 5).

Independent at start (after WP-008): **WP-002, WP-003, WP-004** all become ready
the moment the remediated keystone lands. WP-008 sits on the path of all three
because they conform to the *finalised* contract (the full tier map + the
documented format rules), not the pre-remediation keystone.

**WP-009** depends on **WP-002 + WP-003** (it forward-fixes a defect in each, found
by the batch gate PR-e858389): the `str`/`Path` producer crash (WP-002's call-site
+ the keystone) and the Action's non-loading loop-guard literal (WP-003). It
`blocks: []` — WP-005/006/007 do not depend on these fixes functionally — but it is
a **release blocker** for this change: the producer crashes on every ship until
FIX 1 lands, so WP-009 MUST be DONE before the change ships.

## WP Table

> Header is the canonical `| ID | Title | Primitive | Status | Depends On | Blocks |`
> signature the wpx-index / parse_index_md header lint requires (ID first; no
> duplicate `kind` column). Each WP file's frontmatter carries `kind:` +
> `change_id: 01KSQNPBPN7W74QVAZ25F79RNH` per WORK_PACKAGE_STANDARD v1.1.0.

| ID | Title | Primitive | Status | Depends On | Blocks | Kind | Token (in/out) | Spec WP |
|---|---|---|---|---|---|---|---|---|
| WP-001 | Changeset data model + helper (`_changeset.py`) + the YAML contract | Create | done | — | WP-008 | backend | 10k / 7k | WP-1 |
| WP-008 | Keystone remediation — full 22-primitive tier map + writer guard + contract rules | Extend | done | WP-001 | WP-002, WP-003, WP-004 | backend | 9k / 6k | — |
| WP-002 | `/sulis:change ship` writes a changeset (replaces manual-bump expectation) | Extend | done | WP-008 | — | docs | 6k / 3k | WP-2 |
| WP-003 | `release-on-merge.yml` GHA — the bump authority | Create | done | WP-008 | WP-006 | infra | 8k / 6k | WP-3 |
| WP-004 | `/sulis:release-train` skill — drafts the dev→main PR (read-only) | Create | done | WP-008 | WP-005 | docs | 7k / 5k | WP-4 |
| WP-005 | `version-check.yml` CI guard — ADVISORY-FIRST (warn, exit 0) | Create | done | WP-004 | WP-007 | infra | 5k / 3k | WP-5 |
| WP-006 | `main` branch protection — founder-gated config | Create | done | WP-003 | — | infra | 5k / 3k | WP-6 |
| WP-007 | Standards + docs + retire the manual bump going forward | Document | done | WP-005 | — | docs | 6k / 4k | WP-7 |
| WP-009 | Batch-defect remediation — keystone accepts `str` or `Path` + the Action loop-guard expression loads | Fix | done | WP-002, WP-003 | — | backend | 7k / 3k | — |
| **Total** |  |  |  |  |  |  | **63k / 40k** |  |

## Recommended Implementation Order (bootstrapping-correct)

Respects the spec's "Bootstrapping sequence" (avoids self-lockout) + the
dependency graph.

**Round 1 — the keystone (1 WP):**
- WP-001 (the contract + deterministic core). Nothing else can land first
  (CONTRACT_FIRST). **Merged; remediated by Round 1.5 before consumers dispatch.**

**Round 1.5 — keystone remediation (1 WP, after the keystone lands, before the writer/authority/skill round):**
- WP-008 (full 22-primitive tier map + writer injection guard + cross-language
  contract rules). Driven by the WP-001 batch code-review (PR-1fd6d60) + the
  founder's "cover all 22 primitives" decision. It finalises the contract every
  consumer reads — the complete tier map (so no code-altering primitive ships
  with no release) and the written format rules (so the WP-003 bash reader can't
  diverge). WP-002/003/004 build on this, NOT on the pre-remediation keystone.

**Round 2 — writer + bump authority + skill (up to 3 WPs, parallel):**
- WP-002 (ship writes a changeset) — so changes START producing changesets.
- WP-003 (the GHA bump authority) — so the bump authority EXISTS.
- WP-004 (the release-train skill) — so releases can be CUT from changesets.

  > Spec bootstrapping points 1+2: ship WP-001+WP-008+WP-002+WP-003 first (the
  > finalised keystone + writer + authority) BEFORE any enforcement; then WP-004
  > (releases can be cut). WP-002/003/004 share no files, so they can run in one
  > parallel batch — but only once WP-008 has finalised the contract they conform to.

**Round 2.5 — fix the batch-gate defects (1 WP, after Round 2 merges, before the founder-gated protection round):**
- WP-009 (batch-defect remediation). Driven by the WP-002/003/004 batch
  code-review (PR-e858389), which returned `Block` on one CRITICAL: the ship step
  never writes a changeset (`write_changeset('.changesets', …)` passes a `str`;
  the keystone calls `.mkdir()` → `AttributeError`), and the Action's loop-guard
  expression won't load (double-quoted literal inside `${{ }}`). WP-009 hardens the
  keystone to accept `str | Path` (immunising every caller, with a test proving a
  `str` dir round-trips) and single-quotes the GHA literal. It is a **release
  blocker** for this change — the producer crashes on every ship until it lands —
  but it `blocks` no remaining WP (WP-005/006/007 don't depend on these fixes).
  Both WP-002 + WP-003 are merged on the change branch and gate-blocked; nothing
  reached `main`, so this is forward remediation in place, not a revert.

**Round 3 — the founder-gated protection (1 WP, lands WITH WP-003):**
- WP-006 (main branch protection) — PAUSES for founder review of the exact
  `gh api` config; verifies the bot push on a throwaway. Lands with WP-003 so
  the bot can push the bump (spec bootstrapping point 4).

**Round 4 — advisory enforcement (1 WP):**
- WP-005 (version-check, ADVISORY/warn-only) — ships AFTER the train is live +
  producing changesets so in-flight branches without changesets don't break
  (spec bootstrapping point 3). Promotion to required is a separate later
  founder-gated step.

**Round 5 — document the new ceremony (1 WP):**
- WP-007 (standards + docs) — documents the complete flow once all machinery is
  in place; retires the manual bump from the documented flow GOING FORWARD.

**This change's own ship** (spec bootstrapping point 5) goes through the OLD flow
— a manual bump ONE last time. The train goes live for the NEXT release.

## Total surface

| Metric | Value |
|---|---|
| New files | 5 (`_changeset.py`, `tests/unit/test_changeset.py`, `.changesets/README.md`, `release-on-merge.yml`, `version-check.yml`) + 1 new skill dir (`skills/release-train/SKILL.md`) |
| Modified files | 3 (`skills/change/SKILL.md`, `git-workflow-standard.md`, marketplace/plugin version files at this change's own manual-bump ship) + 3 re-touched by WP-008 (`_changeset.py`, `tests/unit/test_changeset.py`, `.changesets/README.md` — the keystone remediation, NOT new files) |
| Config applied | 1 (`main` branch protection via `gh api`) |
| New LOC | ~250 (`_changeset.py` ~120 + its tests ~130) + ~3 workflows/skill bodies; WP-008 adds ~13 tier-map entries + 1 guard helper + ~10 tests + the README "Rules for re-implementers" section (in-place, ~+60 LOC) |

## Cross-kind / CONTRACT_FIRST seam

The changeset YAML is a **producer/consumer seam**: WP-002 writes it; WP-003 +
WP-004 read it; WP-005 reads its presence. `.changesets/README.md` (authored in
WP-001, **finalised in WP-008**) **is** that contract. Per CONTRACT_FIRST, WP-001
is the contract + keystone — it lands first. **WP-008 then finalises that
contract** (full 22-primitive tier map, the writer injection guard, and the
written "Rules for re-implementers" parser grammar), so every writer/reader
`dependsOn` WP-008, not the pre-remediation keystone. There is no separate
`kind: contract` WP because the contract is a README + a pure helper module (not
an OpenAPI/JSON-Schema cross-service seam); the README's examples AND its tier
table are validated by `test_readme_examples_parse` (WP-001) +
`test_readme_tier_table_matches_primitive_tier_map` (WP-008), giving executable
conformance without the schema tooling (ADR-005).

## Decompose Validation

See [`DECOMPOSE_VALIDATION.md`](DECOMPOSE_VALIDATION.md) for the rubric run on the
8-WP set (7 spec pieces 1:1 + WP-008 keystone remediation from the code-review) +
the proof of coverage + the bootstrapping order with Round 1.5.
