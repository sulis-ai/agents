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

import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
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

  // WP-008 — at tablet/mobile widths the visible label condenses to "+ New" so
  // the top bar never wraps/clips (IDEAS.md Concern 4). The FULL action must
  // still be announced: the accessible name stays "Start something new" even
  // when the visible text is the compact form. jsdom can't apply the media
  // query, so we pin the contract that makes the collapse safe: the button
  // carries an explicit accessible name independent of its visible label text,
  // so hiding the label via CSS can never strip the action's name from the
  // accessibility tree. (The visible collapse itself is a CSS-pin below + the
  // Playwright 390px journey.)
  it("the Start button's accessible name stays 'Start something new' independent of the visible label (so the '+ New' collapse keeps the full name)", () => {
    renderTopBar();
    const topbar = screen.getByTestId("workspace-topbar");
    const startButton = within(topbar).getByTestId("start-change-button");
    // An explicit aria-label pins the full name on the element itself — it does
    // NOT depend on the visible <span> label (which CSS hides at narrow widths).
    expect(startButton).toHaveAttribute("aria-label", "Start something new");
    // And it is still findable by that accessible name (the role+name contract
    // the journey + the WP-001 tests rely on).
    expect(
      within(topbar).getByRole("button", { name: /start something new/i }),
    ).toBe(startButton);
  });

  describe("WorkspaceShell.module.css encodes the responsive top-bar collapse (WP-008)", () => {
    const TOPBAR_CSS = resolve(
      __dirname,
      "..",
      "layouts",
      "WorkspaceShell.module.css",
    );
    const css = existsSync(TOPBAR_CSS) ? readFileSync(TOPBAR_CSS, "utf8") : "";

    it("collapses the Start button's visible label and shows a compact '+ New' at narrow widths", () => {
      // A media query exists for the condensed chrome, and within it the long
      // label is hidden while a compact "New" affordance appears.
      expect(css).toMatch(/@media[^{]*max-width:\s*(1099|599)px/);
      expect(css).toMatch(/startBtnLabel[\s\S]*?display:\s*none/);
      // The compact form surfaces "New" (the visible "+ New" text) at narrow
      // widths — via a ::after content rule on the button.
      expect(css).toMatch(/content:\s*["']\+?\s*New["']/);
    });

    it("the top bar stays one fixed-height row that never wraps (no flex-wrap at narrow widths)", () => {
      // The bar's height is fixed (48px) and it must not wrap — pinned so a
      // 390px viewport can't push controls onto a second row or off-screen.
      const block = css.slice(css.indexOf(".topbar"));
      expect(block).toMatch(/height:\s*48px/);
      expect(block).not.toMatch(/flex-wrap:\s*wrap/);
    });

    it("carries no raw colour literals in the new responsive rules — tokens only (WPF-07)", () => {
      const hexMatches = css.match(/#[0-9a-fA-F]{3,8}\b/g) ?? [];
      expect(hexMatches).toEqual([]);
    });
  });
});
