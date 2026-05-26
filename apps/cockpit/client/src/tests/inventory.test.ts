// WP-011 — inventory check: apiGet is the only fetch caller in
// client/src.
//
// Per the WP Contract's Blue checklist: "apiGet is the only fetch
// caller in the client. Inventory grep test: any other fetch( is a
// violation." This guards against future WPs sprouting ad-hoc fetch
// calls and bypassing the single error-shape funnel.
//
// Implementation: walk client/src/**/*.{ts,tsx} (excluding tests) and
// flag any `fetch(` occurrence outside api/client.ts.

import { describe, it, expect } from "vitest";
import { promises as fs } from "node:fs";
import path from "node:path";

const ROOT = path.resolve(__dirname, "..");
const FETCH_OK_FILE = path.resolve(ROOT, "api/client.ts");

async function walk(dir: string): Promise<string[]> {
  const out: string[] = [];
  const entries = await fs.readdir(dir, { withFileTypes: true });
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      out.push(...(await walk(full)));
    } else if (
      entry.isFile() &&
      (entry.name.endsWith(".ts") || entry.name.endsWith(".tsx"))
    ) {
      out.push(full);
    }
  }
  return out;
}

describe("inventory — fetch caller funnel", () => {
  it("only api/client.ts calls fetch directly", async () => {
    const files = await walk(ROOT);
    const offenders: Array<{ file: string; lines: string[] }> = [];
    for (const file of files) {
      // Tests are allowed to use fetch (vi.spyOn etc.).
      if (file.includes(`${path.sep}tests${path.sep}`)) continue;
      if (file === FETCH_OK_FILE) continue;
      const src = await fs.readFile(file, "utf8");
      const lines = src.split(/\r?\n/);
      const matches = lines.filter((line) => /\bfetch\s*\(/.test(line));
      if (matches.length > 0) {
        offenders.push({ file: path.relative(ROOT, file), lines: matches });
      }
    }
    expect(offenders, JSON.stringify(offenders, null, 2)).toEqual([]);
  });
});
