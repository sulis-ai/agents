// WP-002 — reason-containment (MUC-3 / FR-32 / NFR-SEC-2, S-26).
//
// The health `reason` and the attention `reason` describe the SHAPE of
// what's happening — they are drawn from a fixed, enumerable set and NEVER
// interpolate transcript or reply text. This pins S-26: seed a change whose
// transcript holds markup / secret-looking text and assert no reason field
// on its feed row contains any of it.

import { describe, it, expect } from "vitest";
import request from "supertest";
import { mkdtemp, rm, mkdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { createApp } from "../app";
import { FakeChangeStoreReader } from "../adapters/FakeChangeStoreReader";
import { mangleCwd } from "../lib/mangleCwd";
import type { ChangeStoreRecord } from "../ports/ChangeStoreReader";
import type { Change } from "../../shared/api-types";

const SECRET = "sk-live-DEADBEEF-SECRET-TOKEN";
const MARKUP = "<script>alert('xss')</script>";

function record(overrides: Partial<ChangeStoreRecord> = {}): ChangeStoreRecord {
  return {
    changeId: "01SEC",
    handle: "CH-01SEC",
    slug: "secret-leak",
    primitive: "create",
    branch: "change/secret-leak",
    worktreePath: "/tmp/never-used",
    intent: "a change",
    baseBranch: "main",
    baseSha: "deadbeef",
    createdAt: "2026-05-01T00:00:00Z",
    updatedAt: "2026-05-02T00:00:00Z",
    stage: "implement",
    ...overrides,
  };
}

/** Seed a transcript whose body carries the secret + markup, located the
 *  way locateTranscripts expects (projectsDir/mangleCwd(wt)/*.jsonl with a
 *  first content record cwd === wt). */
async function seedTranscript(
  projectsDir: string,
  wt: string,
): Promise<void> {
  const dir = join(projectsDir, mangleCwd(wt));
  await mkdir(dir, { recursive: true });
  const lines = [
    JSON.stringify({
      type: "user",
      uuid: "u1",
      timestamp: "2026-05-02T10:00:00Z",
      cwd: wt,
      message: { role: "user", content: `please ${MARKUP} ${SECRET}?` },
    }),
    JSON.stringify({
      type: "assistant",
      uuid: "a1",
      timestamp: "2026-05-02T10:01:00Z",
      cwd: wt,
      message: {
        role: "assistant",
        content: [{ type: "text", text: `here is ${SECRET} and ${MARKUP}?` }],
      },
    }),
  ];
  await writeFile(join(dir, "session.jsonl"), lines.join("\n"), "utf8");
}

describe("reason-containment — no reason echoes change content (S-26)", () => {
  it("neither health.reason nor needsAttention.reason contains transcript markup/secret", async () => {
    const tmpState = await mkdtemp(join(tmpdir(), "cockpit-state-"));
    const tmpProjects = await mkdtemp(join(tmpdir(), "claude-projects-"));
    const wt = await mkdtemp(join(tmpdir(), "wt-sec-"));
    try {
      await seedTranscript(tmpProjects, wt);
      const reader = new FakeChangeStoreReader([
        record({ changeId: "01SEC", worktreePath: wt }),
      ]);
      const app = createApp({
        changeStore: reader,
        sulisStateDir: tmpState,
        claudeProjectsDir: tmpProjects,
      });
      const res = await request(app).get("/api/changes");
      expect(res.status).toBe(200);
      const row = (res.body as Change[])[0]!;

      const healthReason = row.health.reason ?? "";
      const attentionReason = row.needsAttention.reason ?? "";
      for (const reason of [healthReason, attentionReason]) {
        expect(reason).not.toContain(SECRET);
        expect(reason).not.toContain(MARKUP);
        expect(reason).not.toContain("script");
        expect(reason).not.toContain("sk-live");
      }
      // The whole serialized response carries the transcript nowhere either —
      // the feed never ships the reply body in any field.
      const serialized = JSON.stringify(row);
      expect(serialized).not.toContain(SECRET);
    } finally {
      await rm(tmpState, { recursive: true, force: true });
      await rm(tmpProjects, { recursive: true, force: true });
      await rm(wt, { recursive: true, force: true });
    }
  });
});
