// <ThreadView /> tests — the change workspace (chat-B2 signed contract).
//
// The change owns the screen inside its tab: a change-scoped LEFT NAV
// (<ChangeNav>: name + vertical stage track + view switches) + a full-width
// MAIN area rendering the selected view. Conversation is the default; Files /
// Brain / Preview swap the main area (one at a time).
//
// Preserved: the header info (name/stage) renders; a 404 renders the
// gone-or-moved message without crashing; the loading state renders.
// New: the vertical stage track marks the current stage; the status headline
// + needs-attention badge show; switching views swaps the main area.

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThreadView } from "../pages/ThreadView";
import type { ChangeDetail, ChangeStatus } from "../../../shared/api-types";

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

const sampleStatus: ChangeStatus = {
  changeId: "abc",
  stage: "implement",
  headline: "Building the change — working now.",
  needsAttention: { flagged: false, reason: null },
};

function mockFetch(opts: {
  change?: { status: number; body: unknown };
  status?: { status: number; body: unknown };
}) {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url === "/api/changes/abc") {
      const c = opts.change ?? { status: 200, body: sampleChange };
      return Promise.resolve(jsonResponse(c.status, c.body));
    }
    if (url === "/api/changes/abc/status") {
      const s = opts.status ?? { status: 200, body: sampleStatus };
      return Promise.resolve(jsonResponse(s.status, s.body));
    }
    // transcript / files / brain / anything else — empty so children don't error.
    return Promise.resolve(jsonResponse(200, []));
  });
}

describe("<ThreadView /> — change workspace (chat-B2)", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockReset();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the change-scoped left nav with the change name", async () => {
    mockFetch({});
    renderAt("/c/abc");
    await waitFor(() =>
      expect(screen.getByTestId("change-nav")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("change-nav").textContent).toContain(
      "ship the thing",
    );
  });

  it("marks the change's current stage in the vertical stage track (FR-04)", async () => {
    mockFetch({});
    renderAt("/c/abc");
    const nav = await screen.findByTestId("change-nav");
    const now = nav.querySelector('[data-stage="implement"]');
    expect(now).not.toBeNull();
    expect(now!.getAttribute("data-state")).toBe("now");
  });

  it("renders the read-time plain-English status headline (FR-05)", async () => {
    mockFetch({});
    renderAt("/c/abc");
    await waitFor(() =>
      expect(
        screen.getByText("Building the change — working now."),
      ).toBeInTheDocument(),
    );
  });

  it("renders the needs-attention badge when the status flags it (FR-12)", async () => {
    mockFetch({
      status: {
        status: 200,
        body: {
          ...sampleStatus,
          needsAttention: { flagged: true, reason: "waiting-on-decision" },
        },
      },
    });
    renderAt("/c/abc");
    await waitFor(() =>
      expect(screen.getByTestId("needs-attention")).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("needs-attention").textContent?.toLowerCase(),
    ).toMatch(/waiting on you/);
  });

  it("defaults to the Conversation view; switching the left nav swaps the main area", async () => {
    mockFetch({});
    renderAt("/c/abc");
    await waitFor(() =>
      expect(screen.getByTestId("change-nav")).toBeInTheDocument(),
    );
    // Conversation is the default view.
    expect(screen.getByTestId("section-conversation")).toBeInTheDocument();
    expect(screen.queryByTestId("section-files")).not.toBeInTheDocument();
    expect(screen.getByTestId("view-conversation")).toHaveAttribute(
      "aria-selected",
      "true",
    );

    // Switching to Files swaps the main area — one view at a time.
    fireEvent.click(screen.getByTestId("view-files"));
    expect(screen.getByTestId("section-files")).toBeInTheDocument();
    expect(screen.queryByTestId("section-conversation")).not.toBeInTheDocument();
  });

  it("shows the 'gone or moved' message when useChange returns 404 (preserved)", async () => {
    mockFetch({ change: { status: 404, body: { error: "not found" } } });
    renderAt("/c/abc");
    await waitFor(() =>
      expect(screen.getByTestId("thread-gone-or-moved")).toBeInTheDocument(),
    );
  });

  it("renders a loading state while the change is in flight (one state-pattern set)", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(
      () => new Promise(() => {}),
    );
    renderAt("/c/abc");
    await waitFor(() =>
      expect(screen.getByTestId("page-thread")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("thread-loading")).toBeInTheDocument();
  });
});
