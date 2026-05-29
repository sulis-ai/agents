// WP-003 — <ContractLinks> tests (WPF-05 states, WPF-06 a11y gate).
//
// The per-change "open data contract / open UI" affordances. Coverage:
//   - loading state while the summary is fetched;
//   - error state on a failed fetch (with retry);
//   - ready + UI present  → two links, each pointing at THIS change's
//     own /contract/data + /contract/ui (per-change resolution, ADR-003);
//   - ready + UI none      → data link + a plain "no UI contract" note,
//     never a broken link;
//   - unavailable          → a plain degrade note (shipped change gone);
//   - jest-axe has no WCAG AA violations in the ready state.
//
// Data is fetched through the typed client (apiGet funnel) — never `fetch`
// in the component (WPF-02). The test drives the real hook against a mocked
// global fetch, the same substrate every other client test uses.

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, waitFor, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { axe } from "jest-axe";
import type { Change } from "../../../shared/api-types";
import { ContractLinks } from "../components/ContractLinks";

function makeChange(overrides: Partial<Change> = {}): Change {
  return {
    changeId: "01ABC",
    handle: "CH-01ABC",
    slug: "demo",
    primitive: "create",
    branch: "change/demo",
    worktreePath: "/tmp/worktree",
    intent: "Demo change",
    baseBranch: "main",
    baseSha: "abc123",
    createdAt: "2026-05-26T11:00:00Z",
    updatedAt: "2026-05-26T11:55:00Z",
    stage: "design",
    liveness: { status: "not-running" },
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

function renderLinks(change: Change, client = freshClient()) {
  return render(
    <QueryClientProvider client={client}>
      <ContractLinks change={change} />
    </QueryClientProvider>,
  );
}

describe("<ContractLinks>", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockReset();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders a loading state while the summary is fetched", () => {
    vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise(() => {}));
    const { getByTestId } = renderLinks(makeChange());
    expect(getByTestId("contract-links-loading")).toBeInTheDocument();
  });

  it("renders an error state with a retry on failure", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(500, { error: "boom", code: "INTERNAL_ERROR" }),
    );
    const { getByRole, getByText } = renderLinks(makeChange());
    await waitFor(() =>
      expect(getByText(/load the contract preview/i)).toBeInTheDocument(),
    );
    expect(getByRole("button", { name: /retry/i })).toBeInTheDocument();
  });

  it("ready + UI present → two links, each pointing at THIS change's own contracts", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(200, {
        status: "ready",
        present: true,
        dataContract: { format: "servicespec", name: "Platforms" },
        uiContract: { status: "present" },
      }),
    );
    const change = makeChange({ changeId: "01OWN", handle: "CH-01OWN" });
    const { getByRole } = renderLinks(change);

    const dataLink = await waitFor(() =>
      getByRole("link", { name: /open data contract/i }),
    );
    const uiLink = getByRole("link", { name: /open ui|open visual/i });

    // Per-change resolution: each href carries THIS change's id (ADR-003).
    expect(dataLink).toHaveAttribute(
      "href",
      "/api/changes/01OWN/contract/data",
    );
    expect(uiLink).toHaveAttribute("href", "/api/changes/01OWN/contract/ui");
  });

  it("ready + UI none → data link + a plain note, never a broken UI link", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(200, {
        status: "ready",
        present: true,
        dataContract: { format: "openapi", name: null },
        uiContract: {
          status: "none",
          note: "No UI contract for this change — it carries no visual contract.",
        },
      }),
    );
    const { getByRole, getByText, queryByRole } = renderLinks(makeChange());

    await waitFor(() =>
      expect(
        getByRole("link", { name: /open data contract/i }),
      ).toBeInTheDocument(),
    );
    // No UI link rendered…
    expect(queryByRole("link", { name: /open ui|open visual/i })).toBeNull();
    // …instead a plain note.
    expect(getByText(/no ui contract for this change/i)).toBeInTheDocument();
  });

  it("ready but nothing rendered yet (present:false) → a 'not rendered yet' note, no links", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(200, {
        status: "ready",
        present: false,
        dataContract: null,
        uiContract: { status: "none", note: "No UI contract." },
      }),
    );
    const { getByTestId, queryByRole } = renderLinks(makeChange());
    await waitFor(() =>
      expect(getByTestId("contract-links-not-rendered")).toBeInTheDocument(),
    );
    expect(queryByRole("link", { name: /open data contract/i })).toBeNull();
  });

  it("unavailable → a plain degrade note (no links)", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(200, {
        status: "unavailable",
        note: "couldn't reach this shipped change's contracts",
      }),
    );
    const { getByText, queryByRole } = renderLinks(makeChange());
    await waitFor(() =>
      expect(
        getByText(/couldn't reach this shipped change's contracts/i),
      ).toBeInTheDocument(),
    );
    expect(queryByRole("link", { name: /open data contract/i })).toBeNull();
  });

  it("has no WCAG AA violations in the ready state (jest-axe)", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(200, {
        status: "ready",
        present: true,
        dataContract: { format: "servicespec", name: "Platforms" },
        uiContract: { status: "present" },
      }),
    );
    const { container, getByRole } = renderLinks(makeChange());
    await waitFor(() => getByRole("link", { name: /open data contract/i }));
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
