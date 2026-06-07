// Hover-prefetch — pointer-enter / focus on a tree row warms its data so the
// click lands on a cache hit (the "feels instant" headline).
//
// We render the real <FileTree> (All-files) and the real <ChangedList>
// (Changed scope) against a real QueryClient, spy on prefetchQuery, and
// assert that hovering / focusing a folder, a file, and a changed row fires
// the right prefetch (same queryKey the hook uses), with keyboard parity.

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ChangedFiles, TreeNode } from "../../../shared/api-types";
import { FileTree } from "../components/FileTree";
import { ChangedList } from "../components/ChangedList";

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

const ROOT: TreeNode[] = [
  { name: "src", path: "src", kind: "directory", hasChildren: true },
  { name: "README.md", path: "README.md", kind: "file", hasChildren: false },
];

function renderTree(client: QueryClient) {
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/c/abc"]}>
        <Routes>
          <Route path="/c/:changeId" element={<FileTree changeId="abc" />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const CHANGED: ChangedFiles = {
  baseKnown: true,
  files: [{ path: "README.md", status: "edited", added: 6, removed: 1 }],
};

function renderChanged(client: QueryClient) {
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/c/abc"]}>
        <Routes>
          <Route
            path="/c/:changeId"
            element={
              <ChangedList
                changeId="abc"
                changed={CHANGED}
                isLoading={false}
                isError={false}
                filter=""
              />
            }
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("hover-prefetch", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.includes("path=src"))
        return Promise.resolve(jsonResponse(200, []));
      if (url.includes("/tree")) return Promise.resolve(jsonResponse(200, ROOT));
      return Promise.resolve(jsonResponse(200, {}));
    });
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("prefetches a folder's children on mouse-enter", async () => {
    const client = freshClient();
    const spy = vi.spyOn(client, "prefetchQuery");
    renderTree(client);

    await waitFor(() => expect(screen.getByText("src")).toBeInTheDocument());
    spy.mockClear();
    fireEvent.mouseEnter(screen.getByText("src"));

    expect(
      spy.mock.calls.some(
        (c) => JSON.stringify((c[0] as { queryKey: unknown }).queryKey) ===
          JSON.stringify(["tree", "abc", "src"]),
      ),
    ).toBe(true);
  });

  it("prefetches a file's contents AND its origin on mouse-enter", async () => {
    const client = freshClient();
    const spy = vi.spyOn(client, "prefetchQuery");
    renderTree(client);

    await waitFor(() =>
      expect(screen.getByText("README.md")).toBeInTheDocument(),
    );
    spy.mockClear();
    fireEvent.mouseEnter(screen.getByText("README.md"));

    const keys = spy.mock.calls.map((c) =>
      JSON.stringify((c[0] as { queryKey: unknown }).queryKey),
    );
    expect(keys).toContain(JSON.stringify(["file", "abc", "README.md"]));
    expect(keys).toContain(
      JSON.stringify(["origin", "abc", "path", "README.md"]),
    );
  });

  it("prefetches on focus too (keyboard parity)", async () => {
    const client = freshClient();
    const spy = vi.spyOn(client, "prefetchQuery");
    renderTree(client);

    await waitFor(() => expect(screen.getByText("src")).toBeInTheDocument());
    spy.mockClear();
    fireEvent.focus(screen.getByText("src"));

    expect(
      spy.mock.calls.some(
        (c) => JSON.stringify((c[0] as { queryKey: unknown }).queryKey) ===
          JSON.stringify(["tree", "abc", "src"]),
      ),
    ).toBe(true);
  });

  it("prefetches a changed row's file + origin on mouse-enter", async () => {
    const client = freshClient();
    const spy = vi.spyOn(client, "prefetchQuery");
    renderChanged(client);

    spy.mockClear();
    fireEvent.mouseEnter(screen.getByTestId("changed-row-README.md"));

    const keys = spy.mock.calls.map((c) =>
      JSON.stringify((c[0] as { queryKey: unknown }).queryKey),
    );
    expect(keys).toContain(JSON.stringify(["file", "abc", "README.md"]));
    expect(keys).toContain(
      JSON.stringify(["origin", "abc", "path", "README.md"]),
    );
  });
});
