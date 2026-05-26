// WP-015 — <FileToolbar /> diff-toggle tests.
//
// WP-014 shipped a disabled diff stub. WP-015 makes it live:
//   - the toggle is enabled
//   - label is "Show diff" when diff is off, "Show current" when on
//   - clicking flips the ?diff=1 search param on/off (URL is the source
//     of truth — toggle state derives from the URL, not local state)
//
// References: WP-015 Contract (<FileToolbar> change), TDD §6.1.

import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route, useSearchParams } from "react-router-dom";
import { FileToolbar } from "../components/FileToolbar";

// Surfaces the live search string so tests can assert URL changes.
function SearchProbe() {
  const [params] = useSearchParams();
  return <div data-testid="search-probe">{params.toString()}</div>;
}

function renderToolbar(initialEntry: string) {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route
          path="/c/:changeId"
          element={
            <>
              <FileToolbar
                relativePath="src/index.ts"
                absolutePath="/wt/src/index.ts"
              />
              <SearchProbe />
            </>
          }
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe("<FileToolbar /> diff toggle", () => {
  it("the diff toggle is enabled", () => {
    renderToolbar("/c/abc?file=src/index.ts");
    expect(
      screen.getByRole("button", { name: /show diff/i }),
    ).toBeEnabled();
  });

  it("shows 'Show diff' when diff is off", () => {
    renderToolbar("/c/abc?file=src/index.ts");
    expect(screen.getByRole("button", { name: /show diff/i })).toBeInTheDocument();
  });

  it("shows 'Show current' when diff is on", () => {
    renderToolbar("/c/abc?file=src/index.ts&diff=1");
    expect(
      screen.getByRole("button", { name: /show current/i }),
    ).toBeInTheDocument();
  });

  it("clicking turns the diff param on", () => {
    renderToolbar("/c/abc?file=src/index.ts");
    fireEvent.click(screen.getByRole("button", { name: /show diff/i }));
    expect(screen.getByTestId("search-probe").textContent).toContain("diff=1");
  });

  it("clicking again turns the diff param off", () => {
    renderToolbar("/c/abc?file=src/index.ts&diff=1");
    fireEvent.click(screen.getByRole("button", { name: /show current/i }));
    expect(screen.getByTestId("search-probe").textContent).not.toContain(
      "diff=1",
    );
  });

  it("preserves the file param when toggling", () => {
    renderToolbar("/c/abc?file=src/index.ts");
    fireEvent.click(screen.getByRole("button", { name: /show diff/i }));
    expect(screen.getByTestId("search-probe").textContent).toContain("file=");
  });
});
