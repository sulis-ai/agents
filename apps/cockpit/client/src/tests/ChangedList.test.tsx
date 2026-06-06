// WP-P03/P04 — <ChangedList /> diff-count tests.
//
// The Changed scope renders an in-memory expand/collapse tree of the
// changed files. On top of the existing status dot + folder structure,
// each file row shows its +N −N line counts (from git numstat), and each
// folder rolls up the sum of its descendants' added/removed (skipping
// binary files, whose counts are null). A binary file shows "binary"
// rather than numbers.
//
// References: WP-P03 (file counts), WP-P04 (folder rollups);
// end-to-end-journey.html signed mockup (the Changed tree).

import { describe, it, expect } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import type { ChangedFiles } from "../../../shared/api-types";
import { ChangedList } from "../components/ChangedList";

function renderList(changed: ChangedFiles) {
  return render(
    <MemoryRouter initialEntries={["/c/abc"]}>
      <Routes>
        <Route
          path="/c/:changeId"
          element={
            <ChangedList
              changed={changed}
              isLoading={false}
              isError={false}
              filter=""
            />
          }
        />
      </Routes>
    </MemoryRouter>,
  );
}

const sample: ChangedFiles = {
  baseKnown: true,
  files: [
    { path: "src/checkout/checkout.ts", status: "edited", added: 118, removed: 9 },
    { path: "src/checkout/cart.ts", status: "edited", added: 34, removed: 12 },
    { path: "src/checkout/pricing.ts", status: "new", added: 52, removed: 4 },
    { path: "README.md", status: "edited", added: 6, removed: 1 },
    // a binary file — numstat reports "-" for both, surfaced as null
    { path: "assets/logo.png", status: "new", added: null, removed: null },
  ],
};

describe("ChangedList — diff counts", () => {
  it("shows +N −N on a file row beside its status dot", () => {
    renderList(sample);
    const row = screen.getByTestId("changed-row-README.md");
    expect(within(row).getByText("+6")).toBeInTheDocument();
    expect(within(row).getByText("−1")).toBeInTheDocument();
    // status dot still present
    expect(within(row).getByLabelText("edited")).toBeInTheDocument();
  });

  it("rolls up the sum of descendants onto the folder row", () => {
    renderList(sample);
    // src/checkout = 118+34+52 added, 9+12+4 removed.
    // src is collapsed by default — expand it to reveal the checkout folder.
    fireEvent.click(screen.getByRole("button", { name: /^src204 added/ }));
    const folder = screen.getByRole("button", { name: /^checkout204 added/ });
    expect(within(folder).getByText("+204")).toBeInTheDocument();
    expect(within(folder).getByText("−25")).toBeInTheDocument();
  });

  it("rolls up across nested folders onto the top-level folder", () => {
    renderList(sample);
    // src contains only checkout/* here, so src rolls up to the same totals
    const src = screen.getByRole("button", { name: /^src204 added/ });
    expect(within(src).getByText("+204")).toBeInTheDocument();
    expect(within(src).getByText("−25")).toBeInTheDocument();
  });

  it("shows 'binary' instead of numbers for a binary file", () => {
    renderList(sample);
    // assets is collapsed by default; expand it
    const assets = screen.getByRole("button", { name: /^assets/ });
    fireEvent.click(assets);
    const row = screen.getByTestId("changed-row-assets/logo.png");
    expect(within(row).getByText("binary")).toBeInTheDocument();
    expect(within(row).queryByText(/^\+/)).not.toBeInTheDocument();
  });

  it("skips binary (null) counts in the folder rollup", () => {
    renderList(sample);
    // assets/ holds only the binary file → rolls up to +0 −0 (it changed)
    const assets = screen.getByRole("button", { name: /^assets/ });
    expect(within(assets).getByText("+0")).toBeInTheDocument();
    expect(within(assets).getByText("−0")).toBeInTheDocument();
  });

  it("does not render diff counts in the loading/error/no-baseline states", () => {
    const { rerender } = render(
      <MemoryRouter>
        <ChangedList
          changed={undefined}
          isLoading={true}
          isError={false}
          filter=""
        />
      </MemoryRouter>,
    );
    expect(screen.queryByText(/^\+/)).not.toBeInTheDocument();
    rerender(
      <MemoryRouter>
        <ChangedList
          changed={{ files: [], baseKnown: false }}
          isLoading={false}
          isError={false}
          filter=""
        />
      </MemoryRouter>,
    );
    expect(screen.getByText(/No baseline recorded/)).toBeInTheDocument();
  });
});
