---
founder_facing: false
---
# Spec — Record change-origin exactly at commit time (live-stamping)

**Change:** CH-01KTHP · feat

## Intent

The provenance foundation (ADE epic #216) built the *receiving* end of
change-origin: a `prepare-commit-msg` git hook that, when `SULIS_ORIGIN` is
set in the environment, appends a `Sulis-Origin:` trailer to the commit being
made; the `_origin_stamp.py` writer + constructors; and the cockpit read path
that prefers a *recorded* (exact) origin over an *inferred* (likely) one.

What's missing is the *sending* end. Today nothing computes and exports
`SULIS_ORIGIN` at commit time, so the hook is a no-op and every commit falls
back to inferred ("likely") origin. This change wires the sending end for both
write paths so a commit's origin is recorded **exactly** at the moment it's
made:

- the cockpit **chat relay** (assisted commits), and
- the **executor** (autonomous commits).

The observable payoff: the cockpit's origin view flips a file/commit from
**likely → exact** once the trailer is present, and commits from different
chat conversations are attributed to the right conversation instead of being
guessed at.

## Scope

- **Widen the bridge spawn port to carry origin.** The
  `StreamJsonSessionBridge` `spawnBridge(argv, cwd)` port drops the third
  `originEnv` argument the production `spawnClaudeBridge(argv, cwd, originEnv?)`
  already accepts. Widen the port so the assisted-origin env reaches the
  spawned session. (The documented TODO at `StreamJsonSessionBridge.ts`.)
- **Chat relay computes conversation + turn.** On each relay, derive a stable
  **conversation id** (stable across the turns of one chat thread, distinct
  per thread) and a **1-based turn index**, build the assisted env via
  `assisted_origin(conversation, turn)` → `format_trailer`, and pass it through
  the widened port. Commits the spawned chat session makes then carry
  `Sulis-Origin: assisted; conversation=<id>; turn=<n>`.
- **Executor sets autonomous origin.** Wire the executor's commit path to
  export `SULIS_ORIGIN="autonomous; run=<lifecyclerun-ulid>; confidence=<…>"`
  before it commits, so the already-installed hook stamps it. (The terminal
  launcher already installs the hook; this feeds it.)
- **Close the multi-session attribution gap.** Because conversation id + turn
  are computed per relay, commits from concurrent or sequential chat sessions
  against the same change are each attributed to their own conversation rather
  than collapsing to one inferred guess.
- **Confirm likely → exact end to end** on a real executor commit and a real
  chat commit (live round-trip on the founder's machine).

## Non-goals

- **Interactive terminal-spawn Sulis sessions** (the `/sulis:change start
  --spawn` founder chat terminal) setting an *assisted* origin. That spawn
  surface already installs the hook but isn't covered by this change's relay
  wiring; it's a natural follow-up, called out here so it can be pulled in if
  wanted. *(Boundary — redirect if you want it in.)*
- **Changing the cockpit read/UI.** The origin badge, trace, and read
  adapters already exist and already prefer recorded over inferred; this
  change only makes recorded origin actually get written.
- **Backfilling origin** onto commits already made without a trailer. Existing
  commits keep their inferred origin.
- **The trailer format / stamper / hook themselves** — delivered by #216; this
  change consumes them unchanged.

## Acceptance

- A commit made by the **executor** during a real run carries a
  `Sulis-Origin: autonomous; run=…; confidence=…` trailer, and the cockpit
  shows that commit's origin as **exact** (recorded), not likely (inferred).
- A commit made by a **cockpit chat** session carries a
  `Sulis-Origin: assisted; conversation=…; turn=…` trailer, and the cockpit
  shows it as **exact**.
- Two commits from **two different chat conversations** against the same change
  carry **different** conversation ids; turn index increments within a
  conversation.
- A stamp **failure is non-fatal**: if the trailer can't be written, the commit
  is still made and origin degrades gracefully to inferred (no crash, no lost
  commit) — the foundation's invariant is preserved end to end.
- CI is green with the wiring covered by tests; the live round-trip is observed
  on the founder's machine.

## Constraints

- **The cockpit stays provably read-only (ADR-003).** Passing an env to the
  one sanctioned `spawn` site is read-only from the cockpit's side — it neither
  writes a file nor mutates git. No new process-start site; no second bridge.
  The trailer is written by the *spawned session's* hook, outside cockpit code.
- **Append-only at commit time (ADR-013).** No new commit, no network, nothing
  published — the trailer rides the commit the write path already makes.
- **No control chars / no trailer injection.** Reuse the foundation's
  boundary guards (`_has_control_char`, the env parser); don't re-implement
  formatting.
- **Logging discipline (NFR-SEC-03 / TDD §3.4).** One structured log line per
  stamp — ulid / id / confidence only; never commit-message text, prompt text,
  or reply text.
- **Conversation-id derivation must be stable + collision-resistant** across
  the turns of one thread and distinct across threads (exact derivation is a
  design-stage call).

## Verification Plan

- **Foundational (what proves it):** the round-trip from "a session makes a
  commit" to "the cockpit reports that commit's origin as exact" is the thing
  under test — not merely "the trailer string formats correctly."
- **Existing integrations (reused, not rebuilt):** the `prepare-commit-msg`
  hook, `_origin_stamp.py` (`assisted_origin`, `autonomous_origin`,
  `format_trailer`, `parse_origin_env`), `spawnClaudeBridge`'s `originEnv`
  param, and the cockpit `RecordedOriginAttribution` read path all exist on
  `main` (#216) and are exercised, not modified.
- **New integration — chat relay → bridge port → session env:** contract test
  that the relay computes conversation + turn and the widened `spawnBridge`
  port receives the assisted `originEnv`; verified in CI with a stubbed child.
- **New integration — executor → hook:** test that the executor's commit path
  exports the autonomous `SULIS_ORIGIN` so the hook stamps it.
- **Live observation (founder machine, out of CI):** one real cockpit-chat
  commit and one real executor commit; assert the trailer is present
  (`git log --format=%(trailers)`) and the cockpit origin view reads exact.
  This is the green-but-broken guard — CI uses a stubbed child, so the real
  `claude` round-trip must be observed at least once.
- **Degradation:** force a stamp failure (e.g. unwritable hook path) and assert
  the commit still lands and origin falls back to inferred.

## Notes

- The `#23` in the intent is the origin-stamping-live follow-up referenced
  directly in the `StreamJsonSessionBridge.ts` TODO — not the lessons-capture
  lesson the pre-spawn auto-linker attached to CONTEXT.md (that was a mislink).
