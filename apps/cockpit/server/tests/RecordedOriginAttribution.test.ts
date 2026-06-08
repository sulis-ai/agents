// WP-P13 — RecordedOriginAttribution adapter test (ADR-012/013).
//
// Builds a REAL world (no mocks at the git boundary — MEA-09): a temp git repo
// with files committed carrying a real `Sulis-Origin:` trailer (the stamp the
// executor / relay write at WP-P12), plus one file whose origin lives only in a
// `.sulis/origin/<sha>.json` sidecar (the trailer-can't-be-written fallback),
// plus one file with neither (→ unknown). Then it:
//   1. runs the SHARED OriginAttribution contract (the SAME suite the inferred
//      adapter passes — fake-vs-adapter parity, ADR-012), and
//   2. pins the recorded-specific invariant — every resolved result is
//      `attribution: "recorded"`, the exact origin read back from the stamp.
//
// File → expected category:
//   auto.txt    — committed with a `Sulis-Origin: autonomous; run=…` trailer
//   assist.txt  — committed with a `Sulis-Origin: assisted; …` trailer
//   sidecar.txt — committed plain; origin recorded in a sidecar json
//   stray.txt   — committed plain, no trailer, no sidecar → unknown

import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { mkdtemp, mkdir, writeFile, rm, realpath } from "node:fs/promises";
import { writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

import { RecordedOriginAttribution } from "../adapters/RecordedOriginAttribution";
import {
  runContract,
  type OriginContractWorld,
} from "./OriginAttribution.contract.test";

const CHANGE_ID = "01RECORDEDTESTCHANGE00000A";
const RUN_ID = "01RUNAUTONOMOUS0000000000A";
const CONVERSATION_ID = "session-recorded";

function git(cwd: string, args: string[], env?: NodeJS.ProcessEnv): void {
  const result = spawnSync("git", args, {
    cwd,
    encoding: "utf8",
    env: { ...process.env, ...env },
  });
  if (result.status !== 0) {
    throw new Error(
      `git ${args.join(" ")} failed (status ${result.status}): ${result.stderr}`,
    );
  }
}

/** Commit one file; `trailer` (when given) is appended as the message trailer. */
function commitFile(
  repo: string,
  path: string,
  content: string,
  trailer: string | null,
): void {
  writeFileSync(join(repo, path), content, "utf8");
  git(repo, ["add", path]);
  const message =
    trailer === null ? `add ${path}` : `add ${path}\n\n${trailer}`;
  git(repo, ["commit", "-q", "-m", message], {
    GIT_AUTHOR_NAME: "Tester",
    GIT_AUTHOR_EMAIL: "t@example.com",
    GIT_COMMITTER_NAME: "Tester",
    GIT_COMMITTER_EMAIL: "t@example.com",
  });
}

/** The abbreviated sha of the last commit that touched `path`. */
function lastSha(repo: string, path: string): string {
  const r = spawnSync("git", ["log", "-1", "--format=%h", "--", path], {
    cwd: repo,
    encoding: "utf8",
  });
  return r.stdout.trim();
}

describe("RecordedOriginAttribution (real world)", () => {
  let repo: string;

  beforeAll(async () => {
    repo = await realpath(await mkdtemp(join(tmpdir(), "recorded-adapter-")));
    git(repo, ["init", "-q", "-b", "main"]);
    git(repo, ["config", "commit.gpgsign", "false"]);

    commitFile(
      repo,
      "auto.txt",
      "auto\n",
      `Sulis-Origin: autonomous; run=${RUN_ID}; confidence=0.91`,
    );
    commitFile(
      repo,
      "assist.txt",
      "assist\n",
      `Sulis-Origin: assisted; conversation=${CONVERSATION_ID}; turn=3`,
    );
    // sidecar.txt — plain commit, origin recorded in a sidecar keyed by sha.
    commitFile(repo, "sidecar.txt", "sidecar\n", null);
    const sidecarSha = lastSha(repo, "sidecar.txt");
    const sidecarDir = join(repo, ".sulis", "origin");
    await mkdir(sidecarDir, { recursive: true });
    await writeFile(
      join(sidecarDir, `${sidecarSha}.json`),
      JSON.stringify({
        kind: "autonomous",
        run: RUN_ID,
        confidence: 0.5,
      }),
      "utf8",
    );
    // stray.txt — no trailer, no sidecar → unknown.
    commitFile(repo, "stray.txt", "stray\n", null);
  });

  afterAll(async () => {
    await rm(repo, { recursive: true, force: true });
  });

  function makeAttribution(): RecordedOriginAttribution {
    return new RecordedOriginAttribution({ worktreeRoot: repo });
  }

  // 1. The SHARED contract — same suite the inferred adapter passes (ADR-012).
  runContract("RecordedOriginAttribution", {
    setup: async (): Promise<OriginContractWorld> => ({
      attribution: makeAttribution(),
      changeId: CHANGE_ID,
      autonomousPath: "auto.txt",
      assistedPath: "assist.txt",
      unknownPath: "stray.txt",
    }),
  });

  // 2. The recorded-specific invariants.
  it("reads the autonomous trailer back EXACTLY with attribution=recorded", async () => {
    const origin = await makeAttribution().originFor(CHANGE_ID, "auto.txt");
    expect(origin.kind).toBe("autonomous");
    if (origin.kind !== "autonomous") throw new Error("narrowing");
    expect(origin.run.runId).toBe(RUN_ID);
    expect(origin.confidence).toBe(0.91);
    expect(origin.attribution).toBe("recorded");
  });

  it("reads the assisted trailer back EXACTLY with attribution=recorded", async () => {
    const origin = await makeAttribution().originFor(CHANGE_ID, "assist.txt");
    expect(origin.kind).toBe("assisted");
    if (origin.kind !== "assisted") throw new Error("narrowing");
    expect(origin.conversation.conversationId).toBe(CONVERSATION_ID);
    expect(origin.conversation.turn).toBe(3);
    expect(origin.attribution).toBe("recorded");
  });

  it("falls back to the sidecar when no trailer is present", async () => {
    const origin = await makeAttribution().originFor(CHANGE_ID, "sidecar.txt");
    expect(origin.kind).toBe("autonomous");
    if (origin.kind !== "autonomous") throw new Error("narrowing");
    expect(origin.run.runId).toBe(RUN_ID);
    expect(origin.confidence).toBe(0.5);
    expect(origin.attribution).toBe("recorded");
  });

  it("returns unknown (never throws) when neither trailer nor sidecar exists", async () => {
    const origin = await makeAttribution().originFor(CHANGE_ID, "stray.txt");
    expect(origin.kind).toBe("unknown");
    expect(origin.attribution).toBe("recorded");
  });

  it("change-level (no path) is an honest unknown", async () => {
    const origin = await makeAttribution().originFor(CHANGE_ID);
    expect(origin.kind).toBe("unknown");
    expect(origin.attribution).toBe("recorded");
  });
});
