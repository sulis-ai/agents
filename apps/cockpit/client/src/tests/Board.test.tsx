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
import { render, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { axe } from "jest-axe";
import type { Change } from "../../../shared/api-types";
import { Board } from "../pages/Board";

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
