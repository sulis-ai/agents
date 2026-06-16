// WP-003 — <Board> tests (the NEW stage-column board cases; RED first).
//
// Journey A round-trip, client half: the board lays the active Product's
// in-flight changes into six lifecycle stage columns
// (recon→specify→design→implement→review→ship), each card in its column,
// shipped changes excluded (FR-15), with the one state-pattern set
// (loading skeleton / empty / error+retry — ADR-005).
//
// These are the column-placement + scope cases the characterisation test
// (Dashboard.test.tsx, behaviour pin) does not cover. Data is fetched
// through the typed client (apiGet funnel) — never `fetch` in the
// component (WPF-02); the test drives the real hook against mocked global
// fetch, the substrate every client test uses.

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { fireEvent, render, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { axe } from "jest-axe";
import type { Change } from "../../../shared/api-types";
import { Board } from "../pages/Board";
import { LIVENESS_POLL_MS } from "../config";

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
    // WP-001 widened fields — fixture defaults (override per test as needed).
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
          <Route path="/c/:changeId" element={<div data-testid="thread-view" />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const STAGES = ["recon", "specify", "design", "implement", "review", "ship"];

describe("<Board>", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockReset();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders all six stage columns in recon→ship order, including empty ones (FR-01, ADR-005)", async () => {
    // One in-flight change → the board (not the empty state) renders, and it
    // always shows all six columns in order — the columns without a change
    // are present-but-empty, not omitted.
    const changes: Change[] = [
      makeChange({ changeId: "01D", handle: "CH-01D", stage: "design" }),
    ];
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(200, changes));
    const { findAllByTestId } = renderBoard(freshClient());
    const columns = await findAllByTestId("stage-column");
    expect(columns).toHaveLength(6);
    expect(columns.map((c) => c.getAttribute("data-stage"))).toEqual(STAGES);
  });

  it("places three changes at three stages into their three columns", async () => {
    const changes: Change[] = [
      makeChange({ changeId: "01R", handle: "CH-01R", intent: "Recon work", stage: "recon" }),
      makeChange({ changeId: "01D", handle: "CH-01D", intent: "Design work", stage: "design" }),
      makeChange({ changeId: "01V", handle: "CH-01V", intent: "Review work", stage: "review" }),
    ];
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(200, changes));
    const { findByTestId } = renderBoard(freshClient());

    const reconCol = await findByTestId("stage-column-recon");
    const designCol = await findByTestId("stage-column-design");
    const reviewCol = await findByTestId("stage-column-review");
    const specifyCol = await findByTestId("stage-column-specify");

    expect(within(reconCol).getByText("CH-01R")).toBeInTheDocument();
    expect(within(designCol).getByText("CH-01D")).toBeInTheDocument();
    expect(within(reviewCol).getByText("CH-01V")).toBeInTheDocument();
    // A change is only in its own column.
    expect(within(specifyCol).queryByText("CH-01R")).not.toBeInTheDocument();
    // Each card surfaces handle + intent + stage badge (the card reuse).
    expect(within(reconCol).getByText("Recon work")).toBeInTheDocument();
  });

  it("excludes shipped changes from the in-flight board (FR-15)", async () => {
    const changes: Change[] = [
      makeChange({ changeId: "01LIVE", handle: "CH-01LIVE", stage: "review" }),
      makeChange({ changeId: "01DONE", handle: "CH-01DONE", stage: "shipped" }),
    ];
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(200, changes));
    const { findByText, queryByText } = renderBoard(freshClient());
    await findByText("CH-01LIVE");
    expect(queryByText("CH-01DONE")).not.toBeInTheDocument();
  });

  it("renders a skeleton while loading (one state-pattern set, ADR-005)", () => {
    vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise(() => {}));
    const { getByTestId } = renderBoard(freshClient());
    expect(getByTestId("board-loading")).toBeInTheDocument();
  });

  it("renders the empty state guiding how to start a change when zero changes (FR-03)", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(200, []));
    const { findByText } = renderBoard(freshClient());
    expect(await findByText(/nothing in flight/i)).toBeInTheDocument();
  });

  it("treats an all-shipped store as empty (no in-flight cards → empty state, FR-15/FR-03)", async () => {
    const changes: Change[] = [
      makeChange({ changeId: "01DONE", handle: "CH-01DONE", stage: "shipped" }),
    ];
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(200, changes));
    const { findByText } = renderBoard(freshClient());
    expect(await findByText(/nothing in flight/i)).toBeInTheDocument();
  });

  it("renders an error message + retry button on failure (ADR-005 error+retry)", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(500, { error: "boom" }));
    const { findByText, getByRole } = renderBoard(freshClient());
    await findByText(/something went wrong/i);
    expect(getByRole("button", { name: /retry/i })).toBeInTheDocument();
  });

  it("has no WCAG AA violations on the populated board (jest-axe, WPF-06)", async () => {
    const changes: Change[] = [
      makeChange({ changeId: "01R", handle: "CH-01R", stage: "recon" }),
      makeChange({ changeId: "01I", handle: "CH-01I", stage: "implement" }),
    ];
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(200, changes));
    const { container, findByText } = renderBoard(freshClient());
    await findByText("CH-01R");
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});

// ─── WP-007 — the integration seam + the board-level async-state behaviour ───
//
// WP-002 produces the enriched feed; WP-004 the lanes; WP-005 the card. This
// suite is the SEAM: it asserts the REAL needsAttention / health /
// lastActivityAt fields flow Board → StageColumn → ChangeCard end-to-end (not
// a mock), and that the board's loading / error / empty states still hold with
// the wider shape — including the four board-level async behaviours this WP
// owns: feed-fail → retry (EF-1), poll-fails-mid-session keeps last-good
// (EF-3), filter narrows the SAME board (UC-6), and shipped drops off on the
// next poll (AF-5). One feed poll only (NFR-POLL-1).

/** A URL-aware fetch double: route /api/changes vs /api/search to separate
 *  handlers, so the filter test can give the full board and the search
 *  different bodies (the board falls back to /api/changes with no filter and
 *  switches to /api/search when a filter is active). */
function routedFetch(handlers: {
  changes: () => Response;
  search?: () => Response;
}) {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input.toString();
    if (url.includes("/api/search")) {
      return (handlers.search ?? handlers.changes)();
    }
    return handlers.changes();
  });
}

describe("<Board> — enriched-feed integration seam (WP-007)", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockReset();
  });
  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("renders the WAITING foot (not health) for a flagged change — real needsAttention flows through (UC-2, BR-1)", async () => {
    const changes: Change[] = [
      makeChange({
        changeId: "01W",
        handle: "CH-01W",
        stage: "implement",
        needsAttention: { flagged: true, reason: "blocked" },
        // Even with an off-track health, the flagged change shows ONLY the
        // waiting foot (the single-verdict rule) — proves needsAttention.flagged
        // is the real field driving the branch, not a mock default.
        health: { state: "off-track", reason: "stalled" },
      }),
    ];
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(200, changes));
    const { findByTestId, queryByText } = renderBoard(freshClient());
    const card = await findByTestId("change-card");
    expect(within(card).getByText(/waiting on you/i)).toBeInTheDocument();
    // The health badge must NOT also render (waiting XOR health).
    expect(queryByText(/off track/i)).not.toBeInTheDocument();
  });

  it("renders the HEALTH badge for a not-flagged change — real health.state flows through (UC-3)", async () => {
    const changes: Change[] = [
      makeChange({
        changeId: "01H",
        handle: "CH-01H",
        stage: "review",
        needsAttention: { flagged: false, reason: null },
        health: { state: "off-track", reason: "tests failing" },
      }),
    ];
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(200, changes));
    const { findByTestId } = renderBoard(freshClient());
    const card = await findByTestId("change-card");
    // The health badge carries data-health-state from the REAL health.state.
    const badge = card.querySelector('[data-health-state="off-track"]');
    expect(badge).not.toBeNull();
    expect(within(card).queryByText(/waiting on you/i)).not.toBeInTheDocument();
  });

  it("reflects the real lastActivityAt on the probe (recent → working) (FR-41/42)", async () => {
    // Real timers (so findBy* polling works). The probe derives working-vs-live
    // from `lastActivityAt` recency against its `new Date()` default; a 5s-ago
    // activity is inside the 60s working window regardless of wall clock, so the
    // real lastActivityAt field drives the probe to "working".
    const recent = new Date(Date.now() - 5_000).toISOString();
    const changes: Change[] = [
      makeChange({
        changeId: "01P",
        handle: "CH-01P",
        stage: "implement",
        liveness: { status: "running", pid: 4242 },
        lastActivityAt: recent,
      }),
    ];
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(200, changes));
    const { findByTestId } = renderBoard(freshClient());
    const card = await findByTestId("change-card");
    const probe = card.querySelector("[data-probe-state]");
    expect(probe?.getAttribute("data-probe-state")).toBe("working");
  });

  it("S-20 / EF-1 — feed fails → error box + Retry render (no partial board); Retry refetches to a good board", async () => {
    // First load 500s → the error state; no board renders. Retry → 200 → board.
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(500, { error: "boom" }))
      .mockResolvedValueOnce(
        jsonResponse(200, [
          makeChange({ changeId: "01R", handle: "CH-01R", stage: "recon" }),
        ]),
      );
    vi.spyOn(globalThis, "fetch").mockImplementation(fetchMock as never);

    const { findByText, getByRole, queryByTestId } = renderBoard(freshClient());
    await findByText(/something went wrong/i);
    // No partial board behind the error box.
    expect(queryByTestId("board")).not.toBeInTheDocument();

    fireEvent.click(getByRole("button", { name: /retry/i }));
    // Retry refetches → the good board now renders.
    expect(await findByText("CH-01R")).toBeInTheDocument();
  });

  it("S-22 / EF-3 — a mid-session poll failure keeps the last-good board; no flicker to the error box; manual Refresh still works", async () => {
    vi.useFakeTimers();
    // Good load, then the background refetch (poll) 500s, then a manual refresh
    // 200s again — TanStack Query keeps the last-good data on the failed poll.
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse(200, [
          makeChange({ changeId: "01G", handle: "CH-01G", stage: "implement" }),
        ]),
      )
      .mockResolvedValueOnce(jsonResponse(500, { error: "transient" }))
      .mockResolvedValue(
        jsonResponse(200, [
          makeChange({ changeId: "01G", handle: "CH-01G", stage: "implement" }),
        ]),
      );
    vi.spyOn(globalThis, "fetch").mockImplementation(fetchMock as never);

    // retry:false so the failed poll surfaces immediately as the query's error,
    // proving the COMPONENT (not retry) is what keeps the board up.
    const { getByText, queryByText, getByRole } = renderBoard(freshClient());

    // The initial good load.
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    await vi.waitFor(() => expect(getByText("CH-01G")).toBeInTheDocument());

    // Advance past the poll interval → the background refetch fires and 500s.
    await vi.advanceTimersByTimeAsync(LIVENESS_POLL_MS + 50);
    await vi.waitFor(() =>
      expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(2),
    );

    // The last-good card is STILL on the board; the error box did NOT take over.
    expect(getByText("CH-01G")).toBeInTheDocument();
    expect(queryByText(/something went wrong/i)).not.toBeInTheDocument();

    // Manual Refresh still works (invalidate → the 200 handler restores).
    fireEvent.click(getByRole("button", { name: /refresh/i }));
    await vi.waitFor(() => expect(getByText("CH-01G")).toBeInTheDocument());
    vi.useRealTimers();
  });

  it("S-7 / UC-6 — a filter narrows the SAME six-lane board; clearing it restores the full board", async () => {
    // No filter → /api/changes returns two changes. With a query active →
    // /api/search returns ONE result. The board renders both in the SAME
    // six-lane layout (never a separate results screen); clearing restores.
    const fetchMock = routedFetch({
      changes: () =>
        jsonResponse(200, [
          makeChange({ changeId: "01A", handle: "CH-01A", stage: "recon" }),
          makeChange({ changeId: "01B", handle: "CH-01B", stage: "review" }),
        ]),
      search: () =>
        jsonResponse(200, {
          results: [
            makeChange({ changeId: "01A", handle: "CH-01A", stage: "recon" }),
          ],
        }),
    });
    vi.spyOn(globalThis, "fetch").mockImplementation(fetchMock as never);

    const { findByText, findAllByTestId, queryByText, getByRole } = renderBoard(
      freshClient(),
    );
    // Full board: both cards.
    await findByText("CH-01A");
    expect(await findByText("CH-01B")).toBeInTheDocument();

    // Type a query → the board narrows to the search result, in the SAME layout.
    fireEvent.change(getByRole("searchbox"), { target: { value: "alpha" } });
    await waitFor(() => {
      expect(queryByText("CH-01B")).not.toBeInTheDocument();
    });
    // Still the six-lane board (not a separate results screen).
    expect(await findAllByTestId("stage-column")).toHaveLength(6);
    expect(await findByText("CH-01A")).toBeInTheDocument();

    // Clear the query → the full board is restored.
    fireEvent.change(getByRole("searchbox"), { target: { value: "" } });
    expect(await findByText("CH-01B")).toBeInTheDocument();
  });

  it("S-14 / AF-5 — a change re-seeded as shipped drops off the in-flight board on the next poll, no error", async () => {
    vi.useFakeTimers();
    // Poll 1: in-flight (review). Poll 2: re-seeded as shipped → excluded
    // (FR-15) → it drops off the board with no card error.
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse(200, [
          makeChange({ changeId: "01S", handle: "CH-01S", stage: "review" }),
        ]),
      )
      .mockResolvedValue(
        jsonResponse(200, [
          makeChange({ changeId: "01S", handle: "CH-01S", stage: "shipped" }),
        ]),
      );
    vi.spyOn(globalThis, "fetch").mockImplementation(fetchMock as never);

    const { getByText, queryByText } = renderBoard(freshClient());
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    await vi.waitFor(() => expect(getByText("CH-01S")).toBeInTheDocument());

    // Next poll re-seeds it as shipped → it drops off the in-flight board.
    await vi.advanceTimersByTimeAsync(LIVENESS_POLL_MS + 50);
    await vi.waitFor(() =>
      expect(queryByText("CH-01S")).not.toBeInTheDocument(),
    );
    // No error box — a clean drop-off, not a failure.
    expect(queryByText(/something went wrong/i)).not.toBeInTheDocument();
    vi.useRealTimers();
  });

  it("NFR-POLL-1 — the board issues ONE feed poll, never a per-card fetch", async () => {
    const changes: Change[] = [
      makeChange({ changeId: "01A", handle: "CH-01A", stage: "recon" }),
      makeChange({ changeId: "01B", handle: "CH-01B", stage: "review" }),
      makeChange({ changeId: "01C", handle: "CH-01C", stage: "implement" }),
    ];
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      void input;
      return jsonResponse(200, changes);
    });
    vi.spyOn(globalThis, "fetch").mockImplementation(fetchMock as never);
    const { findByText } = renderBoard(freshClient());
    await findByText("CH-01A");
    // Three cards, but only the ONE list fetch — never one fetch per card.
    const calls = fetchMock.mock.calls.map((c) => String(c[0]));
    expect(calls.filter((u) => u.includes("/api/changes"))).toHaveLength(1);
    expect(calls.some((u) => u.includes("/api/changes/01A"))).toBe(false);
  });
});
