// CH-R5EE44 Fix 3 — the per-change AgentPicker drives the resolved provider.
//
// The per-change view had no agent picker; the per-change session was a fixed
// claude pty. This mounts the EXISTING <AgentPicker> (the same one the
// product-wide chat uses) in the per-change terminal view, wired to a REAL
// per-change provider remember (PUT /api/changes/:id/provider). Switching applies
// to the NEXT session-open for that change (the AgentPicker's existing
// applied:"new-work" semantics) — NOT a hot-swap of a running PTY.
//
// This test asserts the picker is mounted in the terminal view, shows the
// change's remembered running provider, and a switch drives the PUT with the
// change's id + the chosen provider.
//
// References: AgentPicker (the reused picker); ThreadView (the terminal view);
// the per-change provider funnel (putChangeProvider / fetchChangeProvider).

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
import type {
  ChangeDetail,
  ChangeStatus,
  ChatProvider,
} from "../../../shared/api-types";

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
  needsAttention: { flagged: false, reason: null },
  health: { state: "unknown", reason: "too early to tell" },
  lastActivityAt: null,
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
    return Promise.resolve(jsonResponse(200, []));
  });
}

function renderAt(
  initialPath: string,
  injected: {
    fetchChangeProvider?: (changeId: string) => Promise<ChatProvider>;
    putChangeProvider?: (
      changeId: string,
      provider: ChatProvider,
    ) => Promise<{ provider: ChatProvider; applied: "new-work" }>;
  },
) {
  return render(
    <QueryClientProvider client={freshClient()}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route
            path="/c/:changeId"
            element={
              <ThreadView
                fetchChangeProvider={injected.fetchChangeProvider}
                putChangeProvider={injected.putChangeProvider}
              />
            }
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ThreadView — per-change AgentPicker (CH-R5EE44 Fix 3)", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockReset();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("mounts the AgentPicker in the terminal view showing the change's remembered provider", async () => {
    mockFetch();
    const fetchChangeProvider = vi.fn(async () => "agy" as ChatProvider);
    renderAt("/c/abc?view=terminal", { fetchChangeProvider });

    // The picker is mounted in the terminal view and names the running provider.
    const picker = await screen.findByTestId("agent-picker");
    expect(picker).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByTestId("agent-picker-trigger").textContent).toMatch(
        /antigravity/i,
      ),
    );
    expect(fetchChangeProvider).toHaveBeenCalledWith("abc");
  });

  it("switching the picker drives putChangeProvider(changeId, provider) for the next open", async () => {
    mockFetch();
    const fetchChangeProvider = vi.fn(async () => "pty" as ChatProvider);
    const putChangeProvider = vi.fn(async (_id: string, p: ChatProvider) => ({
      provider: p,
      applied: "new-work" as const,
    }));
    renderAt("/c/abc?view=terminal", {
      fetchChangeProvider,
      putChangeProvider,
    });

    await screen.findByTestId("agent-picker");
    fireEvent.click(screen.getByTestId("agent-picker-trigger"));
    const menu = screen.getByTestId("agent-picker-menu");
    const antigravity = within(menu)
      .getAllByRole("menuitemradio")
      .find((r) =>
        /antigravity/i.test(r.getAttribute("aria-label") ?? r.textContent ?? ""),
      )!;
    fireEvent.click(antigravity);

    // The change is "running" (liveness.status running), so AgentPicker gates the
    // switch behind the AI-03 confirm ("applies to new work").
    const confirm = await screen.findByTestId("agent-switch-confirm");
    expect(confirm.textContent).toMatch(/new work/i);
    fireEvent.click(screen.getByTestId("agent-switch-confirm-yes"));

    await waitFor(() =>
      expect(putChangeProvider).toHaveBeenCalledWith("abc", "agy"),
    );
  });

  it("does not mount the picker outside the terminal view", async () => {
    mockFetch();
    renderAt("/c/abc", {
      fetchChangeProvider: vi.fn(async () => "pty" as ChatProvider),
    });
    await screen.findByTestId("section-conversation");
    expect(screen.queryByTestId("agent-picker")).not.toBeInTheDocument();
  });
});
