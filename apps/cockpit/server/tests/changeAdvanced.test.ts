// Advanced view — pure-logic tests (classification + stop guards).
// The spawn-based calls (reveal / listChangeProcesses / branchUrl) are
// exercised live; here we pin the classification + the destructive guard.

import { describe, it, expect } from "vitest";
import { classifyProcess, stopProcess } from "../lib/changeAdvanced";

describe("classifyProcess", () => {
  it("recognises the terminal agent session", () => {
    expect(
      classifyProcess("claude --dangerously-skip-permissions --agent sulis hi").kind,
    ).toBe("session");
  });
  it("recognises a headless / web-chat agent", () => {
    expect(classifyProcess("claude -p prompt --resume abc").kind).toBe("agent");
  });
  it("recognises the preview server", () => {
    expect(classifyProcess("node .../vite client").kind).toBe("server");
  });
  it("falls back to a generic node process", () => {
    expect(classifyProcess("node some-script.js").kind).toBe("node");
  });
});

describe("stopProcess (guards)", () => {
  it("refuses an invalid pid", () => {
    expect(stopProcess(0).ok).toBe(false);
    expect(stopProcess(1).ok).toBe(false);
    expect(stopProcess(-5).ok).toBe(false);
    expect(stopProcess(NaN).ok).toBe(false);
  });
  it("refuses to stop the server's own process", () => {
    const r = stopProcess(process.pid);
    expect(r.ok).toBe(false);
    expect(r.error).toMatch(/own server/i);
  });
});
