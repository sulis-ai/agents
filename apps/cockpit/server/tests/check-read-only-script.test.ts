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
  // The script scans the whole cockpit source (~80+ files) and takes ~7-8s
  // locally; the default 5s test timeout is too tight for the real runtime,
  // so allow 30s. The gate itself passes — this only stops a slow scan from
  // being misreported as a failure.
  it("exits 0 against the actual committed cockpit source", () => {
    const res = spawnSync("bash", [script], { encoding: "utf8" });
    expect(res.status, res.stdout + res.stderr).toBe(0);
    expect(res.stdout).toMatch(/Read-only inventory clean/);
  }, 30000);

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

  // WP-005 (ADR-003) — the gate now allow-lists exactly the chat relay's
  // app.post and the SessionBridge adapter's process start, and adds a rule
  // flagging a process start anywhere else.
  it("allows app.post ONLY in the sanctioned chat relay file", async () => {
    const sandbox = await mkdtemp(join(tmpdir(), "cockpit-readonly-"));
    try {
      await mkdir(join(sandbox, "scripts"), { recursive: true });
      await mkdir(join(sandbox, "server", "routes"), { recursive: true });
      await cp(script, join(sandbox, "scripts", "check-read-only.sh"));
      // The relay file may register one mutation route.
      await writeFile(
        join(sandbox, "server", "routes", "chat.ts"),
        "export const reg = (app: any) => app.post('/api/changes/:id/chat', () => {});\n",
        "utf8",
      );
      const res = runGate(sandbox);
      expect(res.status, res.stdout + res.stderr).toBe(0);
    } finally {
      await rm(sandbox, { recursive: true, force: true });
    }
  });

  it("flags a process start OUTSIDE the sanctioned bridge adapter", async () => {
    const sandbox = await mkdtemp(join(tmpdir(), "cockpit-readonly-"));
    try {
      await mkdir(join(sandbox, "scripts"), { recursive: true });
      await mkdir(join(sandbox, "server", "lib"), { recursive: true });
      await cp(script, join(sandbox, "scripts", "check-read-only.sh"));
      await writeFile(
        join(sandbox, "server", "lib", "sneaky.ts"),
        'import { spawn } from "node:child_process";\n' +
          'export const go = () => spawn("claude", ["-p"]);\n',
        "utf8",
      );
      const res = runGate(sandbox);
      expect(res.status).toBe(1);
      expect(res.stdout).toMatch(/VIOLATION \[process start outside the sanctioned bridge\]/);
    } finally {
      await rm(sandbox, { recursive: true, force: true });
    }
  });

  it("allows the process start INSIDE the sanctioned bridge adapter", async () => {
    const sandbox = await mkdtemp(join(tmpdir(), "cockpit-readonly-"));
    try {
      await mkdir(join(sandbox, "scripts"), { recursive: true });
      await mkdir(join(sandbox, "server", "adapters"), { recursive: true });
      await cp(script, join(sandbox, "scripts", "check-read-only.sh"));
      await writeFile(
        join(sandbox, "server", "adapters", "StreamJsonSessionBridge.ts"),
        'import { spawn } from "node:child_process";\n' +
          'export const go = () => spawn("claude", ["-p"]);\n',
        "utf8",
      );
      const res = runGate(sandbox);
      expect(res.status, res.stdout + res.stderr).toBe(0);
    } finally {
      await rm(sandbox, { recursive: true, force: true });
    }
  });

  // ADR-015 (keep-the-gate-with-named-exception) — the four operator-action +
  // summary-cache exceptions are PATH-SCOPED, not blanket. Each test below
  // plants the same forbidden shape in (a) the sanctioned file → still passes,
  // and (b) some OTHER file → still trips the gate.

  it("allows a filesystem write ONLY in the sanctioned summary-cache lib (ADR-015)", async () => {
    const sandbox = await mkdtemp(join(tmpdir(), "cockpit-readonly-"));
    try {
      await mkdir(join(sandbox, "scripts"), { recursive: true });
      await mkdir(join(sandbox, "server", "lib"), { recursive: true });
      await cp(script, join(sandbox, "scripts", "check-read-only.sh"));
      await writeFile(
        join(sandbox, "server", "lib", "turnSummaries.ts"),
        'import { writeFile } from "node:fs/promises";\n' +
          'export const cache = () => writeFile("/tmp/x", "data");\n',
        "utf8",
      );
      const res = runGate(sandbox);
      expect(res.status, res.stdout + res.stderr).toBe(0);
    } finally {
      await rm(sandbox, { recursive: true, force: true });
    }
  });

  it("still flags a filesystem write in ANY other lib (the exception is path-scoped)", async () => {
    const sandbox = await mkdtemp(join(tmpdir(), "cockpit-readonly-"));
    try {
      await mkdir(join(sandbox, "scripts"), { recursive: true });
      await mkdir(join(sandbox, "server", "lib"), { recursive: true });
      await cp(script, join(sandbox, "scripts", "check-read-only.sh"));
      await writeFile(
        join(sandbox, "server", "lib", "notTurnSummaries.ts"),
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

  it("allows a `claude` spawn ONLY in the sanctioned summary-cache lib (ADR-015)", async () => {
    const sandbox = await mkdtemp(join(tmpdir(), "cockpit-readonly-"));
    try {
      await mkdir(join(sandbox, "scripts"), { recursive: true });
      await mkdir(join(sandbox, "server", "lib"), { recursive: true });
      await cp(script, join(sandbox, "scripts", "check-read-only.sh"));
      await writeFile(
        join(sandbox, "server", "lib", "turnSummaries.ts"),
        'import { spawn } from "node:child_process";\n' +
          'export const go = () => spawn("claude", ["-p"]);\n',
        "utf8",
      );
      const res = runGate(sandbox);
      expect(res.status, res.stdout + res.stderr).toBe(0);
    } finally {
      await rm(sandbox, { recursive: true, force: true });
    }
  });

  it("allows the two operator POST routes ONLY in the sanctioned advanced route (ADR-015)", async () => {
    const sandbox = await mkdtemp(join(tmpdir(), "cockpit-readonly-"));
    try {
      await mkdir(join(sandbox, "scripts"), { recursive: true });
      await mkdir(join(sandbox, "server", "routes"), { recursive: true });
      await cp(script, join(sandbox, "scripts", "check-read-only.sh"));
      await writeFile(
        join(sandbox, "server", "routes", "advanced.ts"),
        "export const reg = (router: any) => {\n" +
          "  router.post('/api/changes/:id/reveal', () => {});\n" +
          "  router.post('/api/changes/:id/processes/:pid/stop', () => {});\n" +
          "};\n",
        "utf8",
      );
      const res = runGate(sandbox);
      expect(res.status, res.stdout + res.stderr).toBe(0);
    } finally {
      await rm(sandbox, { recursive: true, force: true });
    }
  });

  it("still flags a POST route in ANY other route file (the exception is path-scoped)", async () => {
    const sandbox = await mkdtemp(join(tmpdir(), "cockpit-readonly-"));
    try {
      await mkdir(join(sandbox, "scripts"), { recursive: true });
      await mkdir(join(sandbox, "server", "routes"), { recursive: true });
      await cp(script, join(sandbox, "scripts", "check-read-only.sh"));
      await writeFile(
        join(sandbox, "server", "routes", "notAdvanced.ts"),
        "export const reg = (router: any) => router.post('/x', () => {});\n",
        "utf8",
      );
      const res = runGate(sandbox);
      expect(res.status).toBe(1);
      expect(res.stdout).toMatch(/VIOLATION \[HTTP mutation verb\]/);
    } finally {
      await rm(sandbox, { recursive: true, force: true });
    }
  });

  it("allows a non-zero process signal ONLY in the sanctioned stop-process lib (ADR-015)", async () => {
    const sandbox = await mkdtemp(join(tmpdir(), "cockpit-readonly-"));
    try {
      await mkdir(join(sandbox, "scripts"), { recursive: true });
      await mkdir(join(sandbox, "server", "lib"), { recursive: true });
      await cp(script, join(sandbox, "scripts", "check-read-only.sh"));
      await writeFile(
        join(sandbox, "server", "lib", "changeAdvanced.ts"),
        'export const stop = (pid: number) => process.kill(pid, "SIGTERM");\n',
        "utf8",
      );
      const res = runGate(sandbox);
      expect(res.status, res.stdout + res.stderr).toBe(0);
    } finally {
      await rm(sandbox, { recursive: true, force: true });
    }
  });

  it("still flags a non-zero process signal in ANY other lib (the exception is path-scoped)", async () => {
    const sandbox = await mkdtemp(join(tmpdir(), "cockpit-readonly-"));
    try {
      await mkdir(join(sandbox, "scripts"), { recursive: true });
      await mkdir(join(sandbox, "server", "lib"), { recursive: true });
      await cp(script, join(sandbox, "scripts", "check-read-only.sh"));
      await writeFile(
        join(sandbox, "server", "lib", "notChangeAdvanced.ts"),
        'export const kill = (pid: number) => process.kill(pid, "SIGKILL");\n',
        "utf8",
      );
      const res = runGate(sandbox);
      expect(res.status).toBe(1);
      expect(res.stdout).toMatch(/VIOLATION \[non-zero process signal\]/);
    } finally {
      await rm(sandbox, { recursive: true, force: true });
    }
  });

  it("--explain documents the four ADR-015 named exceptions", () => {
    const res = spawnSync("bash", [script, "--explain"], { encoding: "utf8" });
    expect(res.status).toBe(0);
    expect(res.stdout).toMatch(/server\/routes\/advanced\.ts \(ADR-015/);
    expect(res.stdout).toMatch(/server\/lib\/changeAdvanced\.ts \(ADR-015/);
    expect(res.stdout).toMatch(/server\/lib\/turnSummaries\.ts \(ADR-015/);
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
