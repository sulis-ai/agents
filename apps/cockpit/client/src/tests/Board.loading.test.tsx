// WP-010 — <Board> loading state (RED first) — S-34 part 1 + the no-jump
// contract's structural half.
//
// loading ≠ empty (FR-52): while the feed is unresolved the board renders
// PER-CARD skeletons (FR-53) inside the SAME six-lane scaffold a loaded board
// uses — not a per-column block, and never the "start a change" empty guide.
// The loading region carries aria-busy + a screen-reader "Loading…" line, and
// each skeleton card is inert (aria-hidden, not focusable) per the §7c
// precedence (no real card exists yet).
//
// The no-layout-jump guarantee (BR-24 / NFR-PERF-5) has two halves: the
// STRUCTURAL half is pinned here (the loading board uses the real lane
// scaffold + the skeleton shares the real card's box), and the MEASURED half
// (zero card-box moves, no long-frame on the swap) is a Playwright trace in
// e2e/Board.loading.spec.ts — jsdom computes no layout so the box-move
// assertion belongs in a real browser.
//
// EF-3 / WP-007: the skeleton path is the INITIAL load only. A background poll
// refetch (data already present) must NEVER flicker back to skeletons — the
// board keeps last-good data. This suite asserts the skeleton path is not
// re-entered on refetch.

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { fireEvent, render, within } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { axe } from "jest-axe";
import type { Change } from "../../../shared/api-types";
import { Board } from "../pages/Board";
import { LIVENESS_POLL_MS } from "../config";
import { withProductsRoute } from "./_productsFetch";

function makeChange(overrides: Partial<Change> = {}): Change {
  return {
    changeId: "01ABC",
    handle: "CH-01ABC",
    slug: "fix-thing",
    primitive: "fix",
    branch: "fix/thing",
    worktreePath: "/tmp/worktree",
    intent: "Fix the broken thing",
    baseBranch: "main",
    baseSha: "abc123",
    createdAt: "2026-05-26T11:00:00Z",
    updatedAt: "2026-05-26T11:55:00Z",
    stage: "implement",
    liveness: { status: "unknown", reason: "no session" },
    needsAttention: { flagged: false, reason: null },
    health: { state: "unknown", reason: "too early to tell" },
    lastActivityAt: null,
    ...overrides,
  };
}

function freshClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, refetchOnWindowFocus: false, staleTime: 0 },
    },
  });
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function renderBoard(client: QueryClient) {
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route path="/" element={<Board />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const STAGES = ["recon", "specify", "design", "implement", "review", "ship"];

describe("<Board> — loading state (WP-010, S-34 part 1)", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockReset();
  });
  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("renders PER-CARD skeletons inside the real six-lane scaffold while the feed is pending (FR-53)", () => {
    // Never-resolving fetch → the board stays in the loading branch.
    vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise(() => {}));
    const { getByTestId, getAllByTestId } = renderBoard(freshClient());

    const loading = getByTestId("board-loading");
    expect(loading).toBeInTheDocument();

    // The loading board uses the SAME lane scaffold as a loaded board — six
    // labelled lanes, in order — so the swap to data does not restructure.
    const lanes = within(loading).getAllByTestId("stage-column");
    expect(lanes).toHaveLength(6);
    expect(lanes.map((l) => l.getAttribute("data-stage"))).toEqual(STAGES);

    // PER-CARD skeletons (not one block per column): several skeleton cards
    // render, the same component a lane will host once data lands.
    const skeletons = getAllByTestId("skeleton-card");
    expect(skeletons.length).toBeGreaterThan(1);
  });

  it("carries aria-busy + a screen-reader loading line, and the skeletons are inert (aria-hidden, not focusable)", () => {
    vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise(() => {}));
    const { getByTestId, getAllByTestId } = renderBoard(freshClient());

    const loading = getByTestId("board-loading");
    expect(loading).toHaveAttribute("aria-busy", "true");
    // A screen reader is told it's loading (not left to read meaningless bars).
    expect(within(loading).getByText(/loading/i)).toBeInTheDocument();

    // Every skeleton is inert: aria-hidden + nothing focusable.
    for (const sk of getAllByTestId("skeleton-card")) {
      expect(sk).toHaveAttribute("aria-hidden", "true");
      expect(sk.querySelector("a, button, [tabindex]")).toBeNull();
    }
  });

  it("never shows the 'start a change' empty guide while loading (loading ≠ empty, FR-52)", () => {
    vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise(() => {}));
    const { getByTestId, queryByTestId } = renderBoard(freshClient());
    expect(getByTestId("board-loading")).toBeInTheDocument();
    // The empty state must NOT render during loading.
    expect(queryByTestId("dashboard-empty")).not.toBeInTheDocument();
  });

  it("has no WCAG AA violations on the loading board (jest-axe, WPF-06)", async () => {
    vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise(() => {}));
    const { container, getByTestId } = renderBoard(freshClient());
    expect(getByTestId("board-loading")).toBeInTheDocument();
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("EF-3 — a background poll refetch does NOT re-enter the skeleton path (last-good data stays)", async () => {
    vi.useFakeTimers();
    // Good load, then the background poll 500s. The board keeps last-good data
    // and must NOT flicker back to the skeleton loading branch.
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse(200, [
          makeChange({ changeId: "01G", handle: "CH-01G", stage: "implement" }),
        ]),
      )
      .mockResolvedValue(jsonResponse(500, { error: "transient" }));
    vi.spyOn(globalThis, "fetch").mockImplementation(
      withProductsRoute(fetchMock) as never,
    );

    const { getByText, queryByTestId } = renderBoard(freshClient());
    await vi.waitFor(() => expect(getByText("CH-01G")).toBeInTheDocument());
    // Board is up — no skeletons.
    expect(queryByTestId("skeleton-card")).not.toBeInTheDocument();

    // Advance past the poll interval → the background refetch fires and fails.
    await vi.advanceTimersByTimeAsync(LIVENESS_POLL_MS + 50);
    await vi.waitFor(() =>
      expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(2),
    );

    // Still the last-good board, and the skeleton path was NOT re-entered.
    expect(getByText("CH-01G")).toBeInTheDocument();
    expect(queryByTestId("board-loading")).not.toBeInTheDocument();
    expect(queryByTestId("skeleton-card")).not.toBeInTheDocument();
    vi.useRealTimers();
  });

  it("swaps skeletons for real cards in the SAME lane scaffold once data resolves (no restructure)", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse(200, [
        makeChange({ changeId: "01R", handle: "CH-01R", stage: "recon" }),
      ]),
    );
    vi.spyOn(globalThis, "fetch").mockImplementation(
      withProductsRoute(fetchMock) as never,
    );
    const { findByText, getAllByTestId, queryByTestId } =
      renderBoard(freshClient());

    // Once resolved: the real card is in, the skeletons are gone, and the
    // board still has the six lanes in order (same scaffold).
    await findByText("CH-01R");
    expect(queryByTestId("skeleton-card")).not.toBeInTheDocument();
    const lanes = getAllByTestId("stage-column");
    expect(lanes).toHaveLength(6);
    expect(lanes.map((l) => l.getAttribute("data-stage"))).toEqual(STAGES);
  });
});
