// WP-010 — bind-address invariant (TDD §13.1, ADR-002).
//
// The cockpit must bind to 127.0.0.1 (and optionally ::1). It must NOT
// bind to 0.0.0.0. The bind address is hard-coded; no env var changes it.
// This test asserts the invariant in three ways:
//
//   1. CONFIG.bindAddress === "127.0.0.1".
//   2. Inspecting the config module's source: no string literal
//      "0.0.0.0" appears anywhere in the server source tree (excluding
//      tests / docs).
//   3. CONFIG.bindAddress is FROZEN (Object.freeze) — assigning a new
//      value throws in strict mode, so future code cannot subvert it.

import { describe, it, expect } from "vitest";
import { readFile, readdir, stat } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { CONFIG } from "../config";

const here = dirname(fileURLToPath(import.meta.url));
const serverRoot = join(here, "..");

const SCANNED_DIRS = ["", "middleware", "routes", "lib", "adapters", "ports"];

async function walkTsFiles(dir: string): Promise<string[]> {
  let entries;
  try {
    entries = await readdir(dir, { withFileTypes: true });
  } catch {
    return [];
  }
  const out: string[] = [];
  for (const e of entries) {
    if (e.name.startsWith(".")) continue;
    if (e.isFile() && e.name.endsWith(".ts")) {
      out.push(join(dir, e.name));
    }
  }
  return out;
}

async function collect(): Promise<string[]> {
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
      if (sub === "") {
        const rel = f.substring(serverRoot.length + 1);
        if (rel.includes("/")) continue;
      }
      if (f.includes("/tests/")) continue;
      all.push(f);
    }
  }
  return all;
}

describe("bind address invariant (TDD §13.1, ADR-002)", () => {
  it("CONFIG.bindAddress is exactly '127.0.0.1'", () => {
    expect(CONFIG.bindAddress).toBe("127.0.0.1");
  });

  it("CONFIG is frozen so the bind address cannot be mutated at runtime", () => {
    expect(Object.isFrozen(CONFIG)).toBe(true);
  });

  it("no '0.0.0.0' literal appears anywhere in active server source", async () => {
    const files = await collect();
    expect(files.length).toBeGreaterThan(0);
    const offenders: string[] = [];
    for (const f of files) {
      const src = await readFile(f, "utf8");
      // Strip both line and block comments before scanning so docs that
      // mention the forbidden literal in prose don't trip the gate.
      // Block comments first; then line comments scanned per-line.
      const noBlock = src.replace(/\/\*[\s\S]*?\*\//g, "");
      const stripped = noBlock
        .split("\n")
        .map((line) => {
          const idx = line.indexOf("//");
          if (idx === -1) return line;
          if (idx > 0 && line[idx - 1] === ":") return line;
          return line.substring(0, idx);
        })
        .join("\n");
      if (stripped.includes("0.0.0.0")) {
        offenders.push(f);
      }
    }
    expect(offenders).toEqual([]);
  });
});
