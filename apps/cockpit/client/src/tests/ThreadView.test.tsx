// WP-013 — <ThreadView /> tests.
//
//   - Renders <ThreadHeader> with the change's handle + stage from
//     useChange().
//   - <ThreadTabs> switches via search param ?tab=chat|files. Default is
//     chat; Files tab renders the WP-014 placeholder slot.
//   - A 404 from useChange renders the gone-or-moved message rather
//     than crashing the sidebar (sidebar testid stays present).
//
// References: WP-013 Contract (<ThreadView>, <ThreadHeader>,
// <ThreadTabs>), TDD §6 (view tree), TDD §6.2 (worktree-not-found
// empty state framing).

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThreadView } from "../pages/ThreadView";
import type { ChangeDetail } from "../../../shared/api-types";

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

function renderAt(initialPath: string) {
  const client = freshClient();
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path="/c/:changeId" element={<ThreadView />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const sampleChange: ChangeDetail = {
  changeId: "abc",
  handle: "CH-01ABC",
  slug: "my-change",
  primitive: "create",
  branch: "change/create-my-change",
  worktreePath: "/Users/x/repos/wt",
  intent: "ship the thing",
  baseBranch: "dev",
  baseSha: "deadbeef",
  createdAt: "2026-05-20T00:00:00Z",
  updatedAt: "2026-05-21T00:00:00Z",
  stage: "implement",
  liveness: { status: "running", pid: 4242 },
  transcriptPaths: [],
};

describe("<ThreadView />", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockReset();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the header with the change handle + stage", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url === "/api/changes/abc") {
        return Promise.resolve(jsonResponse(200, sampleChange));
      }
      // transcript fetch — return empty so Chat doesn't error.
      return Promise.resolve(jsonResponse(200, []));
    });

    renderAt("/c/abc");
    await waitFor(() =>
      expect(screen.getByTestId("thread-header")).toBeInTheDocument(),
    );
    const header = screen.getByTestId("thread-header");
    expect(header.textContent).toContain("CH-01ABC");
    expect(header.textContent).toContain("implement");
    expect(header.textContent).toContain("ship the thing");
  });

  it("defaults to the Chat tab when no ?tab= query is present", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url === "/api/changes/abc") {
        return Promise.resolve(jsonResponse(200, sampleChange));
      }
      return Promise.resolve(jsonResponse(200, []));
    });

    renderAt("/c/abc");
    await waitFor(() =>
      expect(screen.getByTestId("tab-panel-chat")).toBeInTheDocument(),
    );
    expect(
      screen.queryByTestId("tab-panel-files"),
    ).not.toBeInTheDocument();
  });

  it("switches to the Files tab when the user clicks the Files button", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url === "/api/changes/abc") {
        return Promise.resolve(jsonResponse(200, sampleChange));
      }
      return Promise.resolve(jsonResponse(200, []));
    });

    renderAt("/c/abc");
    await waitFor(() =>
      expect(screen.getByTestId("tab-panel-chat")).toBeInTheDocument(),
    );
    const filesTab = screen.getByRole("tab", { name: /files/i });
    fireEvent.click(filesTab);

    expect(screen.getByTestId("tab-panel-files")).toBeInTheDocument();
    expect(screen.queryByTestId("tab-panel-chat")).not.toBeInTheDocument();
  });

  it("opens directly on the Files tab when ?tab=files is in the URL", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url === "/api/changes/abc") {
        return Promise.resolve(jsonResponse(200, sampleChange));
      }
      return Promise.resolve(jsonResponse(200, []));
    });

    renderAt("/c/abc?tab=files");
    await waitFor(() =>
      expect(screen.getByTestId("tab-panel-files")).toBeInTheDocument(),
    );
  });

  it("shows the 'gone or moved' message when useChange returns 404", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url === "/api/changes/abc") {
        return Promise.resolve(jsonResponse(404, { error: "not found" }));
      }
      return Promise.resolve(jsonResponse(200, []));
    });

    renderAt("/c/abc");
    await waitFor(() =>
      expect(screen.getByTestId("thread-gone-or-moved")).toBeInTheDocument(),
    );
    expect(
      screen.getByText(/This change is gone or moved/i),
    ).toBeInTheDocument();
  });
});
