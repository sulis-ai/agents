// WP-016 — Playwright global setup / teardown.
//
// Seeding is delegated to ensureSeeded() in fixtures/seed.ts, which is
// idempotent and writes a handoff JSON to a stable temp path. Both this
// globalSetup AND the server webServer wrapper call ensureSeeded(), so the
// fixture exists regardless of which Playwright starts first (the order of
// globalSetup vs webServer is version-dependent). Whichever runs first
// seeds; the rest read the handoff.

import { readFile, rm } from "node:fs/promises";

import { ensureSeeded, HANDOFF_PATH, type Handoff } from "./fixtures/seed";

export type { Handoff };

export default async function globalSetup(): Promise<void> {
  await ensureSeeded();
}

export async function readHandoff(): Promise<Handoff> {
  return JSON.parse(await readFile(HANDOFF_PATH, "utf8")) as Handoff;
}

export async function globalTeardown(): Promise<void> {
  try {
    const handoff = await readHandoff();
    await rm(handoff.stateDir, { recursive: true, force: true });
    await rm(handoff.projectsDir, { recursive: true, force: true });
    await rm(handoff.worktree, { recursive: true, force: true });
    await rm(HANDOFF_PATH, { force: true });
  } catch {
    // Handoff may not exist if setup failed — nothing to clean.
  }
}
