// WP-008 — assign-from-card accessibility audit. jest-axe over the card's
// product placement in BOTH themes, for both product states:
//   - unassigned → the always-in-DOM "＋ Product" affordance (≥44px target,
//     accessible name "Add this change to a product");
//   - assigned   → the quiet monogram chip in the foot-meta.
//
// jsdom doesn't compute layout, so axe validates the STRUCTURAL a11y (roles /
// names / aria / no nested-interactive). The card renders as a <Link> (<a>);
// the affordance is a <button> — so it must sit OUTSIDE the anchor (interactive
// content can't nest in <a>), which axe's nested-interactive rule enforces here.

import { describe, it, expect, afterEach } from "vitest";
import { render } from "@testing-library/react";
import { axe } from "jest-axe";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import type { Change, Product } from "../../../shared/api-types";
import { ChangeCard } from "../components/ChangeCard";

const ACME = "dna:product:01ACME00000000000000000000";

const PRODUCTS: Product[] = [{ productId: ACME, name: "Acme" }];

function makeChange(overrides: Partial<Change> = {}): Change {
  return {
    changeId: "01CARD",
    handle: "CH-01CARD",
    slug: "assign-from-card",
    primitive: "feat",
    branch: "feat/x",
    worktreePath: "/w",
    intent: "assign a product straight from the board card",
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

function setTheme(theme: "light" | "dark") {
  if (theme === "dark") document.documentElement.dataset.theme = "dark";
  else delete document.documentElement.dataset.theme;
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

const VARIANTS: Record<string, Partial<Change>> = {
  unassigned: { forProduct: null },
  assigned: { forProduct: ACME },
};

describe("<ChangeCard> product placement WCAG AA, light + dark (WP-008)", () => {
  afterEach(() => {
    delete document.documentElement.dataset.theme;
  });

  for (const theme of ["light", "dark"] as const) {
    for (const [name, overrides] of Object.entries(VARIANTS)) {
      it(`${theme} · ${name} card has no axe violations`, async () => {
        setTheme(theme);
        const { container, findByTestId, findByRole } = renderCard(
          makeChange(overrides),
        );
        // Wait for the products query to settle so the placement is rendered.
        if (name === "assigned") await findByTestId("card-product-chip");
        else
          await findByRole("button", { name: "Add this change to a product" });
        const results = await axe(container);
        expect(results).toHaveNoViolations();
      });
    }
  }
});
