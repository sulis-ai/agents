// WP-008 (re-homed) — the change's live terminal as a ChangeNav VIEW.
//
// The old horizontal ThreadTabs ("Chat | Files | Terminal") was deleted when
// the cockpit moved to the ChangeNav left-nav + ThreadView main-area model.
// The terminal is now a first-class VIEW in that model: a "Terminal" nav entry
// that swaps the main area to <LiveTerminal/> (mirroring how Files is wired).
//
// This test asserts the re-homed contract:
//   - the Terminal nav entry renders alongside the other views,
//   - clicking it swaps the main area to the terminal section (one view at a
//     time — so xterm.js doesn't attach off-view),
//   - the change opens DIRECTLY on the terminal when ?view=terminal is in the
//     URL (the WP-009 launchChangeTerminal entry path).
//
// LiveTerminal mounts with no VITE_TERMINAL_WS_URL configured, so its bridge
// falls back to the "no terminal here" state — it renders its card chrome
// without a live socket, which is all this view-level test needs.
//
// References: WP-008 Contract (the terminal surface); ChangeNav (ChangeView +
// the nav entry); ThreadView (the {view === "terminal"} render + ?view= seed);
// WP-009 launchChangeTerminal (changeTerminalPath → ?view=terminal).

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import {
  render,
  screen,
  waitFor,
  fireEvent,
  within,
} from "@testing-library/react";
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

function renderAt(initialPath: string, client = freshClient()) {
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

function mockFetch() {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url === "/api/changes/abc") {
      return Promise.resolve(jsonResponse(200, sampleChange));
    }
    if (url === "/api/changes/abc/status") {
      return Promise.resolve(jsonResponse(200, sampleStatus));
    }
    // transcript / files / anything else — empty so children don't error.
    return Promise.resolve(jsonResponse(200, []));
  });
}

describe("ThreadView — terminal as a ChangeNav view (WP-008 re-homed)", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockReset();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders a Terminal nav entry alongside the other views", async () => {
    mockFetch();
    renderAt("/c/abc");
    const nav = await screen.findByTestId("change-nav");
    expect(within(nav).getByTestId("view-terminal")).toBeInTheDocument();
    expect(
      within(nav).getByRole("tab", { name: /terminal/i }),
    ).toBeInTheDocument();
  });

  it("swaps the main area to the terminal view when the nav entry is clicked", async () => {
    mockFetch();
    renderAt("/c/abc");
    const nav = await screen.findByTestId("change-nav");

    // Conversation is the default — the terminal is not mounted yet (so
    // xterm.js doesn't attach off-view).
    expect(screen.queryByTestId("section-terminal")).not.toBeInTheDocument();

    fireEvent.click(within(nav).getByTestId("view-terminal"));

    expect(screen.getByTestId("section-terminal")).toBeInTheDocument();
    expect(screen.getByTestId("live-terminal")).toBeInTheDocument();
    // One view at a time — the conversation section is gone.
    expect(screen.queryByTestId("section-conversation")).not.toBeInTheDocument();
    expect(within(nav).getByTestId("view-terminal")).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("opens directly on the terminal view when ?view=terminal is in the URL (WP-009 launch path)", async () => {
    mockFetch();
    renderAt("/c/abc?view=terminal");
    await waitFor(() =>
      expect(screen.getByTestId("section-terminal")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("live-terminal")).toBeInTheDocument();
    expect(screen.getByTestId("view-terminal")).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });
});
