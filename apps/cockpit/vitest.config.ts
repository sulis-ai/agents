// WP-001 — Vitest config for the cockpit workspace.
//
// One config, two test environments:
//   - server/tests/**          → node
//   - client/src/**/tests/**   → jsdom (+ jest-dom matchers via setup)
// We use Vitest's projects feature so a single `npx vitest run` covers
// both surfaces with the right env per file.
//
// WP-016 — combined-run stability:
//   The combined `npx vitest run` runs the node-env server project and the
//   jsdom/Monaco client project together. We pin the `forks` pool so each
//   test file runs in its own child process — the boring, well-supported
//   isolation primitive — so the two environments cannot interfere under
//   parallel load. The root cause of the prior "socket hang up" flake (a
//   real socket bind in app.integration.test.ts) was also removed in favour
//   of in-process supertest; this pool setting is defence-in-depth.
//
// Flake #8 — real-subprocess starvation under parallel load:
//   Several server tests are REAL integration tests that cold-start python3
//   emitters / `sulis-change` CLIs via child_process (discovery.mint-real,
//   startChangeRunner.real, change-store-reader.adapter, …). With the fork
//   pool defaulting to one worker per CPU, 10 forks each spawning their own
//   subprocesses oversubscribe the machine; on CI's constrained 2-core runner
//   the contention is worse, so a subprocess can't make progress inside a
//   test's window and the test times out — deterministically in CI, flakily
//   locally. The cure is to stop oversubscribing: cap the worker pool so each
//   fork (and its spawned subprocess) gets real CPU. Half the host's cores is
//   the boring, well-supported headroom default; CI's small runners floor at
//   the `minForks` of 1. No assertion is weakened — the tests still drive the
//   real subprocesses and validate the real on-disk output.
//
//   Two levers, both boring and both leaving assertions untouched:
//     1. Cap the fork pool (below) so we never oversubscribe the host — each
//        fork and the subprocess it spawns get real CPU. On CI's 2-core runner
//        this floors to a single fork (fully sequential), the strongest guard.
//     2. Raise the global per-test + hook timeout off Vitest's 5s default.
//        5s cannot cover a cold python3 / `git clone` spawn, let alone several
//        under load; the real-subprocess suites also pin their own higher
//        `describe`-level budget. The work itself stays bounded inside each
//        adapter (execFile timeouts), so a runaway still fails fast.

import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { cpus } from "node:os";

// Leave headroom for the OS + the subprocesses the real integration tests
// spawn. Min 1 (CI's 2-core runner), and never more than the host has. An env
// override (VITEST_MAX_FORKS) lets CI pin the pool explicitly if needed.
const HOST_CAP = Math.max(1, Math.floor(cpus().length / 2));
const ENV_CAP = Number.parseInt(process.env.VITEST_MAX_FORKS ?? "", 10);
const MAX_FORKS = Number.isInteger(ENV_CAP) && ENV_CAP > 0 ? ENV_CAP : HOST_CAP;

// Global per-test / hook budget. Generous enough for a real subprocess spawn
// under parallel load; the real-subprocess suites raise it further themselves.
const TEST_TIMEOUT_MS = 30_000;

const poolOptions = {
  forks: {
    minForks: 1,
    maxForks: MAX_FORKS,
  },
};

export default defineConfig({
  test: {
    // Process-level isolation between the two environments.
    pool: "forks",
    poolOptions,
    testTimeout: TEST_TIMEOUT_MS,
    hookTimeout: TEST_TIMEOUT_MS,
    projects: [
      {
        plugins: [],
        test: {
          name: "server",
          environment: "node",
          include: ["server/tests/**/*.test.ts"],
          pool: "forks",
          poolOptions,
          testTimeout: TEST_TIMEOUT_MS,
          hookTimeout: TEST_TIMEOUT_MS,
        },
      },
      {
        plugins: [react()],
        test: {
          name: "client",
          environment: "jsdom",
          include: ["client/src/**/*.test.{ts,tsx}"],
          setupFiles: ["./client/src/tests/setup.ts"],
          globals: true,
          pool: "forks",
          poolOptions,
          testTimeout: TEST_TIMEOUT_MS,
          hookTimeout: TEST_TIMEOUT_MS,
        },
      },
    ],
  },
});
