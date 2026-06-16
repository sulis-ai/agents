// WP-010 — <Board> empty state (RED first) — S-9 / AF-1 / UC-8.
//
// empty ≠ loading (FR-52): empty = the feed RESOLVED with zero in-flight
// changes and no filter active. The board then renders the <EmptyState>
// "start a change" guide and the six-lane board does NOT render — and a
// loading board never shows that guide (asserted in Board.loading.test.tsx).
// This is the first-run state (UC-8 / S-9): zero changes + no filter.
//
// This file tightens the empty branch into its own scenario surface so the
// loading/empty distinction is pinned on both sides.

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render } from "@testing-library/react";
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

describe("<Board> — empty state (WP-010, S-9 / AF-1)", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockReset();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("first-run: zero changes + no filter → the EmptyState guide renders and the six-lane board does NOT (S-9)", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(200, []));
    const { findByTestId, queryByTestId } = renderBoard(freshClient());

    // The "start a change" guide renders.
    const empty = await findByTestId("dashboard-empty");
    expect(empty).toBeInTheDocument();
    // The six-lane board does NOT render (the guide replaces it).
    expect(queryByTestId("board")).not.toBeInTheDocument();
    // And there are no skeletons (this is RESOLVED-empty, not loading).
    expect(queryByTestId("skeleton-card")).not.toBeInTheDocument();
    expect(queryByTestId("board-loading")).not.toBeInTheDocument();
  });

  it("an all-shipped store reads as empty (zero in-flight → the guide, not the board) (FR-15 / AF-1)", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(200, [
        makeChange({
          changeId: "01DONE",
          handle: "CH-01DONE",
          stage: "shipped",
        }),
      ]),
    );
    const { findByTestId, queryByTestId } = renderBoard(freshClient());
    expect(await findByTestId("dashboard-empty")).toBeInTheDocument();
    expect(queryByTestId("board")).not.toBeInTheDocument();
  });

  it("has no WCAG AA violations on the empty-state guide (jest-axe, WPF-06)", async () => {
    // Scope axe to the EmptyState region this WP owns. The whole-page audit is
    // deferred because the mobile lane-switcher (WP-008's SearchBar) dangles
    // aria-controls to lane-<stage> ids that the empty board legitimately omits
    // — a pre-existing WP-008 a11y defect tracked as SF-36729581 (out of this
    // WP's Contract, which is the SkeletonCard + the Board loading branch).
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(200, []));
    const { findByTestId } = renderBoard(freshClient());
    const empty = await findByTestId("dashboard-empty");
    const results = await axe(empty);
    expect(results).toHaveNoViolations();
  });
});
