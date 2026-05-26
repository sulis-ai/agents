// WP-016 — E2E fixture seeder.
//
// Builds, on disk, the minimal but real environment the cockpit reads:
//
//   1. A SULIS_STATE_DIR holding one change record at
//      {stateDir}/changes/{changeId}/change.json (+ state.json stage
//      overlay) — the exact layout _change_state.py enumerates.
//   2. A git-init'd worktree with src/index.ts committed (the diff base)
//      plus an uncommitted edit so the diff has something to show.
//   3. A CLAUDE_PROJECTS_DIR holding one transcript JSONL (user +
//      assistant text+tool-use + system) under the mangled-cwd dir the
//      transcript locator expects.
//
// Idempotent: seed() wipes and recreates the target dirs, so re-runs
// produce identical state (WP-016 Blue requirement). Nothing is committed
// as a binary blob — everything is generated from these literals.

import { mkdtemp, mkdir, writeFile, rm, realpath } from "node:fs/promises";
import { readFileSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

import { mangleCwd } from "../../server/lib/mangleCwd";

/**
 * Path of the handoff file the seeder writes and the server wrapper +
 * Playmaker specs read. A single, stable location in the OS temp dir.
 */
export const HANDOFF_PATH = join(tmpdir(), "cockpit-e2e-handoff.json");

export interface Handoff {
  stateDir: string;
  projectsDir: string;
  worktree: string;
  changeId: string;
  handle: string;
  fileAbsolutePath: string;
}

export interface SeededFixture {
  /** SULIS_STATE_DIR — pass to the server env. */
  stateDir: string;
  /** CLAUDE_PROJECTS_DIR — pass to the server env. */
  projectsDir: string;
  /** The seeded change's worktree (also where the diff lives). */
  worktree: string;
  /** The seeded change id (matches the change-card handle below). */
  changeId: string;
  /** The seeded change handle (visible on the card). */
  handle: string;
  /** Absolute path of the file the happy-path opens. */
  fileAbsolutePath: string;
  /** Tear everything down (called from Playwright globalTeardown). */
  cleanup: () => Promise<void>;
}

const CHANGE_ID = "01E2ESMOKE0000000000000000";
const HANDLE = "CH-01E2ES";

function git(cwd: string, args: string[]): void {
  const res = spawnSync("git", args, { cwd, encoding: "utf8" });
  if (res.status !== 0) {
    throw new Error(
      `git ${args.join(" ")} failed (status ${res.status}): ${res.stderr}`,
    );
  }
}

/**
 * Create the seeded fixture in fresh temp dirs and return its handles.
 * The caller is responsible for exporting stateDir/projectsDir into the
 * server's env before booting it.
 */
export async function seed(): Promise<SeededFixture> {
  const stateDir = await mkdtemp(join(tmpdir(), "cockpit-e2e-state-"));
  const projectsDir = await mkdtemp(join(tmpdir(), "cockpit-e2e-projects-"));
  const worktreeBase = await mkdtemp(join(tmpdir(), "cockpit-e2e-wt-"));
  // realpath so the transcript-locator's cwd match (which realpaths) lines up
  // on macOS where /tmp is a symlink to /private/tmp.
  const worktree = await realpath(worktreeBase);

  // --- worktree: a tiny git repo with a committed base + an edit --------
  await mkdir(join(worktree, "src"), { recursive: true });
  const fileRel = join("src", "index.ts");
  await writeFile(join(worktree, fileRel), "export const x = 1;\n", "utf8");
  await writeFile(join(worktree, "README.md"), "# e2e demo\n", "utf8");

  git(worktree, ["init", "-q", "-b", "main"]);
  git(worktree, ["config", "user.email", "e2e@example.com"]);
  git(worktree, ["config", "user.name", "WP-016 e2e"]);
  git(worktree, ["config", "commit.gpgsign", "false"]);
  git(worktree, ["add", "."]);
  git(worktree, ["commit", "-q", "-m", "base"]);
  const baseSha = spawnSync("git", ["rev-parse", "HEAD"], {
    cwd: worktree,
    encoding: "utf8",
  }).stdout.trim();

  // Uncommitted edit so the diff shows a changed line.
  await writeFile(join(worktree, fileRel), "export const x = 2;\n", "utf8");

  // --- change store: change.json + state.json ---------------------------
  const changeDir = join(stateDir, "changes", CHANGE_ID);
  await mkdir(changeDir, { recursive: true });
  await writeFile(
    join(changeDir, "change.json"),
    JSON.stringify(
      {
        change_id: CHANGE_ID,
        handle: HANDLE,
        slug: "e2e-smoke",
        primitive: "create",
        branch: "change/e2e-smoke",
        worktree_path: worktree,
        intent: "end-to-end smoke fixture",
        base_branch: "main",
        base_sha: baseSha,
        created_at: "2026-05-26T00:00:00Z",
        updated_at: "2026-05-26T00:00:00Z",
        stage: "design",
      },
      null,
      2,
    ),
    "utf8",
  );
  await writeFile(
    join(changeDir, "state.json"),
    JSON.stringify({ stage: "design", history: [] }, null, 2),
    "utf8",
  );

  // --- transcript: one JSONL under the mangled-cwd projects dir ---------
  const projDir = join(projectsDir, mangleCwd(worktree));
  await mkdir(projDir, { recursive: true });
  const transcript =
    [
      JSON.stringify({
        type: "user",
        uuid: "u1",
        timestamp: "2026-05-26T00:00:00Z",
        cwd: worktree,
        message: { role: "user", content: "Walk me through the change." },
      }),
      JSON.stringify({
        type: "assistant",
        uuid: "a1",
        timestamp: "2026-05-26T00:00:01Z",
        cwd: worktree,
        message: {
          role: "assistant",
          content: [
            { type: "text", text: "Here is what I changed." },
            {
              type: "tool_use",
              id: "tu1",
              name: "Read",
              input: { file_path: "src/index.ts" },
            },
          ],
        },
      }),
      JSON.stringify({
        type: "system",
        uuid: "s1",
        timestamp: "2026-05-26T00:00:02Z",
        cwd: worktree,
        subtype: "ack",
        content: "ok",
      }),
    ].join("\n") + "\n";
  await writeFile(join(projDir, "e2e-session.jsonl"), transcript, "utf8");

  return {
    stateDir,
    projectsDir,
    worktree,
    changeId: CHANGE_ID,
    handle: HANDLE,
    fileAbsolutePath: join(worktree, fileRel),
    cleanup: async () => {
      await rm(stateDir, { recursive: true, force: true });
      await rm(projectsDir, { recursive: true, force: true });
      await rm(worktree, { recursive: true, force: true });
    },
  };
}

/**
 * Idempotent: if the handoff already exists, return it; otherwise seed a
 * fresh fixture and write the handoff. Called by BOTH global-setup and the
 * server wrapper, so the boot order (Playwright starts webServers and
 * globalSetup in a version-dependent order) cannot leave the server without
 * its seeded dirs. Whichever runs first does the seeding; the other reads.
 */
export async function ensureSeeded(): Promise<Handoff> {
  if (existsSync(HANDOFF_PATH)) {
    return JSON.parse(readFileSync(HANDOFF_PATH, "utf8")) as Handoff;
  }
  const fx = await seed();
  const handoff: Handoff = {
    stateDir: fx.stateDir,
    projectsDir: fx.projectsDir,
    worktree: fx.worktree,
    changeId: fx.changeId,
    handle: fx.handle,
    fileAbsolutePath: fx.fileAbsolutePath,
  };
  await writeFile(HANDOFF_PATH, JSON.stringify(handoff, null, 2), "utf8");
  return handoff;
}

/** Read the handoff written by {@link ensureSeeded}. */
export function readHandoffSync(): Handoff {
  return JSON.parse(readFileSync(HANDOFF_PATH, "utf8")) as Handoff;
}
