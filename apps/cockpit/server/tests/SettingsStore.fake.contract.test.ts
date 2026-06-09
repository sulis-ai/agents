// WP-002 — FakeSettingsStore runs the shared SettingsStore contract (TDD §5.3,
// §6; MEA-08).
//
// The in-memory adapter is the simplest reference implementation of the port.
// It runs the SAME `settingsStoreContract` the real `SpineSettingsAdapter`
// (WP-005) will run — if a behaviour holds for the fake but not the adapter
// (or vice versa), the boundary-parity guarantee has broken.
//
// Lives under server/tests/ so the vitest server project glob
// (server/tests/**/*.test.ts) collects it. The port + the contract helper it
// imports live under server/ports/ per the WP Contract.
//
// The fake needs no real disk folder for the "non-repo folder" case: it tracks
// "does this path have .git" in memory, so `existingFolderNoGit` just returns a
// known path string the fake will report `present:false` for.

import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { settingsStoreContract } from "../ports/SettingsStore.contract";
import { FakeSettingsStore } from "../adapters/FakeSettingsStore";

settingsStoreContract(
  "FakeSettingsStore (in-memory)",
  async () => new FakeSettingsStore(),
  {
    // A real on-disk folder with no .git — the fake's `present` check is a real
    // existsSync against {path}/.git, so we hand it a freshly-minted temp dir.
    existingFolderNoGit: async () => mkdtemp(join(tmpdir(), "wp002-norepo-")),
  },
);
