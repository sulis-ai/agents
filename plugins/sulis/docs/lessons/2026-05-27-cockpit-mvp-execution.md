# Lessons — cockpit-mvp execution (CH-01KSJA)

> **Source:** the first real end-to-end exercise of the four standards +
> change-as-primitive execution, building the cockpit MVP (a local-only
> React + Node read-only review tool) in this repo.
> **Captured:** 2026-05-27, post-implement, from the bound session's
> retrospective.
> **Why this file exists:** the post-ship lessons-capture step (the
> mechanism this run motivated) isn't built yet — this is the manual
> first instance. `.architecture/` is gitignored (lesson #6), so the
> durable home for lessons is `docs/lessons/`, which travels with the repo.

Each lesson carries a disposition per the finding-triage policy
(`sulis.md` → Decision Discipline → Finding-triage policy):
**fix-now (CW-05)** / **task** / **SEA** (substantive, needs a spec).

---

## Genuine tooling bugs

> **RESOLVED 2026-05-27** — Cluster A (L-01..L-05) fixed on
> `change/refactor-executor-contract-fit` (commits addc90d, bb6a82d, 8753e34,
> f3a5ec7, 8b66560). One shared INDEX column resolver (L-02); single status
> vocabulary with a loud write-time guard (L-03); `wpx-worktree create
> --base-branch` (L-04); published-artifact no-deploy fit on pipeline + train
> + shared contract reader (L-05, also closes #39); cwd-first
> `resolve_current_change` (L-01). 623 tests green; end-to-end `list-ready`
> on a canonical `Depends On` + `pending` INDEX now passes (the cockpit
> failure shape).

### L-01 — `resolve_current_change()` returns null at startup · SEA
Returned `null` despite `SULIS_CHANGE_ID` set + a valid change branch +
manifest existing. The bound session fell back to reading
`.changes/create-cockpit-mvp.yaml` directly. The whole change-context
greeting flow depends on this resolving — real miss.
*Disposition: SEA (needs investigation — env-var read, manifest lookup,
or branch resolution).* → **Cluster A**

### L-02 — Two tools disagree on the INDEX column name, unresolvably · SEA
`wpx-index list-ready` requires the column lowercased to exactly
`depends`; `_wpxlib.parse_index_md` (used by `wpx-train` + `wpx-index
status`) requires `depends on`. **No single header satisfies both.** The
architect emitted `Depends on` (correct for the hot path) which silently
broke `list-ready`. Internal schema inconsistency — the two parsers must
share one normaliser.
*Disposition: SEA (shared normaliser).* → **Cluster A**. Highest value
(blocks any change from running).

### L-03 — Producer emits `Status: ready`; every consumer expects `pending` · SEA
`plan-work`/architect emits `ready`; `list-ready` filters for `pending`,
`wpx-train` eligibility checks `pending` — `ready` is invisible to all of
them. The decomposition was **un-runnable as shipped** until 16 rows + 16
frontmatters were migrated `ready → pending` by hand. Producer (plan-work)
and consumers (wpx-*) must agree on the initial-status vocabulary.
*Disposition: SEA (producer/consumer contract).* → **Cluster A**. Highest
value (blocks any change from running).

### L-04 — `wpx-worktree create` hardcodes `origin/dev` as base · SEA
No support for CW-04 change branches. Every executor dispatch (~10) needed
a manual `git worktree add -b … origin/change/…` + hand-written sidecar.
The worktree helper doesn't know change branches exist.
*Disposition: SEA (change-branch awareness in the worktree helper).*
→ **Cluster A**

### L-05 — run-all/wpx-train doesn't fit a `deploy_target: none` repo · SEA
The train requires `--deploy-workflow` and is built around
deploy→health→smoke. This is a published-artifact marketplace — `dev` is
the release surface. The bound session hand-drove the whole dispatch loop
(flip status → dispatch → merge-to-change-branch → flip done) instead of
the train. No clean "published-artifact, merge-to-change-branch, no-deploy"
mode.
*Disposition: SEA — **already logged as task #39.*** → **Cluster A**

## Hygiene / model gaps

### L-06 — `.architecture/` is gitignored — audit trail doesn't travel · TASK
Every WP journal, code-review bundle, and sidecar lives only locally and
never travels with the branch. The hybrid-storage promise
("reviewable in one PR") is half-met: `.changes/` manifest + spec travel,
the architecture audit trail doesn't. **Policy call needed:** should the
WP journals + review bundles travel with the change branch?
*Disposition: task (policy + .gitignore decision).*

### L-07 — Sidecar files aren't gitignored · FIX-NOW (CW-05)
`.wpx-base-sha` got swept into a worktree commit and nearly leaked onto
dev — caught at the squash. The `.executor-*-dev-sha` / `.wpx-base-sha`
family must be in `.gitignore`.
*Disposition: fix-now — pure CW-05.* **Fixed in this commit.**

### L-08 — Parallel dispatch can't honour EP-03 (extract-shared-primitive) · SEA
Two parallel executors independently built the same `relativeTime` helper
(one in `utils/`, one in `components/` — which then case-collided on
macOS); WP-006/WP-007 both appended classes to `errors.ts` and conflicted.
The shared-primitive rule can't fire across two simultaneously-running
worktrees. **Decomposition lesson:** shared utilities should be their own
**upstream WP**, not left to be discovered inside two parallel siblings.
*Disposition: SEA — a `plan-work` amendment (hoist shared primitives to an
upstream WP before parallel siblings).* → **Cluster C**

## Session slips (not the plugin)

- Backticks in a commit-message body got eaten by the shell. Use plain
  quotes in commit bodies.
- First wrote `d['data']['wps']` against `wpx-index status` when the key is
  `entries` — output schema wasn't where assumed.

---

## Triage summary

| Cluster | Lessons | Disposition |
|---|---|---|
| **A — executor doesn't fit change-branch + published-artifact model** | L-01, L-02, L-03, L-04, L-05 | One SEA change (highest value; L-02 + L-03 block any change from running un-surgically). L-05 = task #39. |
| **B — hygiene** | L-06 (task), L-07 (fixed now) | L-07 done; L-06 needs a policy call. |
| **C — decomposition method** | L-08 | `plan-work` amendment (shared primitive → upstream WP). |

Priority order from the bound session: **L-03 + L-02** (block runs), then
**L-04 + L-05** (change-branch execution model), then **L-01**.

---

## Post-ship test findings (2026-05-27, during "ship it and test it")

### L-09 — `npm run dev` ran `vite` from the wrong root; client never served · FIXED
The `dev`/`dev:client` scripts ran bare `vite` from the package root, but
`index.html` + `client/vite.config.ts` live in `client/`. Vite booted ("ready")
but 404'd on every path — the documented dev-run never served the UI. **CI's
E2E passed** because Playwright's webServer points Vite at the right root,
masking the broken dev-run. Lesson: a green E2E gate doesn't prove the
*documented* dev-run works — they're different invocations. Fix: `vite` →
`vite client` (positional root) in both scripts. Verified end-to-end:
`npm run dev` → client 200 + `<title>Sulis cockpit</title>`, server 200.
*Disposition: fixed in this commit (CW-05).*

### L-10 — ship-flow chained cleanup to an unconfirmed merge · covered by #38
The cockpit had already squash-merged to dev at 00:12 (3711658), but the
change store still showed it "ready to ship" (the #38 auto-cleanup gap) — so
a re-ship was attempted, and the command chain ran `nuke` before confirming
the (rejected, redundant) merge succeeded. No harm (work was safe on dev +
remote), but the ship flow MUST: (a) detect already-merged changes before
re-shipping, (b) only clean up after a confirmed-successful merge. Folds into
#38.

### Note — demo seed
A demo change record (CH-DEMO01, pointing at the repo root) was seeded into
the local store for the visual test; it is not a real change and should be
removed after the browser walkthrough.

### L-11 — diff feature dead for ALL changes: base_sha not in the store schema · SEA (factory)
The cockpit reads `base_sha` from the change-store record
(`SulisChangeStoreReader` → `raw.base_sha`) to render diffs. But the store
writer `_change_state.write_change_record` filters to `_CHANGE_RECORD_FIELDS`,
which does NOT include `base_sha`. So every real change's record has no
base_sha → `baseSha: null` → the diff route returns NO_BASE_SHA for every
file. **The diff view never works for a real change**, not just the demo.
This is a cockpit(consumer)↔store(producer) CONTRACT_FIRST gap: the consumer
assumed a field the producer doesn't record. Fix: add `base_sha` to
`_CHANGE_RECORD_FIELDS` + have `sulis-change start` capture + write it (it
already computes base_sha at start — saw it in the start JSON).
*Disposition: SEA (store schema + start) — task #44.*

### L-12 — cockpit server tests read the real store as a fallback · note
Several server tests create tmp fixtures but the code-under-test falls back
to the real `~/.sulis` / `~/.claude/projects` when the isolation env var
isn't set in that test — so a developer with changes in flight (or a stray
seed) makes them flake. Mirrors the SULIS_STATE_DIR-isolation fix the
PLUGIN's own tests already adopted. Minor (green with a clean store; CI
clean), but a real isolation gap. *Disposition: cockpit test-robustness
backlog (not urgent).*

### Note — process slips (mine, this session)
- Committed a fix (1a4c82c) before gating the commit on a green test run.
  Quality gate: verify green BEFORE commit, not after. (The code was sound;
  the red was my demo-seed pollution + a too-tight timeout.)
- Seeded a demo change into the REAL ~/.sulis for the visual test, which
  polluted unisolated server tests. A demo/dev store should be isolated
  (set SULIS_STATE_DIR for the dev server), never the real one.

---

## v0.1 flow dry-run learnings (re-grounding the cockpit in the Sulis instance → #45)

Walking the build-ui-style flow by hand on the cockpit surfaced exactly what
the #45 v0.1 system must handle:

- **Token resolution is the hard step.** The instance's semantic tokens
  either hold a `$value` or REFERENCE a primitive (`{primitives.colors.
  semantic.blue.600}`). v0.1's token-export step needs a resolver that walks
  refs → literal. (Prototyped: a ~30-line Python resolver → flat tokens.css.)
- **Token substitution needs complete-hex-token boundaries.** A naive
  `#fff → var(...)` replace corrupted `#fff5f5` → `var(--card)5f5`. Any
  write-time enforcement / migration tooling MUST match whole hex tokens
  (negative lookahead on hex digits), not prefixes. Real gotcha.
- **Retheme splits into core-chrome (mechanical) + status/stage tail
  (judgment).** 73 of 119 hex were unambiguous greys/primary → tokens
  (mechanical); 46 were status/stage hues (liveness green, error red, per-
  stage badge colours) needing a token decision. v0.1's enforcement should
  distinguish "tokenise now" from "needs a token mapping decision."
- **The sign-off baseline can be an EXISTING mockup.** `reference/web-app-
  mockup.html` IS the visual contract — v0.1's mockup step can reference the
  instance's existing mockups, not always generate fresh.
- **Static OODA is cheap and real.** Diffing the rethemed cockpit's resolved
  palette (#fafafa/#171717/#2563EB/#e5e5e5) against the mockup's palette
  confirmed the retheme lands on the instance — no Playwright needed.
- **Demo/dev data MUST use an isolated SULIS_STATE_DIR** (the dev server
  pointed at a tmp store), never the real ~/.sulis (re-confirms L-12).

**Done in this pass:** token resolver + tokens.css + app-wide grounding
(index.css) + 73 core-chrome replacements. **Second pass:** the 46 status/
stage hues (map liveness→positive/warning, errors→destructive, decide on
stage-badge hues vs an instance stage-colour scale).

### L-13 — static OODA passed but the founder saw NO change · #45 (visual OODA is not optional)
After the core-chrome retheme, static OODA confirmed "cockpit palette ==
mockup palette" — GREEN. But the founder saw no visible change, for two
reasons static OODA is blind to: (a) the Sulis warm-neutrals are near-
identical to the GitHub greys they replaced (#e1e4e8→#e5e5e5, white→#fafafa
— imperceptible), and (b) the brand FONTS weren't loaded — `--font-sans:
'Inter'` fell back to system-ui, so typography (the dominant visible-brand
lever) didn't move. The mockup gets its Sulis character mostly from Inter +
JetBrains Mono, which it loads via Google Fonts; the cockpit loaded neither.
**Lesson:** "tokens match the instance" ≠ "looks like the brand." Static
OODA verifies token VALUES; it cannot see font-loading or perceptual delta.
The founder's "still looks the same" is precisely the signal visual OODA
(screenshot vs mockup) catches — the screenshot would NOT match (wrong
font) despite the palette matching. So for #45 v0.1: either include visual
OODA, or have static OODA additionally assert (i) webfonts referenced by
font tokens are actually loaded, (ii) a meaningful-delta check, not just
value-equality. Fix applied: load Inter + JetBrains Mono in index.html
(matching the mockup).
