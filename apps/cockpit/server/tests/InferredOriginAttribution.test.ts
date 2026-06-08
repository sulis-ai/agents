// WP-P09 — InferredOriginAttribution adapter test (ADR-012).
//
// Builds a REAL world (no mocks at the git boundary — MEA-09): a temp git repo
// with three files committed at controlled author-dates, a `.brain` carrying one
// `lifecyclerun`, and a Claude Code transcript under the mangled projects dir.
// Then it:
//   1. runs the SHARED OriginAttribution contract (the same suite WP-P13's
//      recorded adapter will pass), and
//   2. pins the inferred-specific invariant — every result is
//      `attribution: "inferred"` — on top.
//
// File → expected category:
//   auto.txt    — committed at the run's `at` (inside the run window) → autonomous
//   assist.txt  — committed at a transcript turn's timestamp          → assisted
//   stray.txt   — committed years earlier, no run/turn nearby         → unknown

import { describe, it, expect, beforeAll, afterAll, vi } from "vitest";
import {
  mkdtemp,
  mkdir,
  writeFile,
  rm,
  realpath,
} from "node:fs/promises";
import { writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

import { InferredOriginAttribution } from "../adapters/InferredOriginAttribution";
import * as parseTranscriptsMod from "../lib/parseTranscripts";
import * as readBrainMod from "../lib/readBrain";
import { mangleCwd } from "../lib/mangleCwd";
import { deriveThreadId } from "../lib/threadIdentity";
import {
  runContract,
  type OriginContractWorld,
} from "./OriginAttribution.contract.test";

const CHANGE_ID = "01ORIGINTESTCHANGE0000000A";
const RUN_AT = "2026-06-02T12:00:00Z";
const TURN_AT = "2026-06-03T09:00:00Z";
const RUN_ID = "01RUNAUTONOMOUS0000000000A";

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

/** Commit one file with a fixed author + committer date (ISO). */
function commitFile(
  repo: string,
  path: string,
  content: string,
  isoDate: string,
  author: string,
): void {
  // author string "Name <email>" → split into name + email for git config args.
  const m = /^(.*)<(.+)>\s*$/.exec(author);
  const name = (m?.[1] ?? "Tester").trim();
  const email = (m?.[2] ?? "t@example.com").trim();
  writeFileSyncish(repo, path, content);
  git(repo, ["add", path]);
  git(
    repo,
    ["commit", "-q", "-m", `add ${path}`],
    {
      GIT_AUTHOR_DATE: isoDate,
      GIT_COMMITTER_DATE: isoDate,
      GIT_AUTHOR_NAME: name,
      GIT_AUTHOR_EMAIL: email,
      GIT_COMMITTER_NAME: name,
      GIT_COMMITTER_EMAIL: email,
    },
  );
}

// tiny sync writer (the test seeds fixtures, not the cockpit — allowed in tests).
function writeFileSyncish(repo: string, rel: string, content: string): void {
  writeFileSync(join(repo, rel), content, "utf8");
}

describe("InferredOriginAttribution (real world)", () => {
  let repo: string; // realpath-resolved worktree root
  let projectsDir: string;

  beforeAll(async () => {
    repo = await realpath(await mkdtemp(join(tmpdir(), "origin-adapter-")));

    git(repo, ["init", "-q", "-b", "main"]);
    git(repo, ["config", "commit.gpgsign", "false"]);

    // auto.txt — committed AT the run's timestamp → inside the run window.
    commitFile(repo, "auto.txt", "auto\n", RUN_AT, "Sulis Bot <bot@sulis.ai>");
    // assist.txt — committed AT a transcript turn timestamp → assisted.
    commitFile(
      repo,
      "assist.txt",
      "assist\n",
      TURN_AT,
      "Iain <iain@nivbow.com>",
    );
    // stray.txt — committed years before any run/turn → unknown.
    commitFile(
      repo,
      "stray.txt",
      "stray\n",
      "2020-01-01T00:00:00Z",
      "Iain <iain@nivbow.com>",
    );

    // Brain: one completed lifecyclerun at RUN_AT.
    const runDir = join(
      repo,
      ".brain",
      "instances",
      "product-development",
      "lifecyclerun",
    );
    await mkdir(runDir, { recursive: true });
    await writeFile(
      join(runDir, `${RUN_ID}.jsonld`),
      JSON.stringify({
        id: `dna:lifecyclerun:${RUN_ID}`,
        _run_id: RUN_ID,
        step_name: "implement",
        at: RUN_AT,
        outcome: "completed",
        confidence: 0.88,
        _workflow: "dna:workflow:WF1",
      }),
      "utf8",
    );

    // Transcript: a Claude Code session whose one turn lands at TURN_AT.
    projectsDir = await mkdtemp(join(tmpdir(), "origin-projects-"));
    const sessionDir = join(projectsDir, mangleCwd(repo));
    await mkdir(sessionDir, { recursive: true });
    const lines = [
      // The cwd-verification record (locateTranscripts checks cwd === repo).
      JSON.stringify({
        type: "user",
        uuid: "u0",
        timestamp: "2026-06-03T08:59:00Z",
        cwd: repo,
        message: { role: "user", content: "please make the assisted change" },
      }),
      // The assistant turn at TURN_AT — the turn we correlate assist.txt to.
      JSON.stringify({
        type: "assistant",
        uuid: "a1",
        timestamp: TURN_AT,
        cwd: repo,
        message: {
          role: "assistant",
          content: [
            { type: "text", text: "Done — I added the assisted change." },
          ],
        },
      }),
    ];
    await writeFile(
      join(sessionDir, "session-abc.jsonl"),
      `${lines.join("\n")}\n`,
      "utf8",
    );
  });

  afterAll(async () => {
    await rm(repo, { recursive: true, force: true });
    await rm(projectsDir, { recursive: true, force: true });
  });

  function makeAttribution(): InferredOriginAttribution {
    return new InferredOriginAttribution({
      worktreeRoot: repo,
      recordedWorktreePath: repo,
      claudeProjectsDir: projectsDir,
      // Tight windows so the fixtures correlate exactly as intended.
      runWindowMs: 60 * 60 * 1000, // 1 h
      turnWindowMs: 15 * 60 * 1000, // 15 min
    });
  }

  // 1. The shared contract — same suite the recorded adapter will pass (P13).
  runContract("InferredOriginAttribution", {
    setup: async (): Promise<OriginContractWorld> => ({
      attribution: makeAttribution(),
      changeId: CHANGE_ID,
      autonomousPath: "auto.txt",
      assistedPath: "assist.txt",
      unknownPath: "stray.txt",
    }),
  });

  // 2. The inferred-specific invariant: every result is attribution:"inferred".
  describe("honesty flag is always 'inferred'", () => {
    it("autonomous → inferred", async () => {
      const o = await makeAttribution().originFor(CHANGE_ID, "auto.txt");
      expect(o.kind).toBe("autonomous");
      expect(o.attribution).toBe("inferred");
    });
    it("assisted → inferred", async () => {
      const o = await makeAttribution().originFor(CHANGE_ID, "assist.txt");
      expect(o.kind).toBe("assisted");
      expect(o.attribution).toBe("inferred");
    });
    it("unknown → inferred", async () => {
      const o = await makeAttribution().originFor(CHANGE_ID, "stray.txt");
      expect(o.kind).toBe("unknown");
      expect(o.attribution).toBe("inferred");
    });
    it("autonomous carries the run's confidence", async () => {
      const o = await makeAttribution().originFor(CHANGE_ID, "auto.txt");
      if (o.kind !== "autonomous") throw new Error("expected autonomous");
      expect(o.confidence).toBe(0.88);
      expect(o.run.runId).toBe(RUN_ID);
    });
    it("assisted carries the conversation id + turn summary", async () => {
      const o = await makeAttribution().originFor(CHANGE_ID, "assist.txt");
      if (o.kind !== "assisted") throw new Error("expected assisted");
      // WP-004 (ADR-018 D2): the conversation id is now the SHARED `thread_`-
      // shaped id (the relay records the same), NOT the raw stem. This is the
      // intentional change the #23 fix documents — the OLD raw-stem expectation
      // was the bug that made the id mutate shape on flip likely→exact.
      expect(o.conversation.conversationId).toBe("thread_session-abc");
      expect(o.conversation.summary).toContain("assisted change");
    });
  });

  // PERF — the whole-change read attributes every file through ONE adapter
  // instance; transcripts must be parsed (and the brain walked) at most ONCE per
  // instance, not once per file. Without this the cost is O(files × transcripts)
  // and the endpoint times out for a large change (~117 files × ~40 transcripts).
  describe("indexes transcripts + runs ONCE per instance (not per file)", () => {
    it("parses transcripts once and walks the brain once across many files", async () => {
      const parseSpy = vi.spyOn(parseTranscriptsMod, "parseTranscripts");
      const brainSpy = vi.spyOn(readBrainMod, "readBrain");
      try {
        const attribution = makeAttribution();
        // Attribute every changed file through the SAME instance, as the route's
        // readOrigin does for the whole change.
        for (const path of ["auto.txt", "assist.txt", "stray.txt"]) {
          await attribution.originFor(CHANGE_ID, path);
        }
        expect(parseSpy).toHaveBeenCalledTimes(1);
        expect(brainSpy).toHaveBeenCalledTimes(1);
      } finally {
        parseSpy.mockRestore();
        brainSpy.mockRestore();
      }
    });
  });

  // WP-004 (reconcile, ADR-018 D2) — the inferred conversation id renders the
  // SAME `thread_`-shaped id the relay records (shared-helper parity, EP-03), so
  // a file's displayed conversation id does not change shape on flip
  // likely→exact. The id MUST come from `deriveThreadId` of the transcript stem,
  // NOT the raw stem. Fails until loadTurns routes through the shared helper.
  describe("reconcile (ADR-018 D2): inferred renders the shared thread_ id", () => {
    it("assisted conversation id equals deriveThreadId(stem) (NOT the raw stem)", async () => {
      const o = await makeAttribution().originFor(CHANGE_ID, "assist.txt");
      if (o.kind !== "assisted") throw new Error("expected assisted");
      // The session stem is "session-abc"; the displayed id must be the
      // `thread_`-shaped id the relay would record for the same session.
      expect(o.conversation.conversationId).toBe(deriveThreadId("session-abc"));
      expect(o.conversation.conversationId).toBe("thread_session-abc");
    });
  });
});

// WP-004 (#23 multi-session fix, ADR-018 D2) — a change spanning 2+ sessions
// must attribute each file to ITS OWN session's `thread_` id, with turns indexed
// 1-based WITHIN that transcript (not "first stem only across the merged
// stream"). A real two-transcript world: two sessions, each with one assistant
// turn at a distinct timestamp, each correlated to its own file.
//
// OLD (the #23 bug this pins as wrong): both files report the FIRST transcript's
// stem as the conversation id, and the second file's turn is index 2 in the
// MERGED stream.
// NEW (the fix): file-one → thread_(session-one), turn 1; file-two →
// thread_(session-two), turn 1 — two distinct thread ids, per-transcript turns.
describe("InferredOriginAttribution — multi-session (#23, ADR-018 D2)", () => {
  let repo: string;
  let projectsDir: string;

  const CHANGE = "01MULTISESSIONCHANGE00000A";
  const STEM_ONE = "session-one";
  const STEM_TWO = "session-two";
  const TURN_ONE_AT = "2026-06-03T09:00:00Z";
  const TURN_TWO_AT = "2026-06-04T14:00:00Z";

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

  function commitFile(rel: string, isoDate: string): void {
    writeFileSync(join(repo, rel), `${rel}\n`, "utf8");
    git(repo, ["add", rel]);
    git(repo, ["commit", "-q", "-m", `add ${rel}`], {
      GIT_AUTHOR_DATE: isoDate,
      GIT_COMMITTER_DATE: isoDate,
      GIT_AUTHOR_NAME: "Iain",
      GIT_AUTHOR_EMAIL: "iain@nivbow.com",
      GIT_COMMITTER_NAME: "Iain",
      GIT_COMMITTER_EMAIL: "iain@nivbow.com",
    });
  }

  /** Write one single-turn transcript (a user record + an assistant turn). */
  async function writeTranscript(
    sessionDir: string,
    stem: string,
    turnAt: string,
  ): Promise<void> {
    const userAt = new Date(Date.parse(turnAt) - 60_000).toISOString();
    const lines = [
      JSON.stringify({
        type: "user",
        uuid: `${stem}-u`,
        timestamp: userAt,
        cwd: repo,
        message: { role: "user", content: "please change a file" },
      }),
      JSON.stringify({
        type: "assistant",
        uuid: `${stem}-a`,
        timestamp: turnAt,
        cwd: repo,
        message: {
          role: "assistant",
          content: [{ type: "text", text: `Done in ${stem}.` }],
        },
      }),
    ];
    await writeFile(join(sessionDir, `${stem}.jsonl`), `${lines.join("\n")}\n`, "utf8");
  }

  beforeAll(async () => {
    repo = await realpath(await mkdtemp(join(tmpdir(), "origin-multisession-")));
    git(repo, ["init", "-q", "-b", "main"]);
    git(repo, ["config", "commit.gpgsign", "false"]);

    // one.txt committed at session-one's turn; two.txt at session-two's turn.
    commitFile("one.txt", TURN_ONE_AT);
    commitFile("two.txt", TURN_TWO_AT);

    projectsDir = await mkdtemp(join(tmpdir(), "origin-multisession-projects-"));
    const sessionDir = join(projectsDir, mangleCwd(repo));
    await mkdir(sessionDir, { recursive: true });
    await writeTranscript(sessionDir, STEM_ONE, TURN_ONE_AT);
    await writeTranscript(sessionDir, STEM_TWO, TURN_TWO_AT);
  });

  afterAll(async () => {
    await rm(repo, { recursive: true, force: true });
    await rm(projectsDir, { recursive: true, force: true });
  });

  function makeAttribution(): InferredOriginAttribution {
    return new InferredOriginAttribution({
      worktreeRoot: repo,
      recordedWorktreePath: repo,
      claudeProjectsDir: projectsDir,
      runWindowMs: 60 * 60 * 1000,
      turnWindowMs: 15 * 60 * 1000,
    });
  }

  it("attributes each file to its OWN session's thread_ id (two distinct ids)", async () => {
    const a = makeAttribution();
    const one = await a.originFor(CHANGE, "one.txt");
    const two = await a.originFor(CHANGE, "two.txt");
    if (one.kind !== "assisted") throw new Error("expected one.txt assisted");
    if (two.kind !== "assisted") throw new Error("expected two.txt assisted");

    expect(one.conversation.conversationId).toBe(deriveThreadId(STEM_ONE));
    expect(two.conversation.conversationId).toBe(deriveThreadId(STEM_TWO));
    // Two distinct sessions → two distinct thread ids (the #23 fix; OLD behaviour
    // reported the first stem for BOTH).
    expect(one.conversation.conversationId).not.toBe(
      two.conversation.conversationId,
    );
  });

  it("indexes turns 1-based WITHIN each transcript (not across the merged stream)", async () => {
    const a = makeAttribution();
    const one = await a.originFor(CHANGE, "one.txt");
    const two = await a.originFor(CHANGE, "two.txt");
    if (one.kind !== "assisted") throw new Error("expected one.txt assisted");
    if (two.kind !== "assisted") throw new Error("expected two.txt assisted");

    // Each transcript's single turn is turn 1 within ITS OWN transcript. OLD
    // behaviour indexed across the merged stream → two.txt's turn was 2.
    expect(one.conversation.turn).toBe(1);
    expect(two.conversation.turn).toBe(1);
  });
});
