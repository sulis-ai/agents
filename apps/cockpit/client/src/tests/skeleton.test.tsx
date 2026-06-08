// WP-011 — smoke test for <App />.
//
// Asserts <App /> mounts without throwing AND the board route (WP-003)
// renders inside the persistent workspace shell. Detailed route + layout
// behaviour lives in routing.test.tsx + WorkspaceShell.test.tsx.
//
// The chat-B2 redesign replaced the sidebar shell with the tabbed workspace
// top bar; the smoke test asserts the topbar (testid "workspace-topbar")
// renders, matching WorkspaceShell.test.tsx.

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AppRoutes } from "../App";
import { renderWithClient } from "./_renderWithClient";
// WP-004 — the workspace top bar now hosts the ThemeToggle (a useTheme()
// consumer), so the smoke mount wraps AppRoutes in a ThemeProvider, mirroring
// App.tsx production. Composed with main's shared renderWithClient harness
// (EP-03 reuse).
import { ThemeProvider } from "../theme/ThemeProvider";
import { stubMatchMedia } from "./helpers/stubMatchMedia";

describe("App smoke", () => {
  beforeEach(() => {
    stubMatchMedia(false);
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    delete document.documentElement.dataset.theme;
  });

  it("mounts AppRoutes with a router + query client without throwing", () => {
    renderWithClient(
      <ThemeProvider>
        <MemoryRouter initialEntries={["/"]}>
          <AppRoutes />
        </MemoryRouter>
      </ThemeProvider>,
    );
    expect(screen.getByTestId("page-board")).toBeInTheDocument();
    expect(screen.getByTestId("workspace-topbar")).toBeInTheDocument();
  });
});
