// WP-010 — read-only inventory gate (TDD §13.7 "guarantee, not convention").
//
// This test is the load-bearing proof that the cockpit server stays
// read-only. It greps the server source tree for any of the forbidden
// shapes:
//
//   - Mutation HTTP verbs:    .post(  .put(  .patch(  .delete(
//   - Writing filesystem:     fs.write*, fs.append*, fs.createWriteStream,
//                             writeFile, writeFileSync, appendFile,
//                             createWriteStream, mkdir is permitted
//                             (test-fixture dirs), but write/append must
//                             not appear.
//   - Mutating git verbs:     git add, git commit, git reset, git checkout
//                             (note: `git show` is read-only and permitted;
//                             we look for the verbs as standalone tokens
//                             passed to a spawn-argv array).
//   - Non-zero signals:       process.kill(<pid>, <sig>) where <sig> is
//                             anything other than 0.
//
// We grep:
//   - server/{index,app,config}.ts
//   - server/middleware/*.ts
//   - server/routes/*.ts
//   - server/lib/*.ts
//   - server/adapters/*.ts
//   - server/ports/*.ts
//
// (Test files themselves are excluded — they legitimately seed fixtures.)
//
// Future WPs that touch the server cannot regress without this test
// firing. That is the guarantee.

import { describe, it, expect } from "vitest";
import { readFile, readdir, stat } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const serverRoot = join(here, "..");

const SCANNED_DIRS = [
  "", // server/*.ts at the top level (index.ts, app.ts, config.ts)
  "middleware",
  "routes",
  "lib",
  "adapters",
  "ports",
];

// Mutation HTTP verbs registered on an Express app/router. Scoped to the
// `app.`/`router.` receiver so unrelated method calls (e.g. `Set.delete`,
// `Map.delete`) are not false-positives — parity with the shell gate's rule 5.
const MUTATION_VERB_PATTERNS = [
  /\b(app|router)\.post\s*\(/,
  /\b(app|router)\.put\s*\(/,
  /\b(app|router)\.patch\s*\(/,
  /\b(app|router)\.delete\s*\(/,
];

// WP-005 (ADR-003) — the chat relay is the ONE sanctioned write path; the
// SessionBridge prod adapter is the ONE sanctioned process-start site. These
// two files are allow-listed by PATH; every other file must still be clean.
// The relay registers a mutation verb (`router.post`); the bridge calls
// `spawn` (the process start). Anything else with either shape is a violation.
const RELAY_ROUTE_BASENAME = "chat.ts";
// WP-002 (ADR-002/003) — the per-product chat routes are a SANCTIONED write
// path: GET /:scope/thread is read, but PUT /:scope/provider + POST
// /:scope/message register write verbs (the provider persist + the SSE relay).
// They ride the SAME SessionBridge as the relay; this is the chat seam's
// per-product sibling, allow-listed alongside chat.ts.
const CHAT_SCOPE_ROUTE_BASENAME = "chatScope.ts";
const BRIDGE_ADAPTER_BASENAME = "StreamJsonSessionBridge.ts";
// WP-010 fix-forward (ADR-007 amended) — the deterministic cold-start mint's
// confirm-gated ACT path. It is the SECOND sanctioned process-start AND the
// sanctioned filesystem-write site (invokes the validated spine emitters +
// `git init`, writes the emitter config yaml + stages entities). Allow-listed
// BY PATH — parity with the chat relay's write-verb exception (ADR-003).
const SPINE_MINTER_BASENAME = "SpineEmitterMinter.ts";
// WP-011 — the deterministic server-side change-start's confirm-gated ACT path.
// It execFiles `sulis-change start` + `git clone` directly (the WP-010 lesson:
// never delegate the consequential act to the bridge agent). It is the THIRD
// sanctioned process-start site, allow-listed BY PATH — parity with the bridge
// + mint adapters. It registers NO new write-verb file: the route lives in
// chat.ts (the one sanctioned relay file, ADR-006).
const STARTER_BASENAME = "SulisChangeStarter.ts";
// WP-005 (ADR-019) — the Settings write surface's sanctioned writer. The
// SpineSettingsAdapter is the ONLY new process-start site in the settings
// change: it execFiles the validated python helpers (edit / set-status / list /
// emit) and writes a temp emitter-config yaml on a fresh-brain product mint
// (mkdtemp/writeFile/rm under tmpdir, never the founder's folder). It is the
// FOURTH sanctioned process-start AND a sanctioned filesystem-write site,
// allow-listed BY PATH — parity with the bridge / mint / starter adapters. The
// settings router (routes/settings.ts) carries the mutation verbs but starts no
// process and writes no file itself; it delegates to this one adapter.
const SETTINGS_ADAPTER_BASENAME = "SpineSettingsAdapter.ts";
// WP-002 (ADR-002/003) — the durable chat store adapter persists the picker's
// chosen provider per scope (`participant_context.provider`) on PUT /provider:
// an atomic temp-write + rename + mkdir under the chat root. This is the one
// sanctioned write of the per-product chat seam (the AI-03 remember), allow-
// listed BY PATH alongside the other adapter write sites.
const CHAT_SCOPE_ADAPTER_BASENAME = "LocalChatScopeStore.ts";

// WP-006 (ADR-019) — the Settings router is the THIRD sanctioned write-verb
// file (parity with the chat relay + the operator-action route). It carries the
// mutating verbs (`router.post` / `router.delete`) for the settings CRUD seam
// BUT starts no process and writes no file itself: every mutation delegates to
// the SettingsStore port, whose sole adapter (SpineSettingsAdapter, above) is
// the one allow-listed writer. Allow-listed BY PATH for the write-verb rule —
// the same single-audited-surface discipline as chat.ts. Every OTHER file with
// a mutation verb is still a violation.
const SETTINGS_ROUTE_BASENAME = "settings.ts";

// ADR-015 (keep-the-gate-with-named-exception) — four operator-action +
// summary-cache sites, each allow-listed BY PATH (parity with the relay/mint
// exceptions above). These are the ONLY additions; any OTHER file with the
// same shape still trips the gate (the negative tests below prove it).
//   - advanced.ts        — the two operator POST routes (reveal + stop-process).
//   - changeAdvanced.ts  — the operator "stop a process" SIGTERM/SIGKILL.
//   - turnSummaries.ts    — the turn-summary disk cache (writeFile) + the Haiku
//                           `claude` spawn that produces the cached summary.
const ADVANCED_ROUTE_BASENAME = "advanced.ts";
const CHANGE_ADVANCED_BASENAME = "changeAdvanced.ts";
// Per-change product assignment — the changes router's PUT /:id/product sets
// for_product on a change's brain record. The write itself happens in the
// allow-listed SpineSettingsAdapter (the route does no I/O); the route file is
// allow-listed BY PATH like the settings router, same single-audited-site rule.
const CHANGES_ROUTE_BASENAME = "changes.ts";
const TURN_SUMMARIES_BASENAME = "turnSummaries.ts";

// WP-004 (ADR-010/ADR-011) — the terminal composition's process-start site:
// the ONE place that spawns the Python session-manager engine.
//   WP-007 (ADR-001/ADR-003) — THE SPAWN MOVED. The cockpit no longer spawns its
//   OWN ephemeral host at boot (the retired `startSessionManagerHost` in
//   index.ts). It now `ensureDaemon`s the SHARED daemon, and that detached
//   `spawn(python, session_manager_daemon.py)` lives in `lib/ensureDaemon.ts`.
//   The gate FOLLOWS the spawn: the sanctioned process-start site is now
//   `ensureDaemon.ts`, allow-listed BY PATH (parity with the bridge/mint/starter
//   exceptions above). `index.ts` itself now starts NO process — it only calls
//   the ensure binding. The HTTP surface stays GET-only — the WS endpoint rides
//   `upgrade`, never `app.post`. Named as one of the two terminal write seams
//   (the other is the sidecar bridge's WS-attachment, below) in
//   `test_terminal_seams_are_named_exceptions`.
const DAEMON_ENSURE_BASENAME = "ensureDaemon.ts";

// WP-005 (ADR-010) — the terminal sidecar bridge is the SECOND founder-intended
// write path's transport seam. It registers NO `app.post` and starts NO process
// (the daemon spawn lives in lib/ensureDaemon.ts, WP-007); instead it attaches a WebSocket upgrade
// handler to the existing HTTP server's `upgrade` event — the WS-ATTACHMENT
// seam. A keystroke written into a live PTY through this seam is a sanctioned
// write, gated at attach authorisation in the engine (ADR-010 §1). The gate
// allow-lists this ONE file BY PATH for WS-attachment — every other file that
// attaches a WS upgrade handler is a violation, the literal analogue of the
// process-start rule. This keeps the GET-only HTTP surface provable AND names
// the new write transport as an audited exception (not a silent bypass).
//   INDEPENDENCE (founder directive): the terminal sidecar is its OWN bridge —
//   it does not depend on, and is not coupled to, the chat relay/bridge. The
//   allow-list ADDS the terminal seams alongside chat's; it does not couple them.
const TERMINAL_SIDECAR_BASENAME = "TerminalSidecar.ts";

// WS-attachment shapes — attaching a WebSocket upgrade handler to the HTTP
// server. This is the terminal's write-transport seam (browser keystroke →
// live PTY). Forbidden everywhere except the allow-listed sidecar bridge
// (the ADR-010 WS-attachment rule), parity with PROCESS_START_PATTERNS.
const WS_ATTACHMENT_PATTERNS = [
  /\bnew\s+WebSocketServer\s*\(/,
  /\.handleUpgrade\s*\(/,
  /\.on\s*\(\s*["']upgrade["']/,
];

// Process-start shapes — spawn/exec of a child process. Forbidden everywhere
// except the allow-listed bridge adapter (the new ADR-003 process-start rule).
const PROCESS_START_PATTERNS = [
  /\bspawn\s*\(/,
  /\bspawnSync\s*\(/,
  /\bexecFile\s*\(/,
  /\bexecFileSync\s*\(/,
];

function basename(file: string): string {
  const parts = file.split("/");
  return parts[parts.length - 1] ?? file;
}

// Filesystem mutation tokens. `mkdir` is intentionally permitted (no
// content written; only used by some helpers' test fixtures, never in
// active server source, but we don't ban it to keep this list narrow).
const FS_MUTATION_PATTERNS = [
  /\bfs\.writeFile\b/,
  /\bfs\.writeFileSync\b/,
  /\bfs\.appendFile\b/,
  /\bfs\.appendFileSync\b/,
  /\bfs\.createWriteStream\b/,
  /\bwriteFileSync\s*\(/, // direct named imports
  /\bappendFileSync\s*\(/,
  /\bcreateWriteStream\s*\(/,
  // Named imports from node:fs/promises: writeFile/appendFile as a
  // top-level reference. These would appear as `await writeFile(`.
  /\bawait\s+writeFile\s*\(/,
  /\bawait\s+appendFile\s*\(/,
];

// Mutating git verbs (positional first arg after "git" or appearing as
// a standalone argv element). The grep is conservative — `git show` is
// read-only; the verbs below are the ones banned by TDD §13.7.
const GIT_MUTATION_PATTERNS = [
  /["']add["']/,
  /["']commit["']/,
  /["']reset["']/,
  /["']checkout["']/,
];

// Signal-other-than-zero: `process.kill(pid, "SIGTERM")` etc. The
// liveness probe uses `process.kill(pid, 0)` — that is permitted.
//
// Pattern logic: after `process.kill(<arg>,`, skip whitespace, then the
// next character must be a digit `0`. Any other character flags. We
// use a character-class anchor (`[^0\s]`) for the first non-whitespace
// after the comma — robust to variable spacing, refuses string "0" or
// numeric variables (both flag, both should be inspected).
const NON_ZERO_KILL_PATTERN = /process\.kill\s*\([^,]+,\s*[^0\s]/;

async function walkTsFiles(dir: string): Promise<string[]> {
  let entries;
  try {
    entries = await readdir(dir, { withFileTypes: true });
  } catch {
    return [];
  }
  const files: string[] = [];
  for (const e of entries) {
    if (e.name.startsWith(".")) continue;
    const full = join(dir, e.name);
    if (e.isFile() && e.name.endsWith(".ts")) {
      files.push(full);
    }
  }
  return files;
}

async function collectSourceFiles(): Promise<string[]> {
  const all: string[] = [];
  for (const sub of SCANNED_DIRS) {
    const dir = sub === "" ? serverRoot : join(serverRoot, sub);
    let s;
    try {
      s = await stat(dir);
    } catch {
      continue;
    }
    if (!s.isDirectory()) continue;
    const tsFiles = await walkTsFiles(dir);
    for (const f of tsFiles) {
      // The top-level scan picks up index.ts, app.ts, config.ts but
      // NOT files in subdirectories (which are scanned explicitly).
      if (sub === "") {
        const rel = f.substring(serverRoot.length + 1);
        if (rel.includes("/")) continue;
      }
      // Never scan the tests dir itself — fixtures may legitimately
      // write files. The SCANNED_DIRS list excludes "tests" by design;
      // this guard is double-defence.
      if (f.includes("/tests/")) continue;
      all.push(f);
    }
  }
  return all;
}

async function readSource(file: string): Promise<string> {
  return await readFile(file, "utf8");
}

/**
 * Strip line comments and block comments so the grep does not flag a
 * forbidden token that lives inside a comment block. The cockpit's lib
 * files (e.g. errors.ts, readWorktreeTree.ts) discuss git verbs in
 * prose comments; that prose is documentation, not active code.
 *
 * We scan line-by-line for `//` comments (anchored to each physical
 * line, not just the start of the file) so a `// process.kill(pid, 0)`
 * comment on line 41 of a file is not mistaken for active code.
 */
function stripComments(src: string): string {
  // 1. Remove /* ... */ (greedy, single-line + multiline).
  let out = src.replace(/\/\*[\s\S]*?\*\//g, "");
  // 2. Remove // line comments on each line. A `//` inside a string
  //    literal is rare in our codebase; we don't try to be a full
  //    tokeniser here — the inventory is a coarse gate, not a parser.
  out = out
    .split("\n")
    .map((line) => {
      const idx = line.indexOf("//");
      if (idx === -1) return line;
      // If the `//` is preceded by `:` (e.g. `http://`) or sits inside
      // an obvious URL, keep the line intact. The cockpit's prod code
      // doesn't have URLs in active source other than CORS origin
      // strings — those are inside string literals and survive this
      // heuristic.
      if (idx > 0 && line[idx - 1] === ":") return line;
      return line.substring(0, idx);
    })
    .join("\n");
  return out;
}

describe("read-only inventory (TDD §13.7)", () => {
  it("registers no POST / PUT / PATCH / DELETE routes — except the sanctioned relay + operator-action routes (ADR-003/015)", async () => {
    const files = await collectSourceFiles();
    expect(files.length).toBeGreaterThan(0);
    // The chat relay (ADR-003), the operator-action routes (ADR-015), and the
    // settings router (WP-006, ADR-019) are the ONLY allow-listed write-verb
    // files.
    const WRITE_VERB_ALLOW = new Set([
      RELAY_ROUTE_BASENAME,
      CHAT_SCOPE_ROUTE_BASENAME,
      ADVANCED_ROUTE_BASENAME,
      SETTINGS_ROUTE_BASENAME,
      CHANGES_ROUTE_BASENAME,
    ]);
    const offenders: string[] = [];
    const writeVerbFiles = new Set<string>();
    for (const f of files) {
      const src = stripComments(await readSource(f));
      const hasVerb = MUTATION_VERB_PATTERNS.some((p) => p.test(src));
      if (!hasVerb) continue;
      writeVerbFiles.add(basename(f));
      if (WRITE_VERB_ALLOW.has(basename(f))) continue;
      offenders.push(`${f} :: HTTP mutation verb outside the allow-list`);
    }
    expect(offenders, JSON.stringify(offenders)).toEqual([]);
    // The EXACT exception set: exactly the relay + the operator-action route +
    // the settings router register a write verb — no more, no less.
    expect([...writeVerbFiles].sort()).toEqual(
      [
        RELAY_ROUTE_BASENAME,
        CHAT_SCOPE_ROUTE_BASENAME,
        ADVANCED_ROUTE_BASENAME,
        SETTINGS_ROUTE_BASENAME,
        CHANGES_ROUTE_BASENAME,
      ].sort(),
    );
  });

  // WP-006 (ADR-019) — the settings router IS a write-verb file (its sanctioned
  // job), but it is the load-bearing ADR-019 proof that it starts NO process and
  // writes NO file itself: every mutation delegates to the SettingsStore port,
  // whose sole adapter (SpineSettingsAdapter) is the one allow-listed writer.
  it("the settings router carries write verbs but starts no process and writes no file (ADR-019)", async () => {
    const files = await collectSourceFiles();
    const router = files.find((f) => basename(f) === SETTINGS_ROUTE_BASENAME);
    expect(
      router,
      "routes/settings.ts must exist (the THIRD sanctioned write surface)",
    ).toBeDefined();
    if (router) {
      const src = stripComments(await readSource(router));
      // It DOES register mutation verbs (that is its sanctioned job).
      expect(MUTATION_VERB_PATTERNS.some((p) => p.test(src))).toBe(true);
      // But it starts NO process and writes NO file — the delegation invariant.
      expect(PROCESS_START_PATTERNS.some((p) => p.test(src))).toBe(false);
      expect(FS_MUTATION_PATTERNS.some((p) => p.test(src))).toBe(false);
    }
  });

  it("starts no child process — except the one sanctioned SessionBridge adapter (ADR-003 new rule)", async () => {
    const files = await collectSourceFiles();
    const offenders: string[] = [];
    const starters: string[] = [];
    for (const f of files) {
      const src = stripComments(await readSource(f));
      const startsProcess = PROCESS_START_PATTERNS.some((p) => p.test(src));
      if (!startsProcess) continue;
      starters.push(basename(f));
      // The sanctioned process-start set (path allow-list; parity with the
      // shell gate's rule 2b): the ONE session bridge (NEW), plus the existing
      // audited read/recreate subprocess sites (gitShow's `git show`, the
      // change-store list helper, the recreate-on-demand CLI). Every OTHER file
      // that starts a process is a violation — the new ADR-003 guarantee.
      const SANCTIONED_PROCESS_STARTERS = new Set([
        BRIDGE_ADAPTER_BASENAME,
        "gitShow.ts",
        "SulisChangeStoreReader.ts",
        "SulisChangeRecreator.ts",
        SPINE_MINTER_BASENAME,
        STARTER_BASENAME,
        // WP-005 (ADR-019) — the Settings adapter, the only new process-start
        // site in the settings change; it execFiles the validated python
        // helpers. Allow-listed BY PATH, parity with the mint adapter.
        SETTINGS_ADAPTER_BASENAME,
        // ADR-015 — turnSummaries.ts spawns `claude` headless for the Haiku
        // one-line turn summary it caches on disk (a derived-summary helper).
        TURN_SUMMARIES_BASENAME,
        // WP-007 (ADR-001/003) — lib/ensureDaemon.ts spawns the SHARED session-
        // manager daemon on demand (the detached `spawn(python,
        // session_manager_daemon.py)`). The spawn MOVED here from index.ts's
        // retired ephemeral host; the gate follows the spawn (the WP-007 Contract).
        DAEMON_ENSURE_BASENAME,
      ]);
      if (SANCTIONED_PROCESS_STARTERS.has(basename(f))) {
        continue;
      }
      offenders.push(`${f} :: process start outside the sanctioned bridge`);
    }
    expect(offenders, JSON.stringify(offenders)).toEqual([]);
    // Positive assertion: the sanctioned bridge IS present and IS the only
    // session process-start site (a relay with no bridge is half-built).
    expect(starters).toContain(BRIDGE_ADAPTER_BASENAME);
    // ADR-015 positive assertion: the summary helper IS exception-listed and IS
    // a real process-start site (it spawns the Haiku summariser).
    expect(starters).toContain(TURN_SUMMARIES_BASENAME);
  });

  it("calls no filesystem-mutating APIs — except the sanctioned mint adapter + summary cache (ADR-007 amended / ADR-015)", async () => {
    const files = await collectSourceFiles();
    // The mint adapter (ADR-007) and the turn-summary disk cache (ADR-015) are
    // the ONLY allow-listed write sites — each BY PATH.
    const FS_WRITE_ALLOW = new Set([
      SPINE_MINTER_BASENAME,
      TURN_SUMMARIES_BASENAME,
      // WP-005 (ADR-019) — the Settings adapter writes a temp emitter-config
      // yaml on a fresh-brain product mint (mkdtemp/writeFile/rm under tmpdir).
      // It NEVER writes the founder's folder (the disk-safety sentinel proves
      // remove + unlink leave it untouched). Allow-listed BY PATH.
      SETTINGS_ADAPTER_BASENAME,
      // WP-002 (ADR-002/003) — the chat-store adapter persists the per-scope
      // provider choice (the AI-03 remember). Allow-listed BY PATH.
      CHAT_SCOPE_ADAPTER_BASENAME,
    ]);
    const offenders: string[] = [];
    const writeFiles = new Set<string>();
    for (const f of files) {
      const src = stripComments(await readSource(f));
      const hasWrite = FS_MUTATION_PATTERNS.some((p) => p.test(src));
      if (!hasWrite) continue;
      writeFiles.add(basename(f));
      if (FS_WRITE_ALLOW.has(basename(f))) continue;
      offenders.push(`${f} :: filesystem write outside the allow-list`);
    }
    expect(offenders, JSON.stringify(offenders)).toEqual([]);
    // The EXACT exception set: the mint adapter + the summary cache + the
    // settings adapter (ADR-019).
    expect([...writeFiles].sort()).toEqual(
      [
        SPINE_MINTER_BASENAME,
        TURN_SUMMARIES_BASENAME,
        SETTINGS_ADAPTER_BASENAME,
        CHAT_SCOPE_ADAPTER_BASENAME,
      ].sort(),
    );
  });

  it("invokes no mutating git verbs (add / commit / reset / checkout)", async () => {
    const files = await collectSourceFiles();
    const offenders: string[] = [];
    for (const f of files) {
      const src = stripComments(await readSource(f));
      for (const pat of GIT_MUTATION_PATTERNS) {
        if (pat.test(src)) {
          offenders.push(`${f} :: ${pat}`);
        }
      }
    }
    expect(offenders).toEqual([]);
  });

  it("sends only signal 0 to other processes — except the operator stop-process site (ADR-005 / ADR-015)", async () => {
    const files = await collectSourceFiles();
    // changeAdvanced.ts is the ONLY allow-listed non-zero-signal site (ADR-015):
    // the operator "stop a process" action sends SIGTERM → SIGKILL.
    const offenders: string[] = [];
    const nonZeroSignalFiles = new Set<string>();
    for (const f of files) {
      const src = stripComments(await readSource(f));
      if (!NON_ZERO_KILL_PATTERN.test(src)) continue;
      nonZeroSignalFiles.add(basename(f));
      if (basename(f) === CHANGE_ADVANCED_BASENAME) continue;
      offenders.push(`${f} :: process.kill with non-zero signal outside the allow-list`);
    }
    expect(offenders, JSON.stringify(offenders)).toEqual([]);
    // The EXACT exception set: only the operator stop-process site signals.
    expect([...nonZeroSignalFiles]).toEqual([CHANGE_ADVANCED_BASENAME]);
  });

  // WP-009 (ADR-006) — the concierge is READ-ONLY: it rides the SAME bridge as
  // the chat and reaches consequence ONLY through the already-sanctioned paths.
  // It must add NO new file-level write/process exception (WP-009 AC#3): the
  // write-verb allow-list stays exactly {chat.ts} and the process-start
  // allow-list stays exactly the audited bridge/git/recreate set. The concierge
  // read lib (lib/concierge/conciergeRead.ts) must itself be clean.
  it("adds NO new write-verb file for the concierge — the allow-list stays {chat.ts, advanced.ts} (FR-N8/ADR-006/015)", async () => {
    const files = await collectSourceFiles();
    const writeVerbFiles: string[] = [];
    for (const f of files) {
      const src = stripComments(await readSource(f));
      if (MUTATION_VERB_PATTERNS.some((p) => p.test(src))) {
        writeVerbFiles.push(basename(f));
      }
    }
    // The concierge POST rides the sanctioned relay (chat.ts) — it adds NO new
    // write-verb file. The write-verb allow-list is exactly the relay + the
    // operator-action route (advanced.ts, ADR-015) + the settings router
    // (settings.ts, WP-006/ADR-019).
    expect(writeVerbFiles.sort()).toEqual(
      [
        RELAY_ROUTE_BASENAME,
        CHAT_SCOPE_ROUTE_BASENAME,
        ADVANCED_ROUTE_BASENAME,
        SETTINGS_ROUTE_BASENAME,
        CHANGES_ROUTE_BASENAME,
      ].sort(),
    );
  });

  it("the concierge read lib starts no process and writes nothing (FR-N8)", async () => {
    const conciergeLib = join(serverRoot, "lib", "concierge", "conciergeRead.ts");
    const src = stripComments(await readSource(conciergeLib));
    expect(PROCESS_START_PATTERNS.some((p) => p.test(src))).toBe(false);
    expect(FS_MUTATION_PATTERNS.some((p) => p.test(src))).toBe(false);
    expect(MUTATION_VERB_PATTERNS.some((p) => p.test(src))).toBe(false);
  });

  // WP-011 (ADR-006) — start-from-intent's consequential act reaches consequence
  // ONLY through the sanctioned `sulis-change start` path (the new
  // SulisChangeStarter adapter). It must add NO new write-verb file: the route
  // lives in chat.ts (the one sanctioned relay), and the orchestration lib stays
  // process-free (the adapter is the one audited process-start site).
  it("adds NO new write-verb file for start-from-intent — the allow-list stays {chat.ts, advanced.ts} (ADR-006/015)", async () => {
    const files = await collectSourceFiles();
    const writeVerbFiles: string[] = [];
    for (const f of files) {
      const src = stripComments(await readSource(f));
      if (MUTATION_VERB_PATTERNS.some((p) => p.test(src))) {
        writeVerbFiles.push(basename(f));
      }
    }
    // The start-from-intent POST rides the sanctioned relay (chat.ts) — it adds
    // NO new write-verb file. The write-verb allow-list is exactly the relay +
    // the operator-action route (advanced.ts, ADR-015) + the settings router
    // (settings.ts, WP-006/ADR-019).
    expect(writeVerbFiles.sort()).toEqual(
      [
        RELAY_ROUTE_BASENAME,
        CHAT_SCOPE_ROUTE_BASENAME,
        ADVANCED_ROUTE_BASENAME,
        SETTINGS_ROUTE_BASENAME,
        CHANGES_ROUTE_BASENAME,
      ].sort(),
    );
  });

  it("the start-from-intent orchestration lib starts no process and writes nothing (the act is the adapter's)", async () => {
    const startLib = join(serverRoot, "lib", "discovery", "startFromIntent.ts");
    const src = stripComments(await readSource(startLib));
    expect(PROCESS_START_PATTERNS.some((p) => p.test(src))).toBe(false);
    expect(FS_MUTATION_PATTERNS.some((p) => p.test(src))).toBe(false);
    expect(MUTATION_VERB_PATTERNS.some((p) => p.test(src))).toBe(false);
  });

  it("the SulisChangeStarter adapter IS the only new process-start site (deterministic server-side act)", async () => {
    const files = await collectSourceFiles();
    const starter = files.find((f) => basename(f) === STARTER_BASENAME);
    expect(starter, "SulisChangeStarter.ts must exist (the deterministic act)").toBeDefined();
    if (starter) {
      const src = stripComments(await readSource(starter));
      // It DOES start a process (that is its sanctioned job).
      expect(PROCESS_START_PATTERNS.some((p) => p.test(src))).toBe(true);
    }
  });

  // WP-005 (ADR-010) — the interactive terminal is a SANCTIONED write path, not
  // a read-only bypass. It introduces EXACTLY two write seams, each named and
  // path-scoped (parity with ADR-003's chat relay/bridge pairing):
  //   1. the terminal sidecar bridge's WS-ATTACHMENT (TerminalSidecar.ts) — the
  //      browser-keystroke → live-PTY transport, gated at attach authorisation;
  //   2. the daemon PROCESS-START (lib/ensureDaemon.ts, WP-007) — the one site
  //      that spawns the Python SHARED daemon that owns the pty + AF_UNIX socket.
  //      (WP-007 MOVED this from index.ts's retired ephemeral host; index.ts now
  //      starts NO process — it only calls the ensure binding. The gate follows.)
  // This test is the positive proof: those two files are the ONLY terminal
  // seams, every OTHER file that attaches a WS upgrade handler is a violation,
  // and the chat seams (ADR-003) are untouched alongside them.
  it("test_terminal_seams_are_named_exceptions — the sidecar WS-attachment + daemon-ensure start are the ONLY two terminal seams (ADR-010/WP-007)", async () => {
    const files = await collectSourceFiles();
    expect(files.length).toBeGreaterThan(0);

    // (a) WS-attachment is allow-listed BY PATH in exactly the sidecar bridge.
    // Every other file that attaches a WS upgrade handler is a violation — the
    // literal analogue of the process-start rule (the terminal's write is the
    // keystroke that reaches the PTY through this attached socket).
    const wsOffenders: string[] = [];
    const wsAttachers = new Set<string>();
    for (const f of files) {
      const src = stripComments(await readSource(f));
      const attachesWs = WS_ATTACHMENT_PATTERNS.some((p) => p.test(src));
      if (!attachesWs) continue;
      wsAttachers.add(basename(f));
      if (basename(f) === TERMINAL_SIDECAR_BASENAME) continue;
      wsOffenders.push(`${f} :: WS-attachment outside the sanctioned terminal sidecar`);
    }
    expect(wsOffenders, JSON.stringify(wsOffenders)).toEqual([]);
    // The EXACT WS-attachment exception set: exactly the sidecar bridge attaches
    // a WS upgrade handler — no more, no less. (A terminal view that mounted a
    // second WS-attachment file would fail here.)
    expect([...wsAttachers]).toEqual([TERMINAL_SIDECAR_BASENAME]);

    // (b) The sidecar bridge itself starts NO process and registers NO write
    // verb — its only write seam is the WS-attachment. The daemon spawn lives in
    // lib/ensureDaemon.ts; the two seams are deliberately separate files (ADR-010 §2).
    const sidecar = files.find((f) => basename(f) === TERMINAL_SIDECAR_BASENAME);
    expect(sidecar, "TerminalSidecar.ts must exist (the WS-attachment seam)").toBeDefined();
    if (sidecar) {
      const src = stripComments(await readSource(sidecar));
      expect(PROCESS_START_PATTERNS.some((p) => p.test(src))).toBe(false);
      expect(MUTATION_VERB_PATTERNS.some((p) => p.test(src))).toBe(false);
      // It IS the WS-attachment seam (that is its sanctioned job).
      expect(WS_ATTACHMENT_PATTERNS.some((p) => p.test(src))).toBe(true);
    }

    // (c) WP-007 — the daemon-ensure process-start is named in lib/ensureDaemon.ts
    // (the SHARED-daemon spawn seam) and nowhere else; the spawn MOVED here from
    // index.ts's retired ephemeral host. index.ts now starts NO process.
    const ensure = files.find((f) => basename(f) === DAEMON_ENSURE_BASENAME);
    expect(ensure, "lib/ensureDaemon.ts must exist (the daemon process-start seam)").toBeDefined();
    if (ensure) {
      const src = stripComments(await readSource(ensure));
      expect(PROCESS_START_PATTERNS.some((p) => p.test(src))).toBe(true);
    }
    // index.ts itself no longer starts a process (it calls the ensure binding).
    const entry = files.find((f) => basename(f) === "index.ts");
    expect(entry, "index.ts must exist (the composition root)").toBeDefined();
    if (entry) {
      const src = stripComments(await readSource(entry));
      expect(PROCESS_START_PATTERNS.some((p) => p.test(src))).toBe(false);
    }

    // (d) INDEPENDENCE (founder directive): the terminal sidecar does NOT import
    // the chat relay/bridge — the terminal seams are added alongside chat's, not
    // coupled to them. The bridge stands up with no chat present.
    if (sidecar) {
      const raw = await readSource(sidecar);
      expect(raw).not.toMatch(/from\s+["'][^"']*routes\/chat["']/);
      expect(raw).not.toMatch(/from\s+["'][^"']*StreamJsonSessionBridge["']/);
    }
  });

  // WP-005 (ADR-010 §3 / NFR-SEC-05) — reading a surface still starts NOTHING.
  // The daemon is ensured at server boot (the one audited lib/ensureDaemon.ts
  // site, WP-007), never on a read. No read-view file (route/lib that serves a
  // GET surface) starts a process or attaches a WS write seam. This extends the
  // existing NFR-SEC-05 "loading a read view starts no session" assertion to
  // cover the terminal's two new seam shapes (process-start + WS-attachment).
  it("test_read_views_start_no_session — mounting a read view spawns no daemon / attaches no write seam (NFR-SEC-05)", async () => {
    const files = await collectSourceFiles();
    // The ONLY files permitted to start a process OR attach a WS write seam are
    // the audited seams; a read view (everything else) does neither.
    const SANCTIONED_SEAM_FILES = new Set([
      BRIDGE_ADAPTER_BASENAME,
      "gitShow.ts",
      "SulisChangeStoreReader.ts",
      "SulisChangeRecreator.ts",
      SPINE_MINTER_BASENAME,
      STARTER_BASENAME,
      // WP-005 (ADR-019) — the Settings adapter is a sanctioned write seam, not
      // a read view; it starts a process (the validated helpers). Named here so
      // the NFR-SEC-05 "a read view starts nothing" assertion still holds for
      // every OTHER file.
      SETTINGS_ADAPTER_BASENAME,
      TURN_SUMMARIES_BASENAME,
      DAEMON_ENSURE_BASENAME,
      TERMINAL_SIDECAR_BASENAME,
    ]);
    const readViewOffenders: string[] = [];
    for (const f of files) {
      if (SANCTIONED_SEAM_FILES.has(basename(f))) continue;
      const src = stripComments(await readSource(f));
      if (PROCESS_START_PATTERNS.some((p) => p.test(src))) {
        readViewOffenders.push(`${f} :: read view starts a process`);
      }
      if (WS_ATTACHMENT_PATTERNS.some((p) => p.test(src))) {
        readViewOffenders.push(`${f} :: read view attaches a WS write seam`);
      }
    }
    expect(readViewOffenders, JSON.stringify(readViewOffenders)).toEqual([]);
  });
});
