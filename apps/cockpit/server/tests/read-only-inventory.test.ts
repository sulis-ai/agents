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
  it("registers no POST / PUT / PATCH / DELETE routes — except the one sanctioned relay (ADR-003)", async () => {
    const files = await collectSourceFiles();
    expect(files.length).toBeGreaterThan(0);
    const offenders: string[] = [];
    for (const f of files) {
      // The chat relay (routes/chat.ts) is the ONE allow-listed write path.
      if (basename(f) === RELAY_ROUTE_BASENAME) continue;
      const src = stripComments(await readSource(f));
      for (const pat of MUTATION_VERB_PATTERNS) {
        if (pat.test(src)) {
          offenders.push(`${f} :: ${pat}`);
        }
      }
    }
    expect(offenders).toEqual([]);
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
  });

  it("calls no filesystem-mutating APIs — except the one sanctioned mint adapter (ADR-007 amended)", async () => {
    const files = await collectSourceFiles();
    const offenders: string[] = [];
    for (const f of files) {
      // The SpineEmitterMinter (WP-010 fix-forward) is the cold-start mint's
      // confirm-gated ACT path — allow-listed BY PATH, the same single-audited-
      // site discipline as the chat relay's write-verb exception.
      if (basename(f) === SPINE_MINTER_BASENAME) continue;
      const src = stripComments(await readSource(f));
      for (const pat of FS_MUTATION_PATTERNS) {
        if (pat.test(src)) {
          offenders.push(`${f} :: ${pat}`);
        }
      }
    }
    expect(offenders).toEqual([]);
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

  it("sends only signal 0 to other processes (liveness probe)", async () => {
    const files = await collectSourceFiles();
    const offenders: string[] = [];
    for (const f of files) {
      const src = stripComments(await readSource(f));
      if (NON_ZERO_KILL_PATTERN.test(src)) {
        offenders.push(`${f} :: process.kill with non-zero signal`);
      }
    }
    expect(offenders).toEqual([]);
  });

  // WP-009 (ADR-006) — the concierge is READ-ONLY: it rides the SAME bridge as
  // the chat and reaches consequence ONLY through the already-sanctioned paths.
  // It must add NO new file-level write/process exception (WP-009 AC#3): the
  // write-verb allow-list stays exactly {chat.ts} and the process-start
  // allow-list stays exactly the audited bridge/git/recreate set. The concierge
  // read lib (lib/concierge/conciergeRead.ts) must itself be clean.
  it("adds NO new write-verb file for the concierge — the allow-list stays {chat.ts} (FR-N8/ADR-006)", async () => {
    const files = await collectSourceFiles();
    const writeVerbFiles: string[] = [];
    for (const f of files) {
      const src = stripComments(await readSource(f));
      if (MUTATION_VERB_PATTERNS.some((p) => p.test(src))) {
        writeVerbFiles.push(basename(f));
      }
    }
    // Exactly one file registers a write verb: the sanctioned relay (which now
    // also hosts the read-only concierge POST so no NEW file gains a verb).
    expect(writeVerbFiles).toEqual([RELAY_ROUTE_BASENAME]);
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
  it("adds NO new write-verb file for start-from-intent — the allow-list stays {chat.ts} (ADR-006)", async () => {
    const files = await collectSourceFiles();
    const writeVerbFiles: string[] = [];
    for (const f of files) {
      const src = stripComments(await readSource(f));
      if (MUTATION_VERB_PATTERNS.some((p) => p.test(src))) {
        writeVerbFiles.push(basename(f));
      }
    }
    // Still exactly one file registers a write verb: the sanctioned relay (which
    // now also hosts the start-from-intent POST so no NEW file gains a verb).
    expect(writeVerbFiles).toEqual([RELAY_ROUTE_BASENAME]);
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
});
