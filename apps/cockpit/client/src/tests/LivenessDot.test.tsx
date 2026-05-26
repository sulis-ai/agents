// WP-012 — <LivenessDot> tests.
//
// Four states per WP Contract + ADR-005 + TDD §8:
//   - running              → green dot, "Claude session running"
//   - running + terminal   → amber dot, "Terminal alive — Claude state unknown"
//   - not-running          → grey dot, "Not running"
//   - unknown              → neutral badge, "Unknown" + reason on hover (title attr)

import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { LivenessDot } from "../components/LivenessDot";

describe("<LivenessDot>", () => {
  it("renders running with green state + 'Claude session running' label", () => {
    const { getByRole } = render(
      <LivenessDot liveness={{ status: "running", pid: 1234 }} />,
    );
    const dot = getByRole("status");
    expect(dot.getAttribute("data-state")).toBe("running");
    expect(dot.getAttribute("aria-label")).toBe("Claude session running");
  });

  it("renders terminal-running with amber state + terminal label", () => {
    const { getByRole } = render(
      <LivenessDot
        liveness={{ status: "running", pid: 1234 }}
        pidKind="terminal"
      />,
    );
    const dot = getByRole("status");
    expect(dot.getAttribute("data-state")).toBe("terminal");
    expect(dot.getAttribute("aria-label")).toBe(
      "Terminal alive — Claude state unknown",
    );
  });

  it("renders not-running with grey state + 'Not running' label", () => {
    const { getByRole } = render(
      <LivenessDot liveness={{ status: "not-running" }} />,
    );
    const dot = getByRole("status");
    expect(dot.getAttribute("data-state")).toBe("not-running");
    expect(dot.getAttribute("aria-label")).toBe("Not running");
  });

  it("renders unknown with neutral state + reason in the title attribute", () => {
    const { getByRole } = render(
      <LivenessDot
        liveness={{ status: "unknown", reason: "no session record" }}
      />,
    );
    const dot = getByRole("status");
    expect(dot.getAttribute("data-state")).toBe("unknown");
    expect(dot.getAttribute("aria-label")).toBe("Unknown");
    expect(dot.getAttribute("title")).toBe("no session record");
  });
});
