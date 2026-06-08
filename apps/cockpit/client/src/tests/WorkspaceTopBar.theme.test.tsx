// CH-01KTHP (dark-mode re-fit) — the ThemeToggle is re-homed into the new
// tabbed workspace top bar.
//
// Background: dark mode (WP-004) originally mounted <ThemeToggle /> in the old
// <Shell /> top bar. #216 ("Autonomous Delivery Environment") replaced that
// layout with <WorkspaceShell /> + <WorkspaceTopBar /> and DELETED Shell.tsx,
// so the toggle lost its mount point. This test pins the toggle's new home:
// rendered inside the workspace top bar (top-right), reachable from every
// route (the top bar is persistent), keeping its accessibility (a labelled
// button with aria-pressed) and its behaviour (flips documentElement theme).
//
// The top bar consumes products + changes (TanStack Query) + the open-tabs
// context; the harness mirrors WorkspaceShell.test.tsx — providers wrapped,
// fetch mocked to keep the network out — PLUS the ThemeProvider the toggle
// consumes (mirrors App.tsx production composition).

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { axe } from "jest-axe";
import { MemoryRouter } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { ActiveProductProvider } from "../api/activeProduct";
import { OpenTabsProvider } from "../api/openTabs";
import { ThemeProvider } from "../theme/ThemeProvider";
import { WorkspaceTopBar } from "../components/WorkspaceTopBar";
import { stubMatchMedia } from "./helpers/stubMatchMedia";
// Reuse the shared QueryClient harness (EP-03) rather than re-rolling one.
import { freshQueryClient } from "./_renderWithClient";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function renderTopBar() {
  return render(
    <QueryClientProvider client={freshQueryClient()}>
      <ThemeProvider>
        <ActiveProductProvider>
          <OpenTabsProvider>
            <MemoryRouter initialEntries={["/"]}>
              <WorkspaceTopBar activeChangeId={null} />
            </MemoryRouter>
          </OpenTabsProvider>
        </ActiveProductProvider>
      </ThemeProvider>
    </QueryClientProvider>,
  );
}

describe("ThemeToggle re-homed in WorkspaceTopBar (CH-01KTHP)", () => {
  beforeEach(() => {
    stubMatchMedia(false); // start light
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(200, []));
  });
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    delete document.documentElement.dataset.theme;
  });

  it("renders the theme toggle inside the workspace top bar", () => {
    renderTopBar();
    const topbar = screen.getByTestId("workspace-topbar");
    // The toggle is a labelled button living WITHIN the top bar (not orphaned
    // elsewhere in the tree).
    const toggle = within(topbar).getByRole("button", {
      name: /switch to dark theme/i,
    });
    expect(toggle).toBeInTheDocument();
  });

  it("the re-homed toggle still flips the app theme on activation", () => {
    renderTopBar();
    const topbar = screen.getByTestId("workspace-topbar");
    expect(document.documentElement.dataset.theme).toBe("light");

    fireEvent.click(
      within(topbar).getByRole("button", { name: /switch to dark theme/i }),
    );

    expect(document.documentElement.dataset.theme).toBe("dark");
    // Accessible name + pressed state reflect the new active theme.
    expect(
      within(topbar).getByRole("button", { name: /switch to light theme/i }),
    ).toHaveAttribute("aria-pressed", "true");
  });

  it("the top bar (with the toggle mounted) has no WCAG AA violations", async () => {
    const { container } = renderTopBar();
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
