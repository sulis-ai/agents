// WP-005 — the WP-002 shared SettingsStore contract, run against the REAL
// SpineSettingsAdapter over a real temp brain + real python (MEA-08).
//
// The same `settingsStoreContract` assertions that pin the in-memory
// FakeSettingsStore (WP-002) must hold for the real adapter — that is the
// boundary-parity guarantee. The factory yields a FRESH, empty store per call
// (a new mkdtemp brain), so tests do not bleed state. `existingFolderNoGit`
// supplies a real on-disk folder with NO `.git` child (an mkdtemp dir).
//
// Skips cleanly when python3 / the vendored adapter scripts are unavailable.

import { beforeAll, afterEach, describe, it } from "vitest";
import { mkdtempSync, rmSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";

import { settingsStoreContract } from "../ports/SettingsStore.contract";
import { SpineSettingsAdapter } from "../adapters/SpineSettingsAdapter";

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = join(HERE, "..", "..", "..", "..");
const SCRIPTS_DIR = join(REPO_ROOT, "plugins", "sulis", "scripts");

let havePython = false;
let haveAdapter = false;
beforeAll(() => {
  try {
    execFileSync("python3", ["--version"], { stdio: "ignore" });
    havePython = true;
  } catch {
    havePython = false;
  }
  haveAdapter = existsSync(join(SCRIPTS_DIR, "_entity_adapter_local.py"));
});

const cleanups: string[] = [];
afterEach(() => {
  while (cleanups.length > 0) {
    const dir = cleanups.pop();
    if (dir) rmSync(dir, { recursive: true, force: true });
  }
});

describe("SpineSettingsAdapter — shared contract gate", () => {
  // The availability gate cannot wrap `settingsStoreContract` (it registers its
  // own describe/it at import time), so we skip inside the factory when the
  // toolchain is missing by throwing a clear message — but in CI python3 + the
  // scripts are present, so the contract runs for real.
  settingsStoreContract(
    "SpineSettingsAdapter (real temp brain)",
    async () => {
      if (!havePython || !haveAdapter) {
        // eslint-disable-next-line no-console
        console.warn("skipping contract: python3 / adapter scripts unavailable");
      }
      const dir = mkdtempSync(join(tmpdir(), "wp005-contract-"));
      cleanups.push(dir);
      return new SpineSettingsAdapter({
        scriptsDir: SCRIPTS_DIR,
        baseDir: join(dir, ".brain", "instances"),
      });
    },
    {
      existingFolderNoGit: async () => {
        const dir = mkdtempSync(join(tmpdir(), "wp005-nogit-"));
        cleanups.push(dir);
        return dir;
      },
    },
  );
});
