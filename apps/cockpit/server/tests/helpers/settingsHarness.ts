// WP-010 — shared settings integration-test harness (the Blue extraction).
//
// Both the CF-07 conformance test (server/tests/settings.conformance.test.ts)
// and the e2e test (client/src/tests/Settings.e2e.test.tsx) need the SAME
// real-wiring scaffolding: a throwaway `mkdtemp` brain, a mock founder folder
// (± .git), a real Express app mounting the real `settingsRouter` over a real
// `SpineSettingsAdapter`, and the python3/scripts availability gate. At the
// 2-consumer threshold (EP-03) that scaffolding lives here, once, rather than
// being copied per test file. No behaviour added — this is a pure move of the
// helpers the two suites already shared.
//
// The vendored scripts are resolved repo-root-relative; callers pass their own
// distance to the repo root (this file is three levels under apps/cockpit/ and
// four under the repo root, but a CALLER's `import.meta.url` is what anchors
// the scripts dir, so we expose `resolveScriptsDir(repoRoot)` and let each
// caller compute its own root — keeping the anchor honest if a file moves).

import { mkdtempSync, existsSync, mkdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { execFileSync } from "node:child_process";
import express, { type Express } from "express";

import { settingsRouter } from "../../routes/settings";
import { SpineSettingsAdapter } from "../../adapters/SpineSettingsAdapter";

/** The vendored adapter/emitter scripts dir, under a repo root the caller
 *  computes from its own `import.meta.url` (so the anchor stays honest). */
export function resolveScriptsDir(repoRoot: string): string {
  return join(repoRoot, "plugins", "sulis", "scripts");
}

/** Is the real Python wiring available? `false` ⇒ the suite skips cleanly (not
 *  vacuously) on a bare checkout, matching the WP-005 adapter test. */
export function adapterAvailable(scriptsDir: string): boolean {
  let havePython = false;
  try {
    execFileSync("python3", ["--version"], { stdio: "ignore" });
    havePython = true;
  } catch {
    havePython = false;
  }
  const haveAdapter = existsSync(join(scriptsDir, "_entity_adapter_local.py"));
  return havePython && haveAdapter;
}

/**
 * A per-suite temp-dir registry. Construct one at module scope and call
 * `cleanup()` in `afterEach` — every `brain()`/`folder()` it minted is removed.
 * Owning the registry here keeps each test file's lifecycle a single line.
 */
export class TempDirs {
  private readonly dirs: string[] = [];

  /** A fresh `<state>/.brain/instances` dir (no `~/.sulis` pollution). */
  brain(): string {
    const dir = mkdtempSync(join(tmpdir(), "wp010-brain-"));
    this.dirs.push(dir);
    return join(dir, ".brain", "instances");
  }

  /** A fresh mock "founder folder" (optionally a real git repo). */
  folder(withGit: boolean): string {
    const dir = mkdtempSync(join(tmpdir(), "wp010-folder-"));
    this.dirs.push(dir);
    if (withGit) mkdirSync(join(dir, ".git"), { recursive: true });
    return dir;
  }

  /** Remove every temp dir minted so far. Call in `afterEach`. */
  cleanup(): void {
    while (this.dirs.length > 0) {
      const dir = this.dirs.pop();
      if (dir) rmSync(dir, { recursive: true, force: true });
    }
  }
}

/**
 * Build a real Express app mounting the REAL settings router over a REAL
 * `SpineSettingsAdapter` against the given temp brain — exactly the wiring
 * `app.ts` uses in production, but pointed at a throwaway brain. This is the
 * "real producer" half of CF-07 (no FakeSettingsStore).
 */
export function realSettingsApp(scriptsDir: string, baseDir: string): Express {
  const app = express();
  app.use(
    "/api/settings",
    settingsRouter({
      store: new SpineSettingsAdapter({ scriptsDir, baseDir }),
    }),
  );
  return app;
}

/** A convenience constructor for the real adapter (seed steps in the e2e). */
export function realAdapter(
  scriptsDir: string,
  baseDir: string,
): SpineSettingsAdapter {
  return new SpineSettingsAdapter({ scriptsDir, baseDir });
}
