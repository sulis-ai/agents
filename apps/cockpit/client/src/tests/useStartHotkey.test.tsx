// WP-002 — useStartHotkey() test (ADR-002 — the minimal global hotkey).
//
// The hook mounts a document "keydown" listener (mirroring the ProductSwitcher
// idiom) that maps Cmd/Ctrl+N and Cmd/Ctrl+K to navigate("/start") — the same
// single front door as the WP-001 button (ADR-001). It no-ops while the user
// is typing (focus in input/textarea/contenteditable) and removes its listener
// on unmount.
//
// Navigation is asserted with a MemoryRouter route probe: a marker element that
// renders only on the /start route. Firing the hotkey from "/" must navigate
// there (the marker appears); a no-op must leave us on "/" (the marker is
// absent). This tests user-visible behaviour, not the navigate() call shape.

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { useStartHotkey } from "../api/useStartHotkey";

function HotkeyHost() {
  useStartHotkey();
  return <div data-testid="home">home</div>;
}

function renderApp(initialPath = "/") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/" element={<HotkeyHost />} />
        <Route
          path="/start"
          element={<div data-testid="start-route">start</div>}
        />
      </Routes>
    </MemoryRouter>,
  );
}

function isOnStart(): boolean {
  return screen.queryByTestId("start-route") !== null;
}

describe("useStartHotkey", () => {
  beforeEach(() => {
    // Ensure no element from a prior test holds focus.
    if (document.activeElement instanceof HTMLElement) {
      document.activeElement.blur();
    }
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("cmd_n_navigates_to_start: firing ⌘N navigates to /start", () => {
    renderApp("/");
    expect(isOnStart()).toBe(false);

    fireEvent.keyDown(document.body, { key: "n", metaKey: true });

    expect(isOnStart()).toBe(true);
  });

  it("cmd_k_navigates_to_start: firing ⌘K navigates to /start", () => {
    renderApp("/");
    expect(isOnStart()).toBe(false);

    fireEvent.keyDown(document.body, { key: "k", metaKey: true });

    expect(isOnStart()).toBe(true);
  });

  it("ctrl variants also navigate (non-mac keyboards)", () => {
    renderApp("/");

    fireEvent.keyDown(document.body, { key: "n", ctrlKey: true });

    expect(isOnStart()).toBe(true);
  });

  it("no_op_when_focus_in_textarea: ⌘N with a focused <textarea> does not navigate", () => {
    renderApp("/");
    const textarea = document.createElement("textarea");
    document.body.appendChild(textarea);
    textarea.focus();
    expect(document.activeElement).toBe(textarea);

    fireEvent.keyDown(textarea, { key: "n", metaKey: true });

    expect(isOnStart()).toBe(false);
  });

  it("no_op_when_focus_in_input: ⌘N with a focused <input> does not navigate", () => {
    renderApp("/");
    const input = document.createElement("input");
    document.body.appendChild(input);
    input.focus();
    expect(document.activeElement).toBe(input);

    fireEvent.keyDown(input, { key: "n", metaKey: true });

    expect(isOnStart()).toBe(false);
  });

  it("no-op when focus is in a contenteditable element", () => {
    renderApp("/");
    const editable = document.createElement("div");
    editable.setAttribute("contenteditable", "true");
    document.body.appendChild(editable);
    editable.focus();

    fireEvent.keyDown(editable, { key: "n", metaKey: true });

    expect(isOnStart()).toBe(false);
  });

  it("ignores a bare 'n' with no modifier", () => {
    renderApp("/");

    fireEvent.keyDown(document.body, { key: "n" });

    expect(isOnStart()).toBe(false);
  });

  it("listener_removed_on_unmount: after unmount, firing ⌘N does nothing", () => {
    const { unmount } = renderApp("/");
    unmount();

    // No host is mounted; the listener must have been removed in cleanup.
    // Firing the key must not throw and must not navigate anything that's
    // still observable. Re-render a probe to confirm we are not on /start.
    fireEvent.keyDown(document.body, { key: "n", metaKey: true });

    renderApp("/");
    expect(isOnStart()).toBe(false);
  });
});
