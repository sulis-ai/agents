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
     EXCEPT in server/adapters/SpineEmitterMinter.ts (the cold-start mint's
     confirm-gated ACT path — WP-010 fix-forward, ADR-007 amended: writes the
     emitter config yaml + stages entities for the all-or-nothing brain mint).
     Why: the cockpit reads worktrees and transcripts; it never writes to them
     EXCEPT through the audited, confirm-gated mint seam.

  2. git spawn
     Forbids: spawn("git", …) / spawnSync("git", …) / execFile("git", …)
     anywhere except lib/gitShow.ts (which runs the read-only `git show`).
     Why: only `git show <base>:<path>` is permitted; it cannot mutate.

  3. Mutating git verbs
     Forbids: the tokens "add" / "commit" / "reset" / "checkout" appearing as
     quoted argv elements (e.g. inside a spawn arg array).
     Why: these are the four mutating porcelain verbs banned by TDD §13.7.

  4. Non-zero process signals
     Forbids: process.kill(pid, <sig>) where <sig> is anything but 0.
     Why: liveness is observation-only (ADR-005); signal 0 probes without
     affecting the target. Any other signal would terminate/interrupt it.

  2b. Process start outside the sanctioned bridge (WP-005, ADR-003)
     Forbids: spawn / spawnSync / execFile / execFileSync of ANY child
     EXCEPT in server/adapters/StreamJsonSessionBridge.ts (the one session
     process-start site) and server/lib/gitShow.ts (read-only `git show`).
     Why: resume/spawn launches a `claude` session — the most consequential
     side effect in the app. It is confined to one audited adapter; loading
     any read surface starts no process (NFR-SEC-05).

  5. HTTP mutation verbs on the Express app/router
     Forbids: app/router .post / .put / .patch / .delete in server/ EXCEPT
     in server/routes/chat.ts (the ONE sanctioned write path — the chat
     relay, ADR-001/003). Every other route is GET-only.
     Why: the cockpit is read-only everywhere except the one explicitly-
     audited write seam.

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

# Accumulate per-rule hits across all files.
declare -a fs_hits=() git_spawn_hits=() git_verb_hits=() kill_hits=() http_hits=() bind_hits=() proc_hits=()

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
  if [ "$rel" != "server/adapters/SpineEmitterMinter.ts" ]; then
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
  #     The guarantee this rule adds: NO NEW file may start a process; a future
  #     route or lib that sprouts a spawn fails the gate.
  case "$rel" in
    "$BRIDGE_ADAPTER_REL" | \
    server/lib/gitShow.ts | \
    server/adapters/SulisChangeStoreReader.ts | \
    server/adapters/SulisChangeRecreator.ts | \
    server/adapters/SpineEmitterMinter.ts)
      ;; # sanctioned process-start site — skip
    *)
      while IFS= read -r line; do
        [ -n "$line" ] && proc_hits+=("$rel: $line")
      done < <(printf '%s\n' "$stripped" | grep -nE \
        '\b(spawn|spawnSync|execFile|execFileSync)[[:space:]]*\(' \
        || true)
      ;;
  esac

  # 3. Mutating git verbs as quoted argv tokens
  while IFS= read -r line; do
    [ -n "$line" ] && git_verb_hits+=("$rel: $line")
  done < <(printf '%s\n' "$stripped" | grep -nE \
    '["'\''](add|commit|reset|checkout)["'\'']' \
    || true)

  # 4. Non-zero process signals
  while IFS= read -r line; do
    [ -n "$line" ] && kill_hits+=("$rel: $line")
  done < <(printf '%s\n' "$stripped" | grep -nE \
    'process\.kill[[:space:]]*\([^,]+,[[:space:]]*[^0[:space:])]' \
    || true)

  # 5 + 6 are server-only.
  case "$rel" in
    server/*)
      # The mutation-verb rule now catches BOTH `app.post` and `router.post`
      # (and put/patch/delete) — except in the ONE sanctioned relay file, which
      # may register exactly one write route (ADR-003). Every other server file
      # must stay GET-only.
      if [ "$rel" != "$RELAY_ROUTE_REL" ]; then
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
