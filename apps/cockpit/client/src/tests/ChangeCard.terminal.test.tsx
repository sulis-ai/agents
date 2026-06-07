// WP-009 — <ChangeCard> "Open terminal" action.
//
// The SUBSTITUTE-Strangle re-point at the UI surface: the card's "open
// terminal" action now opens the change's in-cockpit Terminal tab via
// launchChangeTerminal (the cockpit-rendered <LiveTerminal/> path), NOT the
// OS-window launcher (_terminal_launcher.py, now a deprecated fallback).
//
// The action is wired through an injected onOpenTerminal callback (WPF-03 —
// the card stays a pure presentational component; the page wires it to
// launchChangeTerminal). Clicking it must NOT also follow the card's <Link>
// (it stops the navigation so "open terminal" is distinct from "open change").
//
// References: WP-009 Contract (ChangeCard "open terminal" → launchChangeTerminal);
// contract §2.13.5.

import { describe, it, expect, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { ChangeCard } from "../components/ChangeCard";
import type { Change } from "../../../shared/api-types";

const fixture: Change = {
  changeId: "CH-01KTGY",
  handle: "CH-01KTGY",
  slug: "extend-terminal",
  primitive: "strangle",
  branch: "feat/x",
  worktreePath: "/w",
  intent: "Re-point the launcher",
  baseBranch: "dev",
  baseSha: null,
  createdAt: "2026-06-07T00:00:00Z",
  updatedAt: "2026-06-07T00:00:00Z",
  stage: "implement",
  liveness: { status: "not-running" },
};

function renderCard(onOpenTerminal: (changeId: string) => void) {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <ChangeCard change={fixture} onOpenTerminal={onOpenTerminal} />
    </MemoryRouter>,
  );
}

describe("<ChangeCard /> Open terminal action (WP-009)", () => {
  it("invokes onOpenTerminal with the change id (the cockpit-rendered path, not the OS-window launcher)", () => {
    const onOpenTerminal = vi.fn();
    renderCard(onOpenTerminal);

    fireEvent.click(screen.getByRole("button", { name: /open terminal/i }));

    expect(onOpenTerminal).toHaveBeenCalledWith("CH-01KTGY");
  });

  it("renders no terminal action when onOpenTerminal is omitted (existing usages unchanged)", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <ChangeCard change={fixture} />
      </MemoryRouter>,
    );

    expect(
      screen.queryByRole("button", { name: /open terminal/i }),
    ).not.toBeInTheDocument();
  });
});
