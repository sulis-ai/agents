# LIVE round-trip verification — feat: live-origin-stamping (WP-006, Part B)

> **Status:** **OBSERVED — likely→exact proven** (2026-06-08, driven by Sulis with Iain).
> Driven with the REAL change code (no mocks): the actual `assistedOriginEnv` +
> `LocalTranscriptConversationIdentity` (WP-003), the real `prepare-commit-msg`
> hook + `_origin_stamp` (#216), and the real `RecordedOriginAttribution`
> reader, against REAL git commits.
>
> **Observed evidence:**
> - **Autonomous write:** a real `git commit` with `SULIS_ORIGIN` exported (via
>   `autonomous_env`) produced the trailer
>   `Sulis-Origin: autonomous; run=01KTAUTO9REALULID000000000; confidence=0.9`.
> - **Assisted compute→write→read (the headline flip):** `assistedOriginEnv`
>   emitted `assisted; conversation=thread_01997abc-…-000000000001; turn=1`; the
>   hook stamped it on a real commit; `RecordedOriginAttribution.originFor`
>   returned `{kind:"assisted", conversation:{conversationId:"thread_01997abc-…",
>   turn:1}, attribution:"recorded"}` → **EXACT**.
> - **Degradation (the differential):** an UNSTAMPED commit read back as
>   `kind:"unknown"` (no recorded origin) → composite falls to **inferred
>   (likely)**. So stamped → exact, unstamped → likely: the flip.
> - **Cross-language grammar:** locked by the WP-006 conformance test (TS-emitted
>   bodies round-trip through Python's `parse_origin_env`).
>
> **Boundary (honest):** driven at the real-module + real-git level, NOT through
> the running cockpit HTTP server or a live `claude` child spawned by the relay
> (the local cockpit instance was unresponsive; the HTTP route is a thin wrapper
> over the exact adapters proven here, covered by routes.chat 14/14). The
> end-to-end OUTCOME (compute→write→read→flip) is proven; the last segment
> (HTTP + live spawn) remains component-tested, not OS-process-driven.
>
> **Defect found while driving (see task #4) — NOW FIXED (WP-007):** the trailer
> was appended WITHOUT a blank-line separator for Conventional Commit subjects
> (`feat:`/`fix:` fooled the appender's heuristic), so it was NOT a formal git
> trailer and `git log --format='%(trailers)'` showed nothing. WP-007 fixed the
> block-detection heuristic (it now detects the trailer block from the message's
> last paragraph), so `Sulis-Origin:` is a formal git trailer for all subjects.
> The `git log --format='%(trailers:key=Sulis-Origin)'` verify commands below are
> now CORRECT (no longer a false negative) and `git interpret-trailers --parse`
> recognises the trailer.
>
> The original runbook (for the full HTTP/UI path on a healthy cockpit) follows.
>
> **How to use this file:** run each step's command, then fill the blank
> **Observed** cell with what you actually saw (paste the real output / a
> screenshot path). When all three paths read as expected, this closes the
> SPEC acceptance (likely→exact on a real round-trip + non-fatal degradation).
> The founder runs this **with Iain**; do not pre-fill the Observed cells.

## What this proves (and what it deliberately does not)

- **Proves:** a real commit made through the **executor** (autonomous) and a
  real commit made through a **cockpit chat** (assisted) each carry the
  `Sulis-Origin:` trailer, and the cockpit origin view flips that file/commit
  from **likely (inferred) → exact (recorded)**. Two different chat
  conversations carry **different** thread ids. A commit with **no** origin set
  still lands and reads as inferred (non-fatal degradation).
- **Non-goal (documented, NOT observed here):** ASSISTED stamping for the
  interactive terminal-spawn path is out of SPEC scope for this change — it is
  not exercised by this runbook. (TDD boundary; recorded so the absence is a
  decision, not an omission.)

## Grammar under test (consume #216 unchanged)

The cross-language seam is the `SULIS_ORIGIN` env-var grammar. Part A (shipped
in CI) locks that the TS-emitted bodies round-trip through Python's
`parse_origin_env`:

```
assisted;    conversation=<thread_id>;  turn=<n>     # cockpit relay (TS) → hook (PY)
autonomous;  run=<ulid>[; confidence=<0..1>]         # executor → hook (PY)
```

`turn` is an **integer** (1-based Message ordinal); `conversation` is a
`thread_`-shaped Thread id (ADR-016).

## Pre-requisites

| # | Requirement | Command to confirm |
|---|---|---|
| P1 | A real `claude` CLI on PATH (not the CI stub) | `claude --version` |
| P2 | The cockpit running locally (server `127.0.0.1:5174`, UI `127.0.0.1:5173`) | from `apps/cockpit/`: `npm run dev` — wait for the banner `cockpit server up — bound to http://127.0.0.1:5174` |
| P3 | The origin-stamp hook wired for the repo under test | the executor / terminal launcher wires `core.hooksPath` to `plugins/sulis/scripts/hooks/`; confirm with `git -C <repo> config core.hooksPath` |
| P4 | A change id to observe (the `:id` in the origin API) | the cockpit change list, or the change's ULID under `~/.sulis/changes/` |

> Throughout: `CHANGE_ID` = the change ULID being observed; `REPO` = that
> change's worktree path; `FILE` = the repo-relative path of a file touched by
> the commit under test.

---

## Path 1 — Autonomous (executor) → EXACT

A real executor run that commits exports `SULIS_ORIGIN="autonomous; run=…"`
(WP-005) before its commit, so the wired `prepare-commit-msg` hook stamps the
trailer onto that very commit.

### 1.1 — Make a real executor commit with the origin exported

| | |
|---|---|
| **Command** | Run any WP through the executor (e.g. `/sulis:run-wp <WP>`), OR simulate the executor's Step-7 export on a real commit: `eval "$(cd <REPO> && python3 -c 'import sys; sys.path.insert(0,\"plugins/sulis/scripts\"); from _origin_stamp import autonomous_env; e=autonomous_env(run=\"01KTEST...REALULID\", confidence=None); print(\"export SULIS_ORIGIN=\\x27%s\\x27\" % e[\"SULIS_ORIGIN\"]) if e else None')"` then `git -C <REPO> commit -m "feat: real autonomous work"` |
| **Expected** | The commit lands; the hook appends the autonomous trailer. |
| **Observed** | _(fill in)_ |

### 1.2 — Confirm the commit carries the autonomous trailer

| | |
|---|---|
| **Command** | `git -C <REPO> log -1 --format='%(trailers:key=Sulis-Origin)'` |
| **Expected** | Output contains `Sulis-Origin: autonomous; run=<the-ulid>` (the run ulid you exported). |
| **Observed** | _(fill in)_ |

### 1.3 — Confirm the cockpit reports that file as EXACT (recorded)

| | |
|---|---|
| **Command** | `curl -s "http://127.0.0.1:5174/api/changes/<CHANGE_ID>/origin?path=<FILE>" \| python3 -m json.tool` |
| **Expected** | `origin.attribution == "recorded"` and `origin.kind == "autonomous"` (NOT `"inferred"`). In the UI the file's origin badge drops the "· likely" suffix. |
| **Observed** | _(fill in)_ |

---

## Path 2 — Assisted (cockpit chat) → EXACT, distinct conversations

With the cockpit running, a chat message that results in a commit makes the
relay export `SULIS_ORIGIN="assisted; conversation=thread_…; turn=<n>"` to the
sanctioned spawn, so the same hook stamps the assisted trailer.

### 2.1 — Send a cockpit chat that makes a commit

| | |
|---|---|
| **Command** | In the cockpit UI (`http://127.0.0.1:5173`), open a change's chat and send a message that produces a commit (e.g. "make a trivial commit touching `<FILE>`"). |
| **Expected** | A commit lands in `<REPO>` from the chat-relay path. |
| **Observed** | _(fill in)_ |

### 2.2 — Confirm the commit carries the assisted trailer

| | |
|---|---|
| **Command** | `git -C <REPO> log -1 --format='%(trailers:key=Sulis-Origin)'` |
| **Expected** | Output contains `Sulis-Origin: assisted; conversation=thread_<…>; turn=<n>` — `conversation` carries the `thread_` shape, `turn` is an integer. |
| **Observed** | _(fill in)_ |

### 2.3 — Confirm the cockpit flips that file likely→EXACT

| | |
|---|---|
| **Command** | `curl -s "http://127.0.0.1:5174/api/changes/<CHANGE_ID>/origin?path=<FILE>" \| python3 -m json.tool` |
| **Expected** | `origin.attribution == "recorded"` and `origin.kind == "assisted"`; `origin.conversation` shows the same `thread_` id and turn as the trailer. Before the chat (no recorded trailer) the same call read `"inferred"` (likely) — the flip is the payoff. |
| **Observed (before — likely)** | _(fill in: the attribution you saw before the chat committed)_ |
| **Observed (after — exact)** | _(fill in)_ |

### 2.4 — Two different chat conversations → two different thread ids

| | |
|---|---|
| **Command** | Repeat 2.1–2.2 in a **second, separate** chat conversation (a different session). Compare the `conversation=thread_…` value from each conversation's commit: `git -C <REPO> log --format='%(trailers:key=Sulis-Origin)' \| grep assisted` |
| **Expected** | The two commits carry **different** `conversation=thread_<…>` ids (distinct threads → distinct ids; ADR-016). Turns increment **within** a conversation. |
| **Observed (conversation A id)** | _(fill in)_ |
| **Observed (conversation B id)** | _(fill in)_ |
| **Distinct?** | _(fill in: yes/no)_ |

---

## Path 3 — Degradation (no origin set) → still lands, reads INFERRED

A commit made with no `SULIS_ORIGIN` (or a forced stamp failure) must still land
and fall back to inferred — non-fatal (ADR-013). No crash, no lost commit.

### 3.1 — Make a commit with no origin set

| | |
|---|---|
| **Command** | `unset SULIS_ORIGIN; git -C <REPO> commit --allow-empty -m "chore: no origin (degradation check)"` (or, to force a stamp failure, make the hook path unwritable/unreadable and commit normally). |
| **Expected** | The commit lands normally — exit 0, no error from the hook. |
| **Observed** | _(fill in)_ |

### 3.2 — Confirm the commit carries NO trailer

| | |
|---|---|
| **Command** | `git -C <REPO> log -1 --format='%(trailers:key=Sulis-Origin)'` |
| **Expected** | Empty output — no `Sulis-Origin:` trailer was stamped. |
| **Observed** | _(fill in)_ |

### 3.3 — Confirm the cockpit reports it as INFERRED (likely), not an error

| | |
|---|---|
| **Command** | `curl -s "http://127.0.0.1:5174/api/changes/<CHANGE_ID>/origin?path=<FILE>" \| python3 -m json.tool` |
| **Expected** | HTTP 200; `origin.attribution == "inferred"` (the "likely" badge). The unstamped commit degrades gracefully — it is NOT a 500, NOT "unknown-as-error". |
| **Observed** | _(fill in)_ |

---

## Acceptance summary (fill once all paths observed)

| Path | Expected | Observed verdict |
|---|---|---|
| 1 — Autonomous | trailer `autonomous; run=…` + cockpit **exact** | _(pass / fail)_ |
| 2 — Assisted | trailer `assisted; conversation=thread_…; turn=…` + cockpit **likely→exact** | _(pass / fail)_ |
| 2.4 — Distinct conversations | two chats → two different `thread_` ids | _(pass / fail)_ |
| 3 — Degradation | unstamped commit lands + reads **inferred** (non-fatal) | _(pass / fail)_ |

> When every verdict is **pass**, record this file as the change's
> acceptance evidence for WP-006 (per `wpx-step12 wrap`). Until then, WP-006's
> live half is **prepared, not observed** — Part A (grammar conformance) is the
> only half gated by CI.
