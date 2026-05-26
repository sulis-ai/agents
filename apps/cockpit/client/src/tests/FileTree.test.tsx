// WP-014 — <FileTree /> tests.
//
// The tree renders the worktree root listing (one level), with
// directories first. Expanding a directory fires useTree(changeId,
// path) for that directory's path. Clicking a file sets ?file=... in
// the URL so the selection is shareable and survives refresh.
//
// useTree is backed by GET /api/changes/:id/tree?path=...; we mock
// fetch and assert the request URLs include the right path param.
//
// References: WP-014 Contract (<FileTree>), TDD §6.

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  within,
} from "@testing-library/react";
import { MemoryRouter, Routes, Route, useLocation } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { TreeNode } from "../../../shared/api-types";
import { FileTree } from "../components/FileTree";

function freshClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
  });
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

// Surfaces the current search string so a test can assert ?file=.
function LocationProbe() {
  const loc = useLocation();
  return <div data-testid="location-search">{loc.search}</div>;
}

function renderTree() {
  const client = freshClient();
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/c/abc"]}>
        <Routes>
          <Route
            path="/c/:changeId"
            element={
              <>
                <FileTree changeId="abc" />
                <LocationProbe />
              </>
            }
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const ROOT: TreeNode[] = [
  { name: "src", path: "src", kind: "directory", hasChildren: true },
  { name: "README.md", path: "README.md", kind: "file", hasChildren: false },
  {
    name: "package.json",
    path: "package.json",
    kind: "file",
    hasChildren: false,
  },
];

const SRC_CHILDREN: TreeNode[] = [
  { name: "index.ts", path: "src/index.ts", kind: "file", hasChildren: false },
];

describe("<FileTree />", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockReset();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the three root nodes with the folder first", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      // Root listing only (no path param or empty path).
      if (url.includes("/tree"))
        return Promise.resolve(jsonResponse(200, ROOT));
      return Promise.resolve(jsonResponse(404, { error: "no" }));
    });

    renderTree();

    await waitFor(() => expect(screen.getByText("src")).toBeInTheDocument());
    const tree = screen.getByTestId("file-tree");
    const labels = within(tree).getAllByTestId(/^file-tree-node-/);
    // Directory ("src") must come before the files.
    expect(labels[0]).toHaveTextContent("src");
  });

  it("fires useTree with the directory path when a folder is expanded", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation((input) => {
        const url = String(input);
        if (url.includes("path=src"))
          return Promise.resolve(jsonResponse(200, SRC_CHILDREN));
        if (url.includes("/tree"))
          return Promise.resolve(jsonResponse(200, ROOT));
        return Promise.resolve(jsonResponse(404, { error: "no" }));
      });

    renderTree();

    await waitFor(() => expect(screen.getByText("src")).toBeInTheDocument());
    fireEvent.click(screen.getByText("src"));

    // After expanding, a request with path=src must have been issued and
    // the child file rendered.
    await waitFor(() =>
      expect(screen.getByText("index.ts")).toBeInTheDocument(),
    );
    const calledWithSrcPath = fetchSpy.mock.calls.some((c) =>
      String(c[0]).includes("path=src"),
    );
    expect(calledWithSrcPath).toBe(true);
  });

  it("sets ?file=... in the URL when a file is clicked", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.includes("/tree"))
        return Promise.resolve(jsonResponse(200, ROOT));
      return Promise.resolve(jsonResponse(404, { error: "no" }));
    });

    renderTree();

    await waitFor(() =>
      expect(screen.getByText("README.md")).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByText("README.md"));

    await waitFor(() =>
      expect(screen.getByTestId("location-search").textContent).toContain(
        "file=README.md",
      ),
    );
  });

  it("does not fetch a directory's children until it is expanded", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation((input) => {
        const url = String(input);
        if (url.includes("path=src"))
          return Promise.resolve(jsonResponse(200, SRC_CHILDREN));
        if (url.includes("/tree"))
          return Promise.resolve(jsonResponse(200, ROOT));
        return Promise.resolve(jsonResponse(404, { error: "no" }));
      });

    renderTree();

    // Wait for the root listing (with its collapsed "src" directory) to
    // render, then assert no request for src's children was issued. A
    // collapsed directory must not subscribe to the root query or fetch
    // its own children.
    await waitFor(() => expect(screen.getByText("src")).toBeInTheDocument());
    const fetchedSrcChildren = fetchSpy.mock.calls.some((c) =>
      String(c[0]).includes("path=src"),
    );
    expect(fetchedSrcChildren).toBe(false);
    // Exactly one tree request (the root listing) — collapsed nodes added
    // no extra fetches.
    const treeCalls = fetchSpy.mock.calls.filter((c) =>
      String(c[0]).includes("/tree"),
    );
    expect(treeCalls.length).toBe(1);
  });
});
