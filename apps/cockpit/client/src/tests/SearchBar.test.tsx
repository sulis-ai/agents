// WP-007 — <SearchBar> + board-wiring tests (FR-10/11/12, ADR-005).
//
// Two layers:
//   1. <SearchBar> as a controlled component — the search box, the stage
//      filter chips, and the needs-attention chip emit the right change
//      events and reflect their pressed/active state. It consumes
//      tokens.css only and matches the SIGNED visual contract toolbar
//      (sulis-app.html: role="search", a content-search box, stage chips,
//      a "Needs attention" chip).
//   2. The board wiring — with the SearchBar in the Board's toolbar,
//      typing a term narrows the SAME board (not a separate results
//      screen, ADR-005); stage + needs-attention filters narrow it;
//      clearing restores the full board.
//
// Data is fetched through the typed client (apiGet funnel) — never `fetch`
// in the component (WPF-02); the board-wiring tests drive the real hooks
// against mocked global fetch, the substrate every client test uses.

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, waitFor, within, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { axe } from "jest-axe";
import type { Change } from "../../../shared/api-types";
import { SearchBar } from "../components/SearchBar";
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
    // WP-001 widened fields — fixture defaults (override per test as needed).
    needsAttention: { flagged: false, reason: null },
    health: { state: "unknown", reason: "too early to tell" },
    lastActivityAt: null,
    ...overrides,
  };
}

// ─── Layer 1: <SearchBar> controlled-component contract ──────────────────────

describe("<SearchBar> (controlled component)", () => {
  function noop() {}

  it("renders the search box, the stage chip, and the needs-attention chip (visual contract toolbar)", () => {
    const { getByRole, getByText } = render(
      <SearchBar
        query=""
        stages={[]}
        needsAttention={false}
        onQueryChange={noop}
        onToggleStage={noop}
        onToggleNeedsAttention={noop}
      />,
    );
    // The toolbar is a search landmark (sulis-app.html role="search").
    expect(getByRole("search")).toBeInTheDocument();
    // A content-search textbox.
    expect(getByRole("searchbox")).toBeInTheDocument();
    // The needs-attention chip.
    expect(getByText(/needs attention/i)).toBeInTheDocument();
  });

  it("calls onQueryChange as the founder types", () => {
    const onQueryChange = vi.fn();
    const { getByRole } = render(
      <SearchBar
        query=""
        stages={[]}
        needsAttention={false}
        onQueryChange={onQueryChange}
        onToggleStage={noop}
        onToggleNeedsAttention={noop}
      />,
    );
    fireEvent.change(getByRole("searchbox"), { target: { value: "login" } });
    expect(onQueryChange).toHaveBeenCalledWith("login");
  });

  it("reflects the current query value (controlled)", () => {
    const { getByRole } = render(
      <SearchBar
        query="rollback"
        stages={[]}
        needsAttention={false}
        onQueryChange={noop}
        onToggleStage={noop}
        onToggleNeedsAttention={noop}
      />,
    );
    expect((getByRole("searchbox") as HTMLInputElement).value).toBe("rollback");
  });

  it("toggles a stage when its chip is clicked (FR-11)", () => {
    const onToggleStage = vi.fn();
    const { getByRole } = render(
      <SearchBar
        query=""
        stages={[]}
        needsAttention={false}
        onQueryChange={noop}
        onToggleStage={onToggleStage}
        onToggleNeedsAttention={noop}
      />,
    );
    fireEvent.click(getByRole("button", { name: /design/i }));
    expect(onToggleStage).toHaveBeenCalledWith("design");
  });

  it("marks an active stage chip as pressed (aria-pressed)", () => {
    const { getByRole } = render(
      <SearchBar
        query=""
        stages={["design"]}
        needsAttention={false}
        onQueryChange={noop}
        onToggleStage={noop}
        onToggleNeedsAttention={noop}
      />,
    );
    expect(getByRole("button", { name: /design/i })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("toggles needs-attention when its chip is clicked (FR-12) and reflects pressed state", () => {
    const onToggleNeedsAttention = vi.fn();
    const { getByRole, rerender } = render(
      <SearchBar
        query=""
        stages={[]}
        needsAttention={false}
        onQueryChange={noop}
        onToggleStage={noop}
        onToggleNeedsAttention={onToggleNeedsAttention}
      />,
    );
    const chip = getByRole("button", { name: /needs attention/i });
    expect(chip).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(chip);
    expect(onToggleNeedsAttention).toHaveBeenCalledTimes(1);
    rerender(
      <SearchBar
        query=""
        stages={[]}
        needsAttention={true}
        onQueryChange={noop}
        onToggleStage={noop}
        onToggleNeedsAttention={onToggleNeedsAttention}
      />,
    );
    expect(getByRole("button", { name: /needs attention/i })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("has no WCAG AA violations (jest-axe, WPF-06)", async () => {
    const { container } = render(
      <SearchBar
        query=""
        stages={[]}
        needsAttention={false}
        onQueryChange={noop}
        onToggleStage={noop}
        onToggleNeedsAttention={noop}
      />,
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});

// ─── Layer 1b: <SearchBar> mobile lane-switcher tablist (WP-008, ADR-004) ────
//
// The SAME stage chips gain a width-conditional dual role: filter chips on
// desktop (Layer 1 above — aria-pressed toggles, preserved) AND an ARIA
// tablist lane switcher on mobile (role="tablist" / role="tab" /
// aria-selected). jsdom can't compute the media-query breakpoint, so BOTH
// containers are in the DOM and CSS hides one per width; these tests pin the
// tablist's ARIA contract + behaviour. The selected-tab↔visible-lane scroll
// sync + swipe-follows-rail are browser-only and covered by the Playwright
// journey (S-8). Counts come from the board (one feed, no extra request).

describe("<SearchBar> mobile lane-switcher tablist (WP-008 / S-29)", () => {
  function noop() {}

  const counts = {
    recon: 5,
    specify: 1,
    design: 0,
    implement: 3,
    review: 2,
    ship: 3,
  } as const;

  function renderSwitcher(
    props: Partial<Parameters<typeof SearchBar>[0]> = {},
  ) {
    return render(
      <SearchBar
        query=""
        stages={[]}
        needsAttention={false}
        onQueryChange={noop}
        onToggleStage={noop}
        onToggleNeedsAttention={noop}
        counts={counts}
        selectedStage="recon"
        onSelectStage={noop}
        {...props}
      />,
    );
  }

  it("renders a role=tablist labelled 'Pick a stage to view'", () => {
    const { getByRole } = renderSwitcher();
    expect(
      getByRole("tablist", { name: /pick a stage to view/i }),
    ).toBeInTheDocument();
  });

  it("exposes each stage chip as a role=tab carrying aria-selected + aria-controls=lane-<stage>, with its lane count", () => {
    const { getByRole } = renderSwitcher();
    const tablist = getByRole("tablist", { name: /pick a stage to view/i });
    const recon = within(tablist).getByRole("tab", { name: /recon/i });
    expect(recon).toHaveAttribute("aria-selected", "true");
    expect(recon).toHaveAttribute("aria-controls", "lane-recon");
    expect(recon).toHaveTextContent("5"); // the lane's count is on the chip
    const design = within(tablist).getByRole("tab", { name: /design/i });
    expect(design).toHaveAttribute("aria-selected", "false");
    expect(design).toHaveTextContent("0"); // a zero-change lane still shows its count
  });

  it("activating a tab selects its lane (calls onSelectStage with that stage)", () => {
    const onSelectStage = vi.fn();
    const { getByRole } = renderSwitcher({ onSelectStage });
    const tablist = getByRole("tablist", { name: /pick a stage to view/i });
    fireEvent.click(within(tablist).getByRole("tab", { name: /implement/i }));
    expect(onSelectStage).toHaveBeenCalledWith("implement");
  });

  it("reflects the currently-selected lane: only that stage's tab is aria-selected", () => {
    const { getByRole } = renderSwitcher({ selectedStage: "review" });
    const tablist = getByRole("tablist", { name: /pick a stage to view/i });
    expect(
      within(tablist).getByRole("tab", { name: /review/i }),
    ).toHaveAttribute("aria-selected", "true");
    expect(
      within(tablist).getByRole("tab", { name: /recon/i }),
    ).toHaveAttribute("aria-selected", "false");
  });

  it("keeps 'Needs attention' in the rail as an aria-pressed toggle (not a tab)", () => {
    // The toggle lives in the switcher RAIL but OUTSIDE the role=tablist (a
    // tablist may only own tabs — W3C ARIA; a non-tab child would break
    // aria-required-children). So it is scoped to the rail container, not the
    // tablist element.
    const onToggleNeedsAttention = vi.fn();
    const { getByTestId, rerender } = renderSwitcher({
      onToggleNeedsAttention,
    });
    const rail = getByTestId("lane-switcher");
    const attn = within(rail).getByRole("button", {
      name: /needs attention/i,
    });
    // It is a toggle, NOT a tab (tabs pick a lane; this filters).
    expect(attn).toHaveAttribute("aria-pressed", "false");
    expect(attn).not.toHaveAttribute("role", "tab");
    fireEvent.click(attn);
    expect(onToggleNeedsAttention).toHaveBeenCalledTimes(1);
    rerender(
      <SearchBar
        query=""
        stages={[]}
        needsAttention={true}
        onQueryChange={noop}
        onToggleStage={noop}
        onToggleNeedsAttention={onToggleNeedsAttention}
        counts={counts}
        selectedStage="recon"
        onSelectStage={noop}
      />,
    );
    expect(
      within(getByTestId("lane-switcher")).getByRole("button", {
        name: /needs attention/i,
      }),
    ).toHaveAttribute("aria-pressed", "true");
  });

  it("collapses the search to a reachable icon tap-target in the rail", () => {
    const { getByTestId } = renderSwitcher();
    const rail = getByTestId("lane-switcher");
    // The collapsed search affordance has an accessible name and is a button,
    // in the rail (outside the tablist, like the needs-attention toggle).
    expect(
      within(rail).getByRole("button", { name: /search/i }),
    ).toBeInTheDocument();
  });

  it("has no WCAG AA violations in the tablist role (jest-axe, WPF-06 — the dual role's mobile half)", async () => {
    // The tabs' aria-controls point at the lane elements (id=lane-<stage>),
    // which live in StageColumn — rendered separately in the real Board. Render
    // stub lane targets alongside so the ARIA association resolves (a dangling
    // aria-controls is itself an axe violation), mirroring the assembled board.
    const { container } = render(
      <div>
        <SearchBar
          query=""
          stages={[]}
          needsAttention={false}
          onQueryChange={noop}
          onToggleStage={noop}
          onToggleNeedsAttention={noop}
          counts={counts}
          selectedStage="recon"
          onSelectStage={noop}
        />
        {(
          ["recon", "specify", "design", "implement", "review", "ship"] as const
        ).map((stage) => (
          <section
            key={stage}
            id={`lane-${stage}`}
            aria-label={`${stage} lane`}
          />
        ))}
      </div>,
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});

// ─── Layer 2: board wiring — filters narrow the SAME board (ADR-005) ─────────

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
          <Route
            path="/c/:changeId"
            element={<div data-testid="thread-view" />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

/**
 * Route the mocked fetch: `/api/changes` returns the full board; `/api/search`
 * returns whatever the search args resolve to. The test controls both so it
 * can assert the board narrows to the search results.
 */
function mockApi(opts: {
  changes: Change[];
  onSearch: (url: URL) => Change[];
}) {
  vi.spyOn(globalThis, "fetch").mockImplementation(
    (input: RequestInfo | URL) => {
      const raw = typeof input === "string" ? input : input.toString();
      const url = new URL(raw, "http://localhost");
      if (url.pathname === "/api/search") {
        return Promise.resolve(
          jsonResponse(200, { results: opts.onSearch(url) }),
        );
      }
      // default: the full board list
      return Promise.resolve(jsonResponse(200, opts.changes));
    },
  );
}

describe("Board wiring — the toolbar narrows the SAME board (ADR-005)", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockReset();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the search toolbar above the board", async () => {
    mockApi({
      changes: [makeChange({ changeId: "01A", handle: "CH-01A" })],
      onSearch: () => [],
    });
    const { findByRole } = renderBoard(freshClient());
    expect(await findByRole("search")).toBeInTheDocument();
  });

  it("typing a term narrows the SAME board to the matching changes (FR-10) — no separate results screen", async () => {
    const all = [
      makeChange({ changeId: "01HIT", handle: "CH-01HIT", stage: "design" }),
      makeChange({ changeId: "01MISS", handle: "CH-01MISS", stage: "design" }),
    ];
    mockApi({
      changes: all,
      onSearch: (url) =>
        url.searchParams.get("q") === "marshmallow" ? [all[0]!] : all,
    });
    const { findByText, getByRole, queryByText, getByTestId } =
      renderBoard(freshClient());
    // Full board first.
    await findByText("CH-01HIT");
    expect(getByText0(queryByText, "CH-01MISS")).toBe(true);

    // Type a content-only term → the board narrows to the one match, and it
    // is still the board (the stage columns), not a new screen.
    fireEvent.change(getByRole("searchbox"), {
      target: { value: "marshmallow" },
    });
    // Wait for the narrowed result to land (the loading flicker between the
    // full list and the search can briefly hide both rows).
    await findByText("CH-01HIT");
    await waitFor(() => {
      expect(queryByText("CH-01MISS")).not.toBeInTheDocument();
    });
    expect(getByTestId("board")).toBeInTheDocument();
    expect(
      within(getByTestId("board")).getByText("CH-01HIT"),
    ).toBeInTheDocument();
  });

  it("the needs-attention filter narrows the board to flagged changes (FR-12)", async () => {
    const all = [
      makeChange({ changeId: "01FLAG", handle: "CH-01FLAG", stage: "design" }),
      makeChange({ changeId: "01IDLE", handle: "CH-01IDLE", stage: "design" }),
    ];
    mockApi({
      changes: all,
      onSearch: (url) =>
        url.searchParams.get("needsAttention") === "true" ? [all[0]!] : all,
    });
    const { findByText, getByRole, queryByText } = renderBoard(freshClient());
    await findByText("CH-01IDLE");
    // The board now renders BOTH the desktop filter toolbar and the mobile
    // lane-switcher rail (CSS shows one per breakpoint; jsdom renders both), so
    // "Needs attention" appears twice. Click the DESKTOP filter chip — it lives
    // in the role="search" toolbar — to exercise the filter path under test.
    fireEvent.click(
      within(getByRole("search")).getByRole("button", {
        name: /needs attention/i,
      }),
    );
    // The board narrows to the one flagged change; wait for the positive
    // condition (the loading flicker between the two queries can briefly
    // hide both, so assert on the result, not the absence).
    await findByText("CH-01FLAG");
    await waitFor(() => {
      expect(queryByText("CH-01IDLE")).not.toBeInTheDocument();
    });
    expect(queryByText("CH-01FLAG")).toBeInTheDocument();
  });

  it("clearing the search restores the full board (ADR-005)", async () => {
    const all = [
      makeChange({ changeId: "01HIT", handle: "CH-01HIT", stage: "design" }),
      makeChange({ changeId: "01MISS", handle: "CH-01MISS", stage: "design" }),
    ];
    mockApi({
      changes: all,
      onSearch: (url) => (url.searchParams.get("q") ? [all[0]!] : all),
    });
    const { findByText, getByRole, queryByText } = renderBoard(freshClient());
    await findByText("CH-01MISS");
    // Narrow.
    fireEvent.change(getByRole("searchbox"), { target: { value: "x" } });
    await findByText("CH-01HIT");
    await waitFor(() => {
      expect(queryByText("CH-01MISS")).not.toBeInTheDocument();
    });
    // Clear → the full board returns.
    fireEvent.change(getByRole("searchbox"), { target: { value: "" } });
    await waitFor(() => {
      expect(queryByText("CH-01MISS")).toBeInTheDocument();
    });
  });
});

/** Tiny helper: assert a queryByText found an element (kept terse + typed). */
function getByText0(
  queryByText: (text: string) => HTMLElement | null,
  text: string,
): boolean {
  return queryByText(text) !== null;
}
