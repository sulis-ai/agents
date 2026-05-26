// WP-016 — the read-only inventory gate, exercised from the Vitest suite.
//
// apps/cockpit/scripts/check-read-only.sh is the load-bearing read-only
// guarantee (TDD §13.7, ADR-003). The CI workflow runs it directly; this
// test runs the SAME script from the normal `npx vitest run` suite so the
// gate also fires locally and in branch-ci without needing Playwright
// browsers installed.
//
// Two assertions:
//   1. Against the real committed source, the script exits 0 (clean).
//   2. Against a temp tree with a planted violation, the script exits 1 —
//      proving the gate is a real failing-if-violated check, not a no-op.

import { describe, it, expect } from "vitest";
import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { mkdtemp, mkdir, writeFile, cp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";

const here = dirname(fileURLToPath(import.meta.url));
const cockpitRoot = join(here, "..", ".."); // apps/cockpit
const script = join(cockpitRoot, "scripts", "check-read-only.sh");

function runGate(cwdRoot: string) {
  // Invoke the script that lives under cwdRoot/scripts so the script's own
  // SCRIPT_DIR resolution points at the tree we want to scan.
  const scriptPath = join(cwdRoot, "scripts", "check-read-only.sh");
  return spawnSync("bash", [scriptPath], { encoding: "utf8" });
}

describe("read-only inventory gate script (TDD §13.7, ADR-003)", () => {
  it("exits 0 against the actual committed cockpit source", () => {
    const res = spawnSync("bash", [script], { encoding: "utf8" });
    expect(res.status, res.stdout + res.stderr).toBe(0);
    expect(res.stdout).toMatch(/Read-only inventory clean/);
  });

  it("--explain prints the rule catalogue and exits 0", () => {
    const res = spawnSync("bash", [script, "--explain"], { encoding: "utf8" });
    expect(res.status).toBe(0);
    expect(res.stdout).toMatch(/Filesystem writes/);
    expect(res.stdout).toMatch(/Non-loopback bind/);
  });

  it("exits 1 when a forbidden write API is planted in the tree", async () => {
    const sandbox = await mkdtemp(join(tmpdir(), "cockpit-readonly-"));
    try {
      // Reproduce the minimum shape the script needs: scripts/ (with the
      // gate) + a server/ source file containing a planted violation.
      await mkdir(join(sandbox, "scripts"), { recursive: true });
      await mkdir(join(sandbox, "server", "lib"), { recursive: true });
      await cp(script, join(sandbox, "scripts", "check-read-only.sh"));
      await writeFile(
        join(sandbox, "server", "lib", "evil.ts"),
        'import { writeFile } from "node:fs/promises";\n' +
          'export const go = () => writeFile("/tmp/x", "data");\n',
        "utf8",
      );
      const res = runGate(sandbox);
      expect(res.status).toBe(1);
      expect(res.stdout).toMatch(/VIOLATION \[filesystem write API\]/);
    } finally {
      await rm(sandbox, { recursive: true, force: true });
    }
  });

  it("exits 1 when a mutation HTTP verb is planted on the Express app", async () => {
    const sandbox = await mkdtemp(join(tmpdir(), "cockpit-readonly-"));
    try {
      await mkdir(join(sandbox, "scripts"), { recursive: true });
      await mkdir(join(sandbox, "server", "routes"), { recursive: true });
      await cp(script, join(sandbox, "scripts", "check-read-only.sh"));
      await writeFile(
        join(sandbox, "server", "routes", "bad.ts"),
        "export const reg = (app: any) => app.post('/x', () => {});\n",
        "utf8",
      );
      const res = runGate(sandbox);
      expect(res.status).toBe(1);
      expect(res.stdout).toMatch(/VIOLATION \[HTTP mutation verb\]/);
    } finally {
      await rm(sandbox, { recursive: true, force: true });
    }
  });

  it("ignores forbidden tokens that appear only inside comments", async () => {
    const sandbox = await mkdtemp(join(tmpdir(), "cockpit-readonly-"));
    try {
      await mkdir(join(sandbox, "scripts"), { recursive: true });
      await mkdir(join(sandbox, "server", "lib"), { recursive: true });
      await cp(script, join(sandbox, "scripts", "check-read-only.sh"));
      await writeFile(
        join(sandbox, "server", "lib", "documented.ts"),
        "// This module deliberately never calls fs.writeFile or app.post.\n" +
          "/* git commit is forbidden here; we only read. */\n" +
          "export const value = 1;\n",
        "utf8",
      );
      const res = runGate(sandbox);
      expect(res.status, res.stdout).toBe(0);
    } finally {
      await rm(sandbox, { recursive: true, force: true });
    }
  });
});
