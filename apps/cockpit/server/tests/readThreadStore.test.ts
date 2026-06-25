// CH-GJ9KQR WP-006 — readThreadStore: read the cockpit raw transcript view
// from OUR durable ThreadStore (WP-002) instead of Claude's provider
// transcript files.
//
// The store is the local-first LocalThreadStore (ADR-002 hybrid): an
// append-only JSONL log on disk at
//   {sulisStateDir}/changes/{changeId}/threads/{changeId}.messages.jsonl
// — one ThreadMessage per line, offset-ordered (thread_contract.py
// `store_root_for_change` + `messages_record_filename`; one thread per
// change, ADR-004 → thread_id == changeId).
//
// readThreadStore reads that durable log and projects each ThreadMessage
// onto the SAME wire-shape `TranscriptMessage[]` the UI already renders,
// so the raw view is behaviour-preserving (no visual change, WP Contract).
//
// Discipline: real tmpdir, real fs I/O, no mocks — same convention as the
// locateTranscripts / parseTranscripts tests.

import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { mkdtemp, rm, mkdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { readThreadStore } from "../lib/readThreadStore";

// A ThreadMessage as the Python LocalThreadStore writes it to the JSONL log
// (dataclasses.asdict of thread_contract.ThreadMessage). The durable sink
// stamps id=`{thread_id}-{order}`, participant_type="studio_agent".
interface StoredThreadMessage {
  id: string;
  participant_id: string;
  participant_type: "studio_agent" | "user";
  content: string;
  role: "question" | "answer" | "observation" | "decision" | null;
  created_at: string;
  order: number;
}

function storedMessage(
  overrides: Partial<StoredThreadMessage> = {},
): StoredThreadMessage {
  return {
    id: "01CHG-0",
    participant_id: "studio-agent",
    participant_type: "studio_agent",
    content: "hello from our store",
    role: "observation",
    created_at: "2026-06-24T10:00:00.000Z",
    order: 0,
    ...overrides,
  };
}

async function seedStore(
  stateDir: string,
  changeId: string,
  messages: StoredThreadMessage[],
): Promise<void> {
  const threadsDir = join(stateDir, "changes", changeId, "threads");
  await mkdir(threadsDir, { recursive: true });
  const log =
    messages.map((m) => JSON.stringify(m)).join("\n") +
    (messages.length > 0 ? "\n" : "");
  await writeFile(
    join(threadsDir, `${changeId}.messages.jsonl`),
    log,
    "utf8",
  );
}

describe("readThreadStore", () => {
  let stateDir: string;

  beforeAll(async () => {
    stateDir = await mkdtemp(join(tmpdir(), "sulis-state-"));
  });

  afterAll(async () => {
    await rm(stateDir, { recursive: true, force: true });
  });

  it("projects stored ThreadMessages onto TranscriptMessage[]", async () => {
    const changeId = "01CHGREAD";
    await seedStore(stateDir, changeId, [
      storedMessage({
        id: `${changeId}-0`,
        content: "first message",
        order: 0,
        created_at: "2026-06-24T10:00:00.000Z",
      }),
      storedMessage({
        id: `${changeId}-1`,
        content: "second message",
        order: 1,
        created_at: "2026-06-24T10:00:01.000Z",
      }),
    ]);

    const messages = await readThreadStore(stateDir, changeId);

    expect(messages).toHaveLength(2);
    // The wire shape is TranscriptMessage: every message carries kind, uuid,
    // timestamp. The agent's durable content is an assistant-side record.
    expect(messages[0]?.uuid).toBe(`${changeId}-0`);
    expect(messages[0]?.timestamp).toBe("2026-06-24T10:00:00.000Z");
    expect(messages[1]?.uuid).toBe(`${changeId}-1`);
    // Content is carried through (the raw view renders our records).
    expect(JSON.stringify(messages[0])).toContain("first message");
    expect(JSON.stringify(messages[1])).toContain("second message");
  });

  it("projects a user participant onto a user-kind message, agent onto assistant", async () => {
    const changeId = "01CHGKIND";
    await seedStore(stateDir, changeId, [
      storedMessage({
        id: `${changeId}-0`,
        participant_type: "user",
        content: "founder said this",
        order: 0,
      }),
      storedMessage({
        id: `${changeId}-1`,
        participant_type: "studio_agent",
        content: "agent replied",
        order: 1,
      }),
    ]);

    const messages = await readThreadStore(stateDir, changeId);

    expect(messages[0]?.kind).toBe("user");
    expect(messages[1]?.kind).toBe("assistant");
    // user-kind carries text; assistant-kind carries a text block.
    expect(JSON.stringify(messages[0])).toContain("founder said this");
    expect(JSON.stringify(messages[1])).toContain("agent replied");
  });

  it("returns ordered messages (offset-ordered log, monotonic order)", async () => {
    const changeId = "01CHGORDER";
    await seedStore(stateDir, changeId, [
      storedMessage({ id: `${changeId}-0`, content: "a", order: 0 }),
      storedMessage({ id: `${changeId}-1`, content: "b", order: 1 }),
      storedMessage({ id: `${changeId}-2`, content: "c", order: 2 }),
    ]);

    const messages = await readThreadStore(stateDir, changeId);

    expect(messages.map((m) => m.uuid)).toEqual([
      `${changeId}-0`,
      `${changeId}-1`,
      `${changeId}-2`,
    ]);
  });

  it("returns [] when the store has no log for the change", async () => {
    const messages = await readThreadStore(stateDir, "01NOSTORE");
    expect(messages).toEqual([]);
  });

  it("skips malformed lines without throwing", async () => {
    const changeId = "01CHGBAD";
    const threadsDir = join(stateDir, "changes", changeId, "threads");
    await mkdir(threadsDir, { recursive: true });
    const log =
      [
        JSON.stringify(storedMessage({ id: `${changeId}-0`, order: 0 })),
        "{ this is not valid json",
        "",
        JSON.stringify(storedMessage({ id: `${changeId}-1`, order: 1 })),
      ].join("\n") + "\n";
    await writeFile(
      join(threadsDir, `${changeId}.messages.jsonl`),
      log,
      "utf8",
    );

    const messages = await readThreadStore(stateDir, changeId);
    expect(messages.map((m) => m.uuid)).toEqual([
      `${changeId}-0`,
      `${changeId}-1`,
    ]);
  });

  it("refuses a change id that is not a safe path component", async () => {
    // The store-root convention (thread_contract.validate_store_id) refuses a
    // traversing id; the TS reader must not build a path that escapes the
    // threads dir. A traversing id yields [] (treated as no store), never a read
    // outside {sulisStateDir}/changes/.
    const messages = await readThreadStore(stateDir, "../../etc");
    expect(messages).toEqual([]);
  });
});
