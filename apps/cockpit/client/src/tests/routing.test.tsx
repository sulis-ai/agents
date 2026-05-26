// WP-011 — Routing test.
//
// Asserts the three routes per the WP Contract:
//   /              → <Dashboard> placeholder
//   /c/:changeId   → <ThreadView> placeholder
//   /garbage       → <NotFound>
//
// Pages are rendered inside <Shell />, so the sidebar testid is also
// present in every case (the layout wraps every route).

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AppRoutes } from "../App";

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppRoutes />
    </MemoryRouter>,
  );
}

describe("App routes", () => {
  it("renders Dashboard at /", () => {
    renderAt("/");
    expect(screen.getByTestId("page-dashboard")).toBeInTheDocument();
    expect(screen.getByTestId("shell-sidebar")).toBeInTheDocument();
  });

  it("renders ThreadView at /c/:changeId", () => {
    renderAt("/c/CH-01KSJA");
    expect(screen.getByTestId("page-thread")).toBeInTheDocument();
    expect(screen.getByTestId("shell-sidebar")).toBeInTheDocument();
  });

  it("renders NotFound for an unknown path", () => {
    renderAt("/garbage");
    expect(screen.getByTestId("page-not-found")).toBeInTheDocument();
    expect(screen.getByTestId("shell-sidebar")).toBeInTheDocument();
  });
});
