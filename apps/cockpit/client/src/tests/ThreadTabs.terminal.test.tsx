// WP-008 — <ThreadTabs /> third "Terminal" tab.
//
// WP-008 extends the tab switcher from Chat | Files to Chat | Files |
// Terminal (the new third tab hosting <LiveTerminal/>). The active tab is
// still URL-driven (?tab=chat|files|terminal); only one panel mounts at a
// time (so xterm.js doesn't attach when the founder is on Chat/Files).
//
// References: WP-008 Contract (ThreadTabs extends TabId to
// "chat" | "files" | "terminal"); WP-013 (the original switcher).

import { describe, it, expect } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { ThreadTabs } from "../components/ThreadTabs";

function renderTabs(initialPath = "/c/abc") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <ThreadTabs
        chat={<div data-testid="slot-chat">chat slot</div>}
        files={<div data-testid="slot-files">files slot</div>}
        terminal={<div data-testid="slot-terminal">terminal slot</div>}
      />
    </MemoryRouter>,
  );
}

describe("<ThreadTabs /> — Terminal tab (WP-008)", () => {
  it("renders a Terminal tab button alongside Chat and Files", () => {
    renderTabs();
    expect(screen.getByRole("tab", { name: /chat/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /files/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /terminal/i })).toBeInTheDocument();
  });

  it("mounts only the Terminal panel when the Terminal tab is clicked", () => {
    renderTabs();
    fireEvent.click(screen.getByRole("tab", { name: /terminal/i }));

    expect(screen.getByTestId("slot-terminal")).toBeInTheDocument();
    // Inactive panels are NOT mounted (so xterm.js doesn't attach off-tab).
    expect(screen.queryByTestId("slot-chat")).not.toBeInTheDocument();
    expect(screen.queryByTestId("slot-files")).not.toBeInTheDocument();
  });

  it("opens directly on the Terminal tab when ?tab=terminal is in the URL", () => {
    renderTabs("/c/abc?tab=terminal");
    expect(screen.getByTestId("slot-terminal")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /terminal/i })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });
});
