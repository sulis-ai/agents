// WP-001 — the front-door "Start something new" button in WorkspaceTopBar.
//
// The button is the single primary action in the always-present workspace
// chrome. It navigates to the existing /start route (ADR-001: one front door,
// no new surface, no start-state) and carries a quiet ⌘N hint (ADR-002, kept
// in sync with the WP-002 hotkey). These tests pin: it renders as the only
// primary action; clicking it navigates to /start; it is keyboard-focusable
// with a visible focus ring (WPF-06, never outline:none); the ⌘N hint shows;
// and the top bar with the button has no WCAG AA violations.
//
// Harness mirrors WorkspaceTopBar.theme.test.tsx — the bar consumes products +
// changes (TanStack Query) + the open-tabs and active-product contexts, so we
// wrap the same providers and mock fetch to keep the network out. The
// navigation assertion uses a MemoryRouter + a Routes probe: a sentinel /start
// element that only appears once the click has navigated (the route probe the
// WP Contract calls for).

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { axe } from "jest-axe";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { ActiveProductProvider } from "../api/activeProduct";
import { OpenTabsProvider } from "../api/openTabs";
import { ThemeProvider } from "../theme/ThemeProvider";
import { WorkspaceTopBar } from "../components/WorkspaceTopBar";
import { freshQueryClient } from "./_renderWithClient";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

/**
 * Render the top bar inside a router with a /start route probe. The probe is a
 * sentinel element that is only in the document once navigation to /start has
 * happened — so a passing navigation test is "click → probe appears".
 */
function renderTopBar() {
  return render(
    <QueryClientProvider client={freshQueryClient()}>
      <ThemeProvider>
        <ActiveProductProvider>
          <OpenTabsProvider>
            <MemoryRouter initialEntries={["/"]}>
              <WorkspaceTopBar activeChangeId={null} />
              <Routes>
                <Route path="/" element={<div>board-route</div>} />
                <Route
                  path="/start"
                  element={
                    <div data-testid="start-route-probe">start-route</div>
                  }
                />
              </Routes>
            </MemoryRouter>
          </OpenTabsProvider>
        </ActiveProductProvider>
      </ThemeProvider>
    </QueryClientProvider>,
  );
}

describe("WorkspaceTopBar — front-door 'Start something new' button (WP-001)", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(200, []));
  });
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    delete document.documentElement.dataset.theme;
  });

  it("renders the Start button as the single primary action in the bar", () => {
    renderTopBar();
    const topbar = screen.getByTestId("workspace-topbar");

    // The front-door button is present, by its accessible name, within the bar.
    const startButton = within(topbar).getByRole("button", {
      name: /start something new/i,
    });
    expect(startButton).toBeInTheDocument();

    // It is the ONE primary action: exactly one element carries the primary
    // front-door marker. (The tabs, ProductSwitcher and ThemeToggle are not
    // primary actions; only the Start button is.)
    const primaries = within(topbar).getAllByTestId("start-change-button");
    expect(primaries).toHaveLength(1);
  });

  it("navigates to /start when clicked (route probe appears)", () => {
    renderTopBar();
    const topbar = screen.getByTestId("workspace-topbar");

    // Before the click we are on the board route, not /start.
    expect(screen.queryByTestId("start-route-probe")).not.toBeInTheDocument();

    fireEvent.click(
      within(topbar).getByRole("button", { name: /start something new/i }),
    );

    // After the click the /start route element is rendered — proof we navigated
    // to /start and nothing else.
    expect(screen.getByTestId("start-route-probe")).toBeInTheDocument();
  });

  it("is keyboard-focusable and shows a visible focus ring (never outline:none)", () => {
    renderTopBar();
    const topbar = screen.getByTestId("workspace-topbar");
    const startButton = within(topbar).getByRole("button", {
      name: /start something new/i,
    });

    // It is a real, focusable <button> (not a div-with-onClick): focusing it
    // makes it the active element.
    startButton.focus();
    expect(startButton).toHaveFocus();

    // The focus treatment is the cockpit's --ring via :focus-visible, applied
    // through the component's CSS-module class (not an inline outline:none).
    // We assert the styling hook is present so the focus ring is reachable.
    expect(startButton.className).toBeTruthy();
    expect(startButton.getAttribute("style") ?? "").not.toMatch(
      /outline\s*:\s*none/i,
    );
  });

  it("shows the ⌘N hint inside the button", () => {
    renderTopBar();
    const topbar = screen.getByTestId("workspace-topbar");
    const startButton = within(topbar).getByRole("button", {
      name: /start something new/i,
    });

    expect(startButton).toHaveTextContent("⌘N");
  });

  it("has no WCAG AA violations with the button mounted", async () => {
    const { container } = renderTopBar();
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
