// WP-003 — <AgentPicker> Claude ↔ Antigravity at the composer foot (AI-07/AI-03).
//
// The picker names the RUNNING provider in words (AI-07 honest identity), is a
// real menu (reuses the ProductControl primitive — no second popover, the Blue
// constraint), and a mid-session switch is GUARDED: it opens the AI-03 confirm
// ("applies to new work") and only on confirm calls PUT /provider.

import { describe, it, expect, vi } from "vitest";
import { render, within, fireEvent } from "@testing-library/react";
import { AgentPicker } from "../components/AgentPicker";

describe("<AgentPicker> names the running provider (AI-07)", () => {
  it("shows the running provider's friendly name on the trigger", () => {
    const { getByTestId } = render(
      <AgentPicker
        running="agy"
        selected="agy"
        sessionRunning={false}
        onSwitch={vi.fn()}
      />,
    );
    // agy → Antigravity, named in words on the trigger.
    expect(getByTestId("agent-picker-trigger").textContent).toMatch(/antigravity/i);
  });

  it("is a real menu with menuitemradio rows + aria-checked on the running one", () => {
    const { getByTestId } = render(
      <AgentPicker running="pty" selected="pty" sessionRunning={false} onSwitch={vi.fn()} />,
    );
    fireEvent.click(getByTestId("agent-picker-trigger"));
    const menu = getByTestId("agent-picker-menu");
    const rows = within(menu).getAllByRole("menuitemradio");
    expect(rows).toHaveLength(2);
    const checked = rows.filter((r) => r.getAttribute("aria-checked") === "true");
    expect(checked).toHaveLength(1);
    const checkedRow = checked[0]!;
    expect(checkedRow.getAttribute("aria-label") ?? checkedRow.textContent ?? "").toMatch(/claude/i);
  });
});

describe("<AgentPicker> mid-session switch is guarded (AI-03)", () => {
  it("switching while a session runs opens the confirm before any call", () => {
    const onSwitch = vi.fn();
    const { getByTestId, queryByTestId } = render(
      <AgentPicker running="pty" selected="pty" sessionRunning={true} onSwitch={onSwitch} />,
    );
    fireEvent.click(getByTestId("agent-picker-trigger"));
    const menu = getByTestId("agent-picker-menu");
    const antigravity = within(menu)
      .getAllByRole("menuitemradio")
      .find((r) => /antigravity/i.test(r.getAttribute("aria-label") ?? r.textContent ?? ""))!;
    fireEvent.click(antigravity);

    // The confirm gate appears; nothing committed yet.
    expect(getByTestId("agent-switch-confirm")).toBeTruthy();
    expect(onSwitch).not.toHaveBeenCalled();
    // The confirm wording is honest about "new work".
    expect(getByTestId("agent-switch-confirm").textContent).toMatch(/new work/i);
    // (sanity) the picker menu has closed behind the confirm
    expect(queryByTestId("agent-picker-menu")).toBeNull();
  });

  it("confirming the switch calls onSwitch(provider) exactly once", () => {
    const onSwitch = vi.fn();
    const { getByTestId } = render(
      <AgentPicker running="pty" selected="pty" sessionRunning={true} onSwitch={onSwitch} />,
    );
    fireEvent.click(getByTestId("agent-picker-trigger"));
    const antigravity = within(getByTestId("agent-picker-menu"))
      .getAllByRole("menuitemradio")
      .find((r) => /antigravity/i.test(r.getAttribute("aria-label") ?? r.textContent ?? ""))!;
    fireEvent.click(antigravity);
    fireEvent.click(getByTestId("agent-switch-confirm-yes"));
    expect(onSwitch).toHaveBeenCalledTimes(1);
    expect(onSwitch).toHaveBeenCalledWith("agy");
  });

  it("declining the switch leaves the running provider untouched", () => {
    const onSwitch = vi.fn();
    const { getByTestId } = render(
      <AgentPicker running="pty" selected="pty" sessionRunning={true} onSwitch={onSwitch} />,
    );
    fireEvent.click(getByTestId("agent-picker-trigger"));
    const antigravity = within(getByTestId("agent-picker-menu"))
      .getAllByRole("menuitemradio")
      .find((r) => /antigravity/i.test(r.getAttribute("aria-label") ?? r.textContent ?? ""))!;
    fireEvent.click(antigravity);
    fireEvent.click(getByTestId("agent-switch-confirm-no"));
    expect(onSwitch).not.toHaveBeenCalled();
  });
});

describe("<AgentPicker> no-session switch needs no confirm", () => {
  it("switching with no running session calls onSwitch directly", () => {
    const onSwitch = vi.fn();
    const { getByTestId, queryByTestId } = render(
      <AgentPicker running="pty" selected="pty" sessionRunning={false} onSwitch={onSwitch} />,
    );
    fireEvent.click(getByTestId("agent-picker-trigger"));
    const antigravity = within(getByTestId("agent-picker-menu"))
      .getAllByRole("menuitemradio")
      .find((r) => /antigravity/i.test(r.getAttribute("aria-label") ?? r.textContent ?? ""))!;
    fireEvent.click(antigravity);
    // No confirm gate when nothing is running.
    expect(queryByTestId("agent-switch-confirm")).toBeNull();
    expect(onSwitch).toHaveBeenCalledWith("agy");
  });
});
