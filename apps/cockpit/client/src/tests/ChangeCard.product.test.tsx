// WP-008 — assign-from-card. The board card carries the product vocabulary in
// context: when UNASSIGNED, an always-in-DOM, keyboard-reachable "＋ Product"
// affordance (hover only emphasises it — never controls presence) that opens
// the shared ProductControl popover (mode="assign", compact) so assignment
// happens WITHOUT opening the change; when ASSIGNED, a quiet product monogram
// chip in the foot-meta and the product name rides the card's accessible name.
//
// Assign reuses useAssignChangeProduct verbatim (ADR-002 — the placement wires
// the hook at the edge; ProductControl never touches the network). These tests
// drive the placement's BEHAVIOUR; ChangeCard.product.axe.test.tsx covers the
// shared a11y model across both themes.

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, fireEvent, waitFor, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import type { Change, Product } from "../../../shared/api-types";
import { ChangeCard } from "../components/ChangeCard";

const ACME = "dna:product:01ACME00000000000000000000";
const HARP = "dna:product:01HARP00000000000000000000";

// The products list is INJECTED into the card (ADR-002 — the card never
// fetches); the board threads its one already-fetched list to every card.
const PRODUCTS: Product[] = [
  { productId: ACME, name: "Acme" },
  { productId: HARP, name: "Helpdesk" },
];

function jsonRes(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}

/** Mock only the assign PUT — the one endpoint the card's product placement
 *  touches (assignment via useAssignChangeProduct). Products are injected. */
function mockAssign() {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
    const u = String(url);
    if (u.includes("/api/changes/") && init?.method === "PUT") {
      return jsonRes({ ok: true, id: "dna:change:01CARD", forProduct: HARP });
    }
    return jsonRes({});
  });
}

function makeChange(overrides: Partial<Change> = {}): Change {
  return {
    changeId: "01CARD",
    handle: "CH-01CARD",
    slug: "assign-from-card",
    primitive: "feat",
    branch: "feat/x",
    worktreePath: "/w",
    intent: "let the founder assign a product straight from the board card",
    baseBranch: "dev",
    baseSha: null,
    createdAt: "2026-06-16T10:00:00Z",
    updatedAt: "2026-06-16T11:00:00Z",
    stage: "implement",
    liveness: { status: "running", pid: 1 },
    needsAttention: { flagged: false, reason: null },
    health: { state: "on-track", reason: "tests green" },
    lastActivityAt: "2026-06-16T10:59:50Z",
    forProduct: null,
    ...overrides,
  };
}

function renderCard(change: Change) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ChangeCard change={change} products={PRODUCTS} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("<ChangeCard> assign-from-card (WP-008)", () => {
  beforeEach(() => {
    mockAssign();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("an UNASSIGNED card shows an always-in-DOM, keyboard-reachable ＋ Product affordance with the right accessible name", async () => {
    const { findByRole } = renderCard(makeChange({ forProduct: null }));

    // The affordance is a real, focusable control present in the DOM regardless
    // of hover (keyboard/touch parity). Its accessible name names the action.
    const trigger = await findByRole("button", {
      name: "Add this change to a product",
    });
    expect(trigger).toBeInTheDocument();
    // Keyboard-reachable: a native <button> is in the tab order (not tabindex=-1).
    expect(trigger).not.toHaveAttribute("tabindex", "-1");
  });

  it("activating the affordance opens the ProductControl popover (assign mode) — assignment happens without opening the change", async () => {
    const { findByRole, getByTestId } = renderCard(
      makeChange({ forProduct: null }),
    );

    const trigger = await findByRole("button", {
      name: "Add this change to a product",
    });
    fireEvent.click(trigger);

    // The shared popover opens in place — no navigation to /c/:id needed.
    const menu = await waitFor(() => getByTestId("product-control-menu"));
    expect(menu).toBeInTheDocument();
    expect(
      within(menu).getByRole("menuitemradio", { name: /Acme/ }),
    ).toBeInTheDocument();
  });

  it("assigning from the card commits via useAssignChangeProduct (a PUT) without navigating", async () => {
    const fetchMock = mockAssign();
    const { findByRole, getByTestId } = renderCard(
      makeChange({ forProduct: null }),
    );

    const trigger = await findByRole("button", {
      name: "Add this change to a product",
    });
    fireEvent.click(trigger);
    const menu = await waitFor(() => getByTestId("product-control-menu"));
    fireEvent.click(
      within(menu).getByRole("menuitemradio", { name: /Helpdesk/ }),
    );

    // The assign hook fires a PUT to the change's product endpoint — assignment
    // commits in place, no route change.
    await waitFor(() => {
      const put = fetchMock.mock.calls.find(
        ([url, init]) =>
          String(url).includes("/api/changes/") &&
          (init as RequestInit | undefined)?.method === "PUT",
      );
      expect(put).toBeTruthy();
    });
  });

  it("an ASSIGNED card shows a quiet monogram chip in the foot-meta and carries the product name in its accessible name", async () => {
    const { findByTestId, getByRole } = renderCard(
      makeChange({ forProduct: ACME }),
    );

    // The quiet product chip rides the card foot when assigned.
    const chip = await findByTestId("card-product-chip");
    expect(chip).toBeInTheDocument();
    expect(chip).toHaveTextContent(/Acme/);

    // The product name is part of the card's accessible name so a screen reader
    // hears which product the change belongs to.
    expect(getByRole("link", { name: /Acme/ })).toBeInTheDocument();
  });

  it("does NOT render the ＋ Product affordance when the card is already assigned (chip replaces it)", async () => {
    const { queryByRole, findByTestId } = renderCard(
      makeChange({ forProduct: ACME }),
    );
    await findByTestId("card-product-chip");
    expect(
      queryByRole("button", { name: "Add this change to a product" }),
    ).not.toBeInTheDocument();
  });
});
