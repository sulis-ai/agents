// WP-011 — Shell layout test.
//
// Asserts the persistent two-pane layout renders:
//   - <Sidebar> on the left (testid "shell-sidebar")
//   - <Outlet /> region on the right (testid "shell-outlet"), into
//     which the active route's element is rendered.
//
// The Sidebar's body content is a placeholder owned by WP-011 (WP-012
// fleshes it out); we only assert the structural skeleton here.

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { Shell } from "../layouts/Shell";

function renderShellWith(children: React.ReactNode, path = "/") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route element={<Shell />}>
          <Route path="/" element={<div data-testid="route-marker">child</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe("<Shell />", () => {
  it("renders sidebar and outlet regions", () => {
    renderShellWith(null);
    expect(screen.getByTestId("shell-sidebar")).toBeInTheDocument();
    expect(screen.getByTestId("shell-outlet")).toBeInTheDocument();
  });

  it("renders the matched child route inside the outlet region", () => {
    renderShellWith(null);
    const marker = screen.getByTestId("route-marker");
    expect(marker).toBeInTheDocument();
    // The marker is a descendant of the outlet region (TDD §6).
    expect(screen.getByTestId("shell-outlet")).toContainElement(marker);
  });
});
