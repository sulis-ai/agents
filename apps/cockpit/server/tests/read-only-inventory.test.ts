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

// Mutation HTTP verbs registered on an Express app/router.
const MUTATION_VERB_PATTERNS = [
  /\.post\s*\(/,
  /\.put\s*\(/,
  /\.patch\s*\(/,
  /\.delete\s*\(/,
];

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
  it("registers no POST / PUT / PATCH / DELETE routes", async () => {
    const files = await collectSourceFiles();
    expect(files.length).toBeGreaterThan(0);
    const offenders: string[] = [];
    for (const f of files) {
      const src = stripComments(await readSource(f));
      for (const pat of MUTATION_VERB_PATTERNS) {
        if (pat.test(src)) {
          offenders.push(`${f} :: ${pat}`);
        }
      }
    }
    expect(offenders).toEqual([]);
  });

  it("calls no filesystem-mutating APIs", async () => {
    const files = await collectSourceFiles();
    const offenders: string[] = [];
    for (const f of files) {
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
});
