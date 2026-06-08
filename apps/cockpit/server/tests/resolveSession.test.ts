// WP-005 — resolveSessionFor unit test (ADR-002, FR-N4).
//
// The production resolver composes signal-0 liveness + the transcript locator
// into the side-effect-free resolution decision. We seed a tmp state dir +
// projects dir on disk (the same shapes probeLiveness + locateTranscripts read)
// so the live/resumable/fresh branches are exercised WITHOUT a live agent. It
// starts no process and writes nothing — FR-N4.

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtemp, mkdir, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { resolveSessionFor } from "../lib/resolveSession";
import { mangleCwd } from "../lib/mangleCwd";

const CHANGE_ID = "01RESOLVEAAAAAAAAAAAAAAAAA";

let stateDir: string;
let projectsDir: string;
let worktreePath: string;

beforeEach(async () => {
  stateDir = await mkdtemp(join(tmpdir(), "wp005-state-"));
  projectsDir = await mkdtemp(join(tmpdir(), "wp005-projects-"));
  worktreePath = await mkdtemp(join(tmpdir(), "wp005-worktree-"));
});

afterEach(async () => {
  await rm(stateDir, { recursive: true, force: true });
  await rm(projectsDir, { recursive: true, force: true });
  await rm(worktreePath, { recursive: true, force: true });
});

async function seedSession(pid: number | null): Promise<void> {
  const dir = join(stateDir, "changes", CHANGE_ID);
  await mkdir(dir, { recursive: true });
  await writeFile(
    join(dir, "session.json"),
    JSON.stringify({
      change_id: CHANGE_ID,
      pid,
      pid_kind: "session",
      script_path: "",
      spawned_at: "",
    }),
    "utf8",
  );
}

async function seedTranscript(): Promise<void> {
  const dir = join(projectsDir, mangleCwd(worktreePath));
  await mkdir(dir, { recursive: true });
  await writeFile(
    join(dir, "session.jsonl"),
    JSON.stringify({ type: "user", cwd: worktreePath, text: "hi" }) + "\n",
    "utf8",
  );
}

describe("resolveSessionFor (FR-N4)", () => {
  it("resolves 'live' when the recorded pid is alive (this process)", async () => {
    await seedSession(process.pid); // our own pid is definitely alive
    const r = await resolveSessionFor(CHANGE_ID, {
      sulisStateDir: stateDir,
      claudeProjectsDir: projectsDir,
      worktreePath,
    });
    expect(r.kind).toBe("live");
    expect(r.session.changeId).toBe(CHANGE_ID);
    expect(r.session.cwd).toBe(worktreePath);
  });

  it("resolves 'resumable' when not live but a prior transcript exists", async () => {
    await seedSession(null); // no live pid
    await seedTranscript();
    const r = await resolveSessionFor(CHANGE_ID, {
      sulisStateDir: stateDir,
      claudeProjectsDir: projectsDir,
      worktreePath,
    });
    expect(r.kind).toBe("resumable");
    expect(r.session.lastSessionRef).toBeDefined();
  });

  it("resolves 'fresh' when there is no live session and no transcript", async () => {
    const r = await resolveSessionFor(CHANGE_ID, {
      sulisStateDir: stateDir,
      claudeProjectsDir: projectsDir,
      worktreePath,
    });
    expect(r.kind).toBe("fresh");
    expect(r.session.cwd).toBe(worktreePath);
  });

  it("carries the session.json change_id into the resolved session (binding identity)", async () => {
    await seedSession(process.pid);
    const r = await resolveSessionFor(CHANGE_ID, {
      sulisStateDir: stateDir,
      claudeProjectsDir: projectsDir,
      worktreePath,
    });
    expect(r.session.changeId).toBe(CHANGE_ID);
  });
});
