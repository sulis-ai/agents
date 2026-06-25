#!/usr/bin/env bash
# WP-016 — read-only inventory gate (TDD §13.7, ADR-003).
#
# This is the load-bearing "read-only guarantee" gate for the whole
# cockpit MVP. It statically proves the cockpit never writes: it greps
# the active source tree under apps/cockpit/ for forbidden mutating
# operations and exits non-zero if any appear.
#
# It is *complementary* to:
#   - apps/cockpit/server/tests/read-only-inventory.test.ts (server-only,
#     Vitest, module level).
#   - apps/cockpit/client/src/tests/inventory.test.ts (client fetch funnel).
# This script walks the WHOLE workspace (server + client + shared) so the
# guarantee can never silently regress in either surface.
#
# Excluded from the scan (legitimate write sites):
#   - node_modules/                — third-party code.
#   - **/tests/** and e2e/         — test fixtures seed temp dirs/files.
#   - scripts/                     — this gate + tooling.
#   - dist/ build/ coverage/       — build artefacts.
#
# Run locally:   bash apps/cockpit/scripts/check-read-only.sh
# Explain rules: bash apps/cockpit/scripts/check-read-only.sh --explain

set -euo pipefail

# --- locate the cockpit root relative to this script ------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"   # apps/cockpit

# --- --explain ---------------------------------------------------------------
if [ "${1:-}" = "--explain" ]; then
  cat <<'EXPLAIN'
Read-only inventory gate — what each rule forbids
=================================================

The cockpit is read-only by design (ADR-003). Each rule below proves a
specific class of mutation is absent from the active source tree.

  1. Filesystem writes
     Forbids: fs.writeFile / writeFileSync / appendFile / appendFileSync /
     createWriteStream, and the same as bare named imports (await writeFile(…)),
     EXCEPT in:
       - server/adapters/SpineEmitterMinter.ts (the cold-start mint's
         confirm-gated ACT path — WP-010 fix-forward, ADR-007 amended: writes
         the emitter config yaml + stages entities for the all-or-nothing mint).
       - server/lib/turnSummaries.ts (ADR-015 named exception): writes a hashed
         disk cache of Haiku-generated turn summaries — a derived cache outside
         the cockpit's read surface, never a worktree or transcript write.
     Why: the cockpit reads worktrees and transcripts; it never writes to them
     EXCEPT through the audited, confirm-gated mint seam and the summary cache.

  2. git spawn
     Forbids: spawn("git", …) / spawnSync("git", …) / execFile("git", …)
     anywhere except lib/gitShow.ts (which runs the read-only `git show`).
     Why: only `git show <base>:<path>` is permitted; it cannot mutate.

  3. Mutating git verbs
     Forbids: the tokens "add" / "commit" / "reset" / "checkout" appearing as
     quoted argv elements (e.g. inside a spawn arg array).
     Why: these are the four mutating porcelain verbs banned by TDD §13.7.

  4. Non-zero process signals
     Forbids: process.kill(pid, <sig>) where <sig> is anything but 0, EXCEPT in
     server/lib/changeAdvanced.ts (ADR-015 named exception): the operator
     "stop a process" action sends SIGTERM then escalates to SIGKILL. This is
     an explicit, operator-invoked OS action on a process the operator already
     sees — not a background mutation of a read surface.
     Why: liveness is observation-only (ADR-005); signal 0 probes without
     affecting the target. Any other signal would terminate/interrupt it — only
     the audited operator stop-process site may do so.

  2b. Process start outside the sanctioned bridge (WP-005, ADR-003)
     Forbids: spawn / spawnSync / execFile / execFileSync of ANY child
     EXCEPT in server/adapters/StreamJsonSessionBridge.ts (the one session
     process-start site), server/lib/gitShow.ts (read-only `git show`), the
     audited change read/recreate/mint/start adapters,
     server/lib/turnSummaries.ts (ADR-015 named exception): it spawns `claude`
     headless to produce the Haiku one-line turn summary it caches on disk — a
     best-effort derived-summary helper, not a session start, and
       - server/lib/ensureDaemon.ts (WP-007, ADR-001/003 — the SHARED DAEMON
         start): the cockpit `ensureDaemon`s the shared Python session-manager
         daemon on demand (the daemon owns the pty + AF_UNIX socket). THE SPAWN
         MOVED HERE from index.ts's retired ephemeral host (`startSessionManager
         Host`); the gate follows the spawn. It is the second founder-intended
         write path's process-start seam; allow-listed BY PATH alongside the chat
         bridge above. No other file may start the daemon; index.ts now starts no
         process. The daemon is ensured at boot (a single audited site), never on
         a read.
     Why: resume/spawn launches a `claude` session — the most consequential
     side effect in the app. It is confined to one audited adapter; loading
     any read surface starts no process (NFR-SEC-05).

  2c. WebSocket-attachment outside the sanctioned terminal sidecar (WP-005, ADR-010)
     Forbids: attaching a WebSocket upgrade handler to the HTTP server —
     `new WebSocketServer(`, `.handleUpgrade(`, or `.on("upgrade"` — of ANY
     kind EXCEPT in server/adapters/TerminalSidecar.ts (ADR-010 — the terminal
     sidecar bridge: the ONE WS-ATTACHMENT write-transport seam).
     Why: typing into a live PTY is a write — keystrokes drive a real shell in
     the change's worktree. The terminal is a SANCTIONED write path (ADR-010),
     gated at attach authorisation in the engine, not a read-only bypass. Its
     transport seam is the WebSocket upgrade attachment; it is confined to one
     named, audited file. The HTTP surface stays GET-only — the WS endpoint
     rides `upgrade`, never `app.post`. Every other file that attaches a WS
     upgrade handler is a violation, the literal analogue of rule 2b for the
     terminal's write transport. INDEPENDENCE (founder directive): the terminal
     sidecar is its OWN bridge — added alongside chat's seams (ADR-003), never
     coupled to them.

  5. HTTP mutation verbs on the Express app/router
     Forbids: app/router .post / .put / .patch / .delete in server/ EXCEPT in:
       - server/routes/chat.ts (the ONE sanctioned write path — the chat relay,
         ADR-001/003).
       - server/routes/advanced.ts (ADR-015 named exception): its two operator
         POST routes — reveal-in-finder + stop-process — are explicit operator
         actions, not edits to any read surface.
       - server/routes/chatScope.ts (WP-002, ADR-002/003): the per-product chat
         routes — PUT /provider + POST /message — the chat relay's per-product
         sibling, riding the SAME SessionBridge (the message route relays a turn;
         the provider PUT persists the picker's choice via the one allow-listed
         chat-store adapter write).
     Every other route is GET-only.
     Why: the cockpit is read-only everywhere except the chat write seam and
     the explicitly-audited operator-action routes.

  6. Non-loopback bind
     Forbids: "0.0.0.0" or any bind/listen address other than 127.0.0.1 in
     server/.
     Why: ADR-002 — the cockpit binds to loopback only; it is never exposed
     on the network.

Comments and string-literal docs that *mention* a forbidden token are not
flagged: the scan strips // line comments and /* … */ block comments first.
EXPLAIN
  exit 0
fi

# --- the file set to scan ----------------------------------------------------
# Active TypeScript source only, excluding node_modules, tests, e2e fixtures,
# build artefacts, and the scripts dir itself.
#
# We read into an array with a portable while-loop (not `mapfile`, which is
# absent from the bash 3.2 that ships with macOS) so the gate runs locally
# and in CI alike.
SOURCE_FILES=()
while IFS= read -r _f; do
  SOURCE_FILES+=("$_f")
done < <(
  find "$ROOT" \
    \( -path "*/node_modules/*" \
       -o -path "*/tests/*" \
       -o -path "*/e2e/*" \
       -o -path "*/scripts/*" \
       -o -path "*/dist/*" \
       -o -path "*/build/*" \
       -o -path "*/coverage/*" \) -prune \
    -o \( -type f \( -name '*.ts' -o -name '*.tsx' \) -print \) \
  | sort
)

if [ "${#SOURCE_FILES[@]}" -eq 0 ]; then
  echo "Read-only inventory: no source files found under $ROOT — refusing to pass vacuously." >&2
  exit 1
fi

# --- strip comments so prose mentioning a forbidden token isn't flagged ------
# Removes /* … */ block comments and // line comments. A `//` preceded by ':'
# (e.g. http://) is kept so URLs in string literals survive.
strip_comments() {
  # shellcheck disable=SC2016
  perl -0pe 's{/\*.*?\*/}{}gs' "$1" \
    | perl -pe 's{(?<!:)//.*$}{}'
}

violations=0
report() {
  # $1 = rule label, $2... = matching lines (already prefixed file:line)
  local label="$1"; shift
  if [ "$#" -gt 0 ]; then
    echo "VIOLATION [$label]:"
    printf '  %s\n' "$@"
    violations=$((violations + 1))
  fi
}

# WP-005 (ADR-003) — the ONE sanctioned write path is the chat relay; the ONE
# sanctioned process-start site is the SessionBridge prod adapter. These two
# files are allow-listed BY PATH; every other file must still be clean.
RELAY_ROUTE_REL="server/routes/chat.ts"
BRIDGE_ADAPTER_REL="server/adapters/StreamJsonSessionBridge.ts"

# ADR-015 (keep-the-gate-with-named-exception) — four operator-action +
# summary-cache sites. Each is a single, audited file outside the cockpit's
# read surface; each is allow-listed BY PATH with the same discipline as the
# chat relay and the process-start sites above. No exception beyond these four.
ADVANCED_ROUTE_REL="server/routes/advanced.ts"          # operator POSTs: reveal-in-finder + stop-process
CHANGE_ADVANCED_REL="server/lib/changeAdvanced.ts"      # operator "stop a process" — SIGTERM/SIGKILL
TURN_SUMMARIES_REL="server/lib/turnSummaries.ts"        # turn-summary disk cache write + Haiku `claude` spawn

# WP-005 (ADR-010) — the interactive terminal is a SANCTIONED write path. The
# gate names EXACTLY two terminal write seams, each allow-listed BY PATH (parity
# with the ADR-003 relay/bridge pairing): the sidecar bridge's WS-ATTACHMENT
# (the keystroke → live-PTY transport, rule 2c) and the SHARED-daemon
# PROCESS-START (server/lib/ensureDaemon.ts, in rule 2b's set — WP-007 MOVED it
# there from index.ts's retired ephemeral host). No exception beyond these.
TERMINAL_SIDECAR_REL="server/adapters/TerminalSidecar.ts"  # the ONE WS-attachment seam (ADR-010)

# WP-005 (ADR-019) — the Settings write surface's sanctioned writer. The
# SpineSettingsAdapter is the ONLY new process-start site in the settings change:
# it execFiles the validated python helpers (edit / set-status / list / emit) and
# writes a temp emitter-config yaml on a fresh-brain product mint (mkdtemp /
# writeFile / rm under tmpdir — NEVER the founder's folder). It is allow-listed
# BY PATH for both the filesystem-write rule (1) and the process-start rule (2b),
# the same single-audited-site discipline as SpineEmitterMinter. The settings
# router (server/routes/settings.ts) carries the mutation verbs but starts no
# process and writes no file itself — it delegates to this one adapter.
SETTINGS_ADAPTER_REL="server/adapters/SpineSettingsAdapter.ts"

# WP-006 (ADR-019) — the Settings router is the THIRD sanctioned write-verb file
# (parity with the chat relay + the operator-action route). It registers the
# settings CRUD mutation verbs (`router.post` / `router.delete`) BUT starts no
# process and writes no file itself: every mutation delegates to the SettingsStore
# port, whose sole adapter (SpineSettingsAdapter, above) is the one allow-listed
# writer. Allow-listed BY PATH for the HTTP mutation-verb rule (rule 5) ONLY —
# it gains NO filesystem-write or process-start exception. Every OTHER file with
# a mutation verb is still a violation.
SETTINGS_ROUTE_REL="server/routes/settings.ts"

# Per-change product assignment — the changes router's PUT /:id/product sets
# for_product on a change's brain record. Like the settings router it carries a
# mutation verb BUT starts no process and writes no file itself: the write
# delegates to the allow-listed SpineSettingsAdapter. Allow-listed BY PATH for
# the HTTP mutation-verb rule (rule 5) ONLY — no filesystem-write or
# process-start exception; every OTHER file with a mutation verb still violates.
CHANGES_ROUTE_REL="server/routes/changes.ts"

# WP-002 (ADR-002/003) — the per-product chat seam. The routes file carries the
# PUT /provider + POST /message mutation verbs (the per-product sibling of the
# chat relay, riding the SAME SessionBridge); the store adapter carries the one
# sanctioned FS write (the AI-03 per-scope provider remember — an atomic
# temp-write + rename under the chat root). Each is allow-listed BY PATH with
# the same single-audited-site discipline as the chat relay + settings sites.
CHAT_SCOPE_ROUTE_REL="server/routes/chatScope.ts"
CHAT_SCOPE_ADAPTER_REL="server/adapters/LocalChatScopeStore.ts"

# Accumulate per-rule hits across all files.
declare -a fs_hits=() git_spawn_hits=() git_verb_hits=() kill_hits=() http_hits=() bind_hits=() proc_hits=() ws_hits=()

for f in "${SOURCE_FILES[@]}"; do
  rel="${f#"$ROOT"/}"
  stripped="$(strip_comments "$f")"

  # 1. Filesystem writes. Catches the fs.X member form, the *Sync named
  #    forms, and the bare named-import call form (writeFile(…) /
  #    appendFile(…) / createWriteStream(…)) regardless of an `await`
  #    prefix. The bare-call patterns use a negative guard so a member
  #    access on an unrelated object (e.g. `.writeFile(`) is matched too —
  #    that is still a write and should be flagged for inspection.
  #
  #    SANCTIONED WRITE SITE (WP-010 fix-forward, ADR-007 amended): the
  #    SpineEmitterMinter is the cold-start mint's confirm-gated ACT path. It
  #    writes the tenant/product config yaml the validated emitters consume and
  #    stages entities for the all-or-nothing promotion into the brain. It is
  #    allow-listed BY PATH here — the same single-audited-site discipline as the
  #    chat relay (rule 5) and the process-start sites (rule 2b).
  #    ADR-015 also allow-lists turnSummaries.ts (the turn-summary disk cache):
  #    it writes a hashed cache file of Haiku-generated turn summaries. This is
  #    a derived cache outside the cockpit's read surface — never a worktree or
  #    transcript write.
  if [ "$rel" != "server/adapters/SpineEmitterMinter.ts" ] && [ "$rel" != "$TURN_SUMMARIES_REL" ] && [ "$rel" != "$SETTINGS_ADAPTER_REL" ] && [ "$rel" != "$CHAT_SCOPE_ADAPTER_REL" ]; then
    while IFS= read -r line; do
      [ -n "$line" ] && fs_hits+=("$rel: $line")
    done < <(printf '%s\n' "$stripped" | grep -nE \
      '(\bfs\.(writeFile|writeFileSync|appendFile|appendFileSync|createWriteStream)\b|\b(writeFile|writeFileSync|appendFile|appendFileSync|createWriteStream)[[:space:]]*\()' \
      || true)
  fi

  # 2. git spawn outside lib/gitShow.ts
  if [ "$rel" != "server/lib/gitShow.ts" ]; then
    while IFS= read -r line; do
      [ -n "$line" ] && git_spawn_hits+=("$rel: $line")
    done < <(printf '%s\n' "$stripped" | grep -nE \
      '(spawn|spawnSync|execFile|execFileSync)[[:space:]]*\([[:space:]]*["'\'']git["'\'']' \
      || true)
  fi

  # 2b. WP-005 (ADR-003 NEW rule) — process start (spawn/exec of ANY child)
  #     outside the sanctioned set. This makes "the bridge is the only thing
  #     that starts a SESSION" a runnable check: resume/spawn launches a
  #     `claude` session (the most consequential side effect), so any process
  #     start outside the audited set is flagged.
  #
  #     The sanctioned set (path allow-list — each is a single, audited site):
  #       - StreamJsonSessionBridge.ts — the ONE session process-start (NEW).
  #       - gitShow.ts                 — read-only `git show` (MVP, rule 2).
  #       - SulisChangeStoreReader.ts  — read-only `sulis-list-changes` helper.
  #       - SulisChangeRecreator.ts    — the recreate-on-demand CLI (RecreateRunner
  #                                       port; an explicitly-invoked read/recreate,
  #                                       MVP ADR-004 — never in-process server work).
  #       - SpineEmitterMinter.ts      — the deterministic cold-start mint (WP-010
  #                                       fix-forward, ADR-007 amended): invokes the
  #                                       validated spine-emitter CLIs + `git init`
  #                                       on a confirmed onboarding turn. Confirm-
  #                                       gated + all-or-nothing; the mint moved
  #                                       server-side because the agent-delegated
  #                                       mint was slow + unreliable (minted nothing).
  #       - SulisChangeStarter.ts      — the deterministic start-from-intent
  #                                       change-start (WP-011, ADR-007): execFiles
  #                                       `sulis-change start` + `git clone` on a
  #                                       confirmed start turn. Confirm-gated +
  #                                       all-or-nothing; server-side for the SAME
  #                                       reason as the mint (the agent-delegated
  #                                       act was slow + created nothing).
  #     The guarantee this rule adds: NO NEW file may start a process; a future
  #     route or lib that sprouts a spawn fails the gate.
  case "$rel" in
    "$BRIDGE_ADAPTER_REL" | \
    server/lib/gitShow.ts | \
    server/adapters/SulisChangeStoreReader.ts | \
    server/adapters/SulisChangeRecreator.ts | \
    server/adapters/SpineEmitterMinter.ts | \
    server/adapters/SulisChangeStarter.ts | \
    server/lib/ensureDaemon.ts | \
    "$SETTINGS_ADAPTER_REL" | \
    "$TURN_SUMMARIES_REL")
      ;; # sanctioned process-start site — skip
      #   - SpineSettingsAdapter.ts (WP-005, ADR-019) — the Settings write
      #     surface's sanctioned writer; execFiles the validated python helpers.
      #     The only new process-start site in the settings change.
      #   - turnSummaries.ts (ADR-015) — spawns `claude` headless to produce the
      #     Haiku one-line turn summary cached on disk. A derived-summary helper,
      #     not a session start; the summary is best-effort + the spawn is the
      #     only consequential call it makes.
      #   - server/lib/ensureDaemon.ts (WP-007, ADR-001/003) — spawns the SHARED
      #     Python session-manager daemon on demand (the detached
      #     `spawn(python, session_manager_daemon.py)`). THE SPAWN MOVED HERE from
      #     index.ts's retired ephemeral host (`startSessionManagerHost`); the gate
      #     follows the spawn (the WP-007 Contract). index.ts now starts NO process
      #     — it only calls the ensure binding. The HTTP surface stays GET-only.
    *)
      while IFS= read -r line; do
        [ -n "$line" ] && proc_hits+=("$rel: $line")
      done < <(printf '%s\n' "$stripped" | grep -nE \
        '\b(spawn|spawnSync|execFile|execFileSync)[[:space:]]*\(' \
        || true)
      ;;
  esac

  # 2c. WP-005 (ADR-010 NEW rule) — WebSocket-attachment (attaching a WS upgrade
  #     handler to the HTTP server) outside the sanctioned terminal sidecar.
  #     Typing into a live PTY is a write; the terminal's write transport is the
  #     WebSocket upgrade attachment. The shapes: `new WebSocketServer(`,
  #     `.handleUpgrade(`, `.on("upgrade"`. Allow-listed BY PATH in exactly the
  #     sidecar bridge (parity with rule 2b's process-start allow-list). Every
  #     OTHER file that attaches a WS upgrade handler is flagged — the literal
  #     analogue of "the bridge is the only thing that starts a session".
  #     The host PROCESS-start (server/index.ts) is the second terminal seam and
  #     is covered by rule 2b's allow-list above; here we guard the WS transport.
  if [ "$rel" != "$TERMINAL_SIDECAR_REL" ]; then
    while IFS= read -r line; do
      [ -n "$line" ] && ws_hits+=("$rel: $line")
    done < <(printf '%s\n' "$stripped" | grep -nE \
      '(new[[:space:]]+WebSocketServer[[:space:]]*\(|\.handleUpgrade[[:space:]]*\(|\.on[[:space:]]*\([[:space:]]*["'\'']upgrade["'\''])' \
      || true)
  fi

  # 3. Mutating git verbs as quoted argv tokens
  while IFS= read -r line; do
    [ -n "$line" ] && git_verb_hits+=("$rel: $line")
  done < <(printf '%s\n' "$stripped" | grep -nE \
    '["'\''](add|commit|reset|checkout)["'\'']' \
    || true)

  # 4. Non-zero process signals
  #    ADR-015 allow-lists changeAdvanced.ts: the operator "stop a process"
  #    action sends SIGTERM then escalates to SIGKILL. This is an explicit,
  #    operator-invoked OS action on a process the operator already sees — not
  #    a background mutation of any read surface. Allow-listed BY PATH.
  if [ "$rel" != "$CHANGE_ADVANCED_REL" ]; then
    while IFS= read -r line; do
      [ -n "$line" ] && kill_hits+=("$rel: $line")
    done < <(printf '%s\n' "$stripped" | grep -nE \
      'process\.kill[[:space:]]*\([^,]+,[[:space:]]*[^0[:space:])]' \
      || true)
  fi

  # 5 + 6 are server-only.
  case "$rel" in
    server/*)
      # The mutation-verb rule now catches BOTH `app.post` and `router.post`
      # (and put/patch/delete) — except in the ONE sanctioned relay file, which
      # may register exactly one write route (ADR-003). Every other server file
      # must stay GET-only.
      #    ADR-015 also allow-lists advanced.ts: its two operator POST routes
      #    (reveal-in-finder + stop-process) are explicit operator actions, not
      #    edits to any read surface. Allow-listed BY PATH alongside the relay.
      #    WP-006 (ADR-019) also allow-lists settings.ts: the THIRD sanctioned
      #    write surface — its settings CRUD verbs delegate to the one allow-
      #    listed adapter (it starts no process, writes no file itself).
      #    WP-002 (ADR-002/003) also allow-lists chatScope.ts: the per-product
      #    chat routes (PUT /provider + POST /message) — the chat relay's
      #    per-product sibling, riding the SAME SessionBridge. Allow-listed BY PATH.
      if [ "$rel" != "$RELAY_ROUTE_REL" ] && [ "$rel" != "$ADVANCED_ROUTE_REL" ] && [ "$rel" != "$SETTINGS_ROUTE_REL" ] && [ "$rel" != "$CHANGES_ROUTE_REL" ] && [ "$rel" != "$CHAT_SCOPE_ROUTE_REL" ]; then
        while IFS= read -r line; do
          [ -n "$line" ] && http_hits+=("$rel: $line")
        done < <(printf '%s\n' "$stripped" | grep -nE \
          '\b(app|router)\.(post|put|patch|delete)[[:space:]]*\(' \
          || true)
      fi

      while IFS= read -r line; do
        [ -n "$line" ] && bind_hits+=("$rel: $line")
      done < <(printf '%s\n' "$stripped" | grep -nE \
        '["'\'']0\.0\.0\.0["'\'']' \
        || true)
      ;;
  esac
done

report "filesystem write API"        "${fs_hits[@]+"${fs_hits[@]}"}"
report "git spawn outside gitShow.ts" "${git_spawn_hits[@]+"${git_spawn_hits[@]}"}"
report "process start outside the sanctioned bridge" "${proc_hits[@]+"${proc_hits[@]}"}"
report "WS-attachment outside the sanctioned terminal sidecar" "${ws_hits[@]+"${ws_hits[@]}"}"
report "mutating git verb token"      "${git_verb_hits[@]+"${git_verb_hits[@]}"}"
report "non-zero process signal"      "${kill_hits[@]+"${kill_hits[@]}"}"
report "HTTP mutation verb"           "${http_hits[@]+"${http_hits[@]}"}"
report "non-loopback bind literal"    "${bind_hits[@]+"${bind_hits[@]}"}"

if [ "$violations" -gt 0 ]; then
  echo ""
  echo "Read-only inventory FAILED: $violations rule(s) violated above."
  echo "The cockpit must stay read-only (ADR-003). See: bash $0 --explain"
  exit 1
fi

echo "Read-only inventory clean — scanned ${#SOURCE_FILES[@]} source files; no mutating operations found."
