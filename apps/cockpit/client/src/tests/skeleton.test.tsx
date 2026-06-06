// WP-011 — smoke test for <App />.
//
// Asserts <App /> mounts without throwing AND the board route (WP-003)
// renders inside the persistent workspace shell. Detailed route + layout
// behaviour lives in routing.test.tsx + WorkspaceShell.test.tsx.
//
// The chat-B2 redesign replaced the sidebar shell with the tabbed workspace
// top bar; the smoke test asserts the topbar (testid "workspace-topbar")
// renders, matching WorkspaceShell.test.tsx.

import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AppRoutes } from "../App";
import { renderWithClient } from "./_renderWithClient";

describe("App smoke", () => {
  it("mounts AppRoutes with a router + query client without throwing", () => {
    renderWithClient(
      <MemoryRouter initialEntries={["/"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(screen.getByTestId("page-board")).toBeInTheDocument();
    expect(screen.getByTestId("workspace-topbar")).toBeInTheDocument();
  });
});
