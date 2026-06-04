// WP-004 — <ThreadView /> tests (REORGANISE-Refactor → coherent shell).
//
// The thread is re-homed from disconnected tabs (Chat | Files) to the
// ONE coherent reading order per ADR-005:
//
//   stage track + plain-English status  (top, the "where am I")
//   ───────────────────────────────────
//   Conversation · Brain · Files        (named sections, not tabs)
//   chat composer dock                  (persistent at the bottom)
//
// What the prior tab-era characterisation pinned and is PRESERVED here:
//   - the header renders the change handle + stage,
//   - a 404 from useChange renders the gone-or-moved message without
//     crashing the surface,
//   - the loading state renders.
//
// What is NEW (the refactor's behaviour, FR-04/05/12):
//   - the stage track marks the change's current stage (done/now/pending),
//   - the status header shows the read-time headline from /status,
//   - the needs-attention badge renders when the status flags it,
//   - the working area is named sections (Conversation/Brain/Files), the
//     chat composer is always present (docked) rather than behind a tab.
//
// References: WP-004 Contract (coherent shell), ADR-005, TDD §6/§6.2.

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
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

/** Mock fetch for the change + status + transcript reads the thread makes. */
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
    // transcript / brain / anything else — empty so children don't error.
    return Promise.resolve(jsonResponse(200, []));
  });
}

describe("<ThreadView /> — coherent shell (WP-004)", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockReset();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the header with the change handle (preserved from the tab era)", async () => {
    mockFetch({});
    renderAt("/c/abc");
    await waitFor(() =>
      expect(screen.getByTestId("thread-header")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("thread-header").textContent).toContain(
      "CH-01ABC",
    );
  });

  it("renders the stage track at the top with the change's current stage marked (FR-04)", async () => {
    mockFetch({});
    renderAt("/c/abc");
    await waitFor(() =>
      expect(screen.getByTestId("stage-track")).toBeInTheDocument(),
    );
    const steps = screen.getAllByTestId("stage-step");
    const implement = steps.find(
      (s) => s.getAttribute("data-stage") === "implement",
    )!;
    expect(implement.getAttribute("data-state")).toBe("now");
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

  it("renders the working area as named sections, not tabs (Conversation/Brain/Files)", async () => {
    mockFetch({});
    renderAt("/c/abc");
    await waitFor(() =>
      expect(screen.getByTestId("thread-header")).toBeInTheDocument(),
    );
    // Named sections present together — no single-tab-at-a-time gating.
    expect(screen.getByTestId("section-conversation")).toBeInTheDocument();
    expect(screen.getByTestId("section-files")).toBeInTheDocument();
    // The old tab rail is gone.
    expect(
      screen.queryByRole("tab", { name: /files/i }),
    ).not.toBeInTheDocument();
  });

  it("shows the 'gone or moved' message when useChange returns 404 (preserved)", async () => {
    mockFetch({ change: { status: 404, body: { error: "not found" } } });
    renderAt("/c/abc");
    await waitFor(() =>
      expect(screen.getByTestId("thread-gone-or-moved")).toBeInTheDocument(),
    );
    expect(
      screen.getByText(/This change is gone or moved/i),
    ).toBeInTheDocument();
  });

  it("renders a loading state while the change is in flight (one state-pattern set)", async () => {
    // Never resolve the change fetch — keep it loading.
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
