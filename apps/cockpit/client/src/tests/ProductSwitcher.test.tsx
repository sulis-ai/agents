// WP-005 — <ProductSwitcher> refined (ADR-002, REORGANISE-Refactor).
//
// The switcher now renders the shared <ProductControl mode="scope"> primitive
// (WP-002) rather than its own bespoke menu — one product vocabulary across the
// three homes (the switcher, the change-nav property, the board card). The
// refinement (signed design, Concerns A1 + C1):
//   - "All products" is an everything-tile (grid glyph) row, count = total;
//   - "Unassigned" is a first-class scope (dashed glyph), count = changes with
//     no product — a CLIENT-derived scope (the server has no "unassigned"
//     value; it is rendered by filtering the All-scoped feed, TDD);
//   - every row carries a live count, folded into its accessible name
//     ("All products, 23 changes");
//   - the header echoes the active scope ("Viewing <scope> · N changes") with
//     a one-tap "× clear" back to All when scoped to a product.
//
// CHARACTERISATION (REORGANISE MUST, ADR-002 / EP-07): the EXTERNAL re-scope
// behaviour the old switcher guaranteed is PRESERVED and pinned below — the
// behaviour, not the bespoke DOM, is the contract:
//   - selecting "All products" emits onSelect(null);
//   - selecting a product emits onSelect(productId);
//   - selecting re-scopes only — it fires onSelect and NEVER a network mutation
//     (read-only, FR-38);
//   - the monogram() helper is still exported (reused by ProductControl +
//     OnboardingChat, EP-03).
// The internal swap to <ProductControl> legitimately changes the test ids /
// markup — that is the refactor (ADR-002), and the primitive's own a11y model
// is exhaustively covered by ProductControl.test.tsx; here we pin the switcher
// PLACEMENT (rows wired, counts derived, header echo + clear).
//
// Consumes tokens.css only (no invented colours).

import { describe, it, expect, vi } from "vitest";
import { render, within, fireEvent } from "@testing-library/react";
import { axe } from "jest-axe";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import type { Change, Product } from "../../../shared/api-types";
import { ProductSwitcher, monogram } from "../components/ProductSwitcher";
import { UNASSIGNED_SCOPE } from "../lib/productCounts";

function readSwitcherCss(): string {
  const candidates = [
    resolve(process.cwd(), "src/components/ProductSwitcher.module.css"),
    resolve(process.cwd(), "client/src/components/ProductSwitcher.module.css"),
  ];
  const cssPath = candidates.find((p) => existsSync(p));
  expect(cssPath, "ProductSwitcher.module.css must be locatable").toBeTruthy();
  return readFileSync(cssPath as string, "utf8");
}

const ACME = "dna:product:01ACME00000000000000000000";
const HELP = "dna:product:01HELP00000000000000000000";

function product(overrides: Partial<Product> = {}): Product {
  return { productId: ACME, name: "Acme Checkout", ...overrides };
}

const TWO_PRODUCTS: Product[] = [
  product({ productId: ACME, name: "Acme Checkout", active: true }),
  product({ productId: HELP, name: "Helpdesk" }),
];

function change(overrides: Partial<Change> = {}): Change {
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

// 3 Acme, 2 Helpdesk, 2 unassigned → All = 7, Unassigned = 2.
const CHANGES: Change[] = [
  change({ changeId: "a1", forProduct: ACME }),
  change({ changeId: "a2", forProduct: ACME }),
  change({ changeId: "a3", forProduct: ACME }),
  change({ changeId: "h1", forProduct: HELP }),
  change({ changeId: "h2", forProduct: HELP }),
  change({ changeId: "u1", forProduct: null }),
  change({ changeId: "u2" }),
];

function openMenu(getByTestId: (id: string) => HTMLElement): HTMLElement {
  fireEvent.click(getByTestId("product-control-trigger"));
  return getByTestId("product-control-menu");
}

describe("<ProductSwitcher> — characterisation (re-scope behaviour preserved)", () => {
  it("exports the monogram() helper (reused by ProductControl + OnboardingChat, EP-03)", () => {
    expect(monogram("Acme Checkout")).toBe("AC");
    expect(monogram("Sulis")).toBe("SU");
  });

  it("selecting a product emits onSelect(productId) — the switch", () => {
    const onSelect = vi.fn();
    const { getByTestId } = render(
      <ProductSwitcher
        products={TWO_PRODUCTS}
        activeProductId={null}
        changes={CHANGES}
        onSelect={onSelect}
      />,
    );
    const menu = openMenu(getByTestId);
    fireEvent.click(within(menu).getByText("Helpdesk"));
    expect(onSelect).toHaveBeenCalledWith(HELP);
  });

  it("selecting 'All products' from a scoped state clears back to All — onSelect(null)", () => {
    const onSelect = vi.fn();
    const { getByTestId } = render(
      <ProductSwitcher
        products={TWO_PRODUCTS}
        activeProductId={HELP}
        changes={CHANGES}
        onSelect={onSelect}
      />,
    );
    const menu = openMenu(getByTestId);
    fireEvent.click(within(menu).getByText("All products"));
    expect(onSelect).toHaveBeenCalledWith(null);
  });

  it("performs no mutation — selecting fires only onSelect, never fetch (read-only)", () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const { getByTestId } = render(
      <ProductSwitcher
        products={TWO_PRODUCTS}
        activeProductId={null}
        changes={CHANGES}
        onSelect={() => {}}
      />,
    );
    const menu = openMenu(getByTestId);
    fireEvent.click(within(menu).getByText("Helpdesk"));
    expect(fetchSpy).not.toHaveBeenCalled();
    fetchSpy.mockRestore();
  });

  it("renders nothing when the Tenant has no products", () => {
    const { container } = render(
      <ProductSwitcher
        products={[]}
        activeProductId={null}
        changes={[]}
        onSelect={() => {}}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("offers 'Set up a new product' when onSetUpNew is wired", () => {
    const onSetUpNew = vi.fn();
    const { getByTestId } = render(
      <ProductSwitcher
        products={TWO_PRODUCTS}
        activeProductId={null}
        changes={CHANGES}
        onSelect={() => {}}
        onSetUpNew={onSetUpNew}
      />,
    );
    const menu = openMenu(getByTestId);
    fireEvent.click(within(menu).getByText(/set up a new product/i));
    expect(onSetUpNew).toHaveBeenCalled();
  });
});

// WP-007 — the setup spine: a quiet "Manage products" foot action beside "Set
// up a new product", routing to Settings (Concern D1). The placement just
// supplies the onManageProducts handler (the consumers wire it to
// navigate("/settings")); ProductControl renders the foot item with its menu
// keyboard model. This pins the named verification scenario "Reach product
// setup from the switcher": the item is present, reachable, and invokes the
// route-to-Settings handler.
describe("<ProductSwitcher> — the 'Manage products' setup-spine foot action (WP-007)", () => {
  it("offers a 'Manage products' foot item that invokes onManageProducts (routes to Settings)", () => {
    const onManageProducts = vi.fn();
    const { getByTestId } = render(
      <ProductSwitcher
        products={TWO_PRODUCTS}
        activeProductId={null}
        changes={CHANGES}
        onSelect={() => {}}
        onSetUpNew={() => {}}
        onManageProducts={onManageProducts}
      />,
    );
    const menu = openMenu(getByTestId);
    fireEvent.click(within(menu).getByText(/manage products/i));
    expect(onManageProducts).toHaveBeenCalledOnce();
  });

  it("renders 'Manage products' as a real keyboard-reachable menu item with icon AND word (never icon-only)", () => {
    const { getByTestId } = render(
      <ProductSwitcher
        products={TWO_PRODUCTS}
        activeProductId={null}
        changes={CHANGES}
        onSelect={() => {}}
        onSetUpNew={() => {}}
        onManageProducts={() => {}}
      />,
    );
    const menu = openMenu(getByTestId);
    // A real menu item (keyboard-reachable as a <button role="menuitem">), not
    // a bare icon: it carries the visible word "Manage products" as its
    // accessible name (icon + word, never icon-only — WP Contract).
    const item = within(menu).getByRole("menuitem", { name: /manage products/i });
    expect(item.tagName).toBe("BUTTON");
    expect(item.textContent).toMatch(/manage products/i);
  });

  it("omits the 'Manage products' item when onManageProducts is not wired (no dead affordance)", () => {
    const { getByTestId } = render(
      <ProductSwitcher
        products={TWO_PRODUCTS}
        activeProductId={null}
        changes={CHANGES}
        onSelect={() => {}}
        onSetUpNew={() => {}}
      />,
    );
    const menu = openMenu(getByTestId);
    expect(within(menu).queryByText(/manage products/i)).not.toBeInTheDocument();
  });
});

describe("<ProductSwitcher> — the refined scope rows (All products + Unassigned + counts)", () => {
  it("renders 'All products' with an everything (grid) tile, ticked when active, count = total", () => {
    const { getByTestId } = render(
      <ProductSwitcher
        products={TWO_PRODUCTS}
        activeProductId={null}
        changes={CHANGES}
        onSelect={() => {}}
      />,
    );
    const menu = openMenu(getByTestId);
    const all = within(menu).getByRole("menuitemradio", { name: /all products, 7 changes/i });
    expect(all).toHaveAttribute("aria-checked", "true");
    // The everything-tile is a grid glyph, NOT a two-letter monogram.
    expect(all.querySelector('[data-glyph="all-grid"]')).toBeInTheDocument();
  });

  it("renders 'Unassigned' as a first-class scope with a dashed tile and its count", () => {
    const { getByTestId } = render(
      <ProductSwitcher
        products={TWO_PRODUCTS}
        activeProductId={null}
        changes={CHANGES}
        onSelect={() => {}}
      />,
    );
    const menu = openMenu(getByTestId);
    const unassigned = within(menu).getByRole("menuitemradio", {
      name: /unassigned, 2 changes/i,
    });
    expect(unassigned.querySelector('[data-glyph="unassigned-dashed"]')).toBeInTheDocument();
  });

  it("selecting 'Unassigned' emits onSelect(UNASSIGNED_SCOPE) — a client-filtered scope", () => {
    const onSelect = vi.fn();
    const { getByTestId } = render(
      <ProductSwitcher
        products={TWO_PRODUCTS}
        activeProductId={null}
        changes={CHANGES}
        onSelect={onSelect}
      />,
    );
    const menu = openMenu(getByTestId);
    fireEvent.click(within(menu).getByRole("menuitemradio", { name: /unassigned, 2 changes/i }));
    expect(onSelect).toHaveBeenCalledWith(UNASSIGNED_SCOPE);
  });

  it("carries a live per-product count on every product row (in the accessible name)", () => {
    const { getByTestId } = render(
      <ProductSwitcher
        products={TWO_PRODUCTS}
        activeProductId={null}
        changes={CHANGES}
        onSelect={() => {}}
      />,
    );
    const menu = openMenu(getByTestId);
    expect(
      within(menu).getByRole("menuitemradio", { name: /acme checkout, 3 changes/i }),
    ).toBeInTheDocument();
    expect(
      within(menu).getByRole("menuitemradio", { name: /helpdesk, 2 changes/i }),
    ).toBeInTheDocument();
  });

  it("a stale activeProductId (no matching product) reads as All — header + the ticked row agree", () => {
    // Safe fallback (preserves the old switcher's behaviour): an id that
    // matches no known product never leaves a blank header or an orphaned
    // tick — it reads as All, and the All row is the ticked one.
    const { getByTestId } = render(
      <ProductSwitcher
        products={TWO_PRODUCTS}
        activeProductId="dna:product:01STALE000000000000000000"
        changes={CHANGES}
        onSelect={() => {}}
      />,
    );
    expect(getByTestId("product-scope-header").textContent).toMatch(/all products/i);
    const menu = openMenu(getByTestId);
    const checked = within(menu)
      .getAllByRole("menuitemradio")
      .filter((el) => el.getAttribute("aria-checked") === "true");
    expect(checked).toHaveLength(1);
    expect(checked[0]?.textContent).toContain("All products");
  });

  it("ticks the Unassigned row when the Unassigned scope is active (exactly one ticked row)", () => {
    const { getByTestId } = render(
      <ProductSwitcher
        products={TWO_PRODUCTS}
        activeProductId={UNASSIGNED_SCOPE}
        changes={CHANGES}
        onSelect={() => {}}
      />,
    );
    const menu = openMenu(getByTestId);
    const checked = within(menu)
      .getAllByRole("menuitemradio")
      .filter((el) => el.getAttribute("aria-checked") === "true");
    expect(checked).toHaveLength(1);
    expect(checked[0]?.textContent).toContain("Unassigned");
  });
});

describe("<ProductSwitcher> — the header echo ('Viewing <scope>') + × clear", () => {
  it("echoes 'Viewing All products · 7 changes' at the All scope, with NO clear button", () => {
    const { getByTestId, queryByRole } = render(
      <ProductSwitcher
        products={TWO_PRODUCTS}
        activeProductId={null}
        changes={CHANGES}
        onSelect={() => {}}
      />,
    );
    const echo = getByTestId("product-scope-header");
    expect(echo.textContent).toMatch(/viewing/i);
    expect(echo.textContent).toMatch(/all products/i);
    expect(echo.textContent).toMatch(/7 changes/i);
    // At the All scope there is nothing to clear back to.
    expect(queryByRole("button", { name: /clear scope/i })).not.toBeInTheDocument();
  });

  it("echoes the product scope with a count and a '× clear' that returns to All", () => {
    const onSelect = vi.fn();
    const { getByTestId, getByRole } = render(
      <ProductSwitcher
        products={TWO_PRODUCTS}
        activeProductId={ACME}
        changes={CHANGES}
        onSelect={onSelect}
      />,
    );
    const echo = getByTestId("product-scope-header");
    expect(echo.textContent).toMatch(/viewing/i);
    expect(echo.textContent).toMatch(/acme checkout/i);
    expect(echo.textContent).toMatch(/3 changes/i);
    const clear = getByRole("button", { name: /clear scope/i });
    fireEvent.click(clear);
    expect(onSelect).toHaveBeenCalledWith(null);
  });

  it("shows the clear control for the Unassigned scope too (returns to All)", () => {
    const onSelect = vi.fn();
    const { getByTestId, getByRole } = render(
      <ProductSwitcher
        products={TWO_PRODUCTS}
        activeProductId={UNASSIGNED_SCOPE}
        changes={CHANGES}
        onSelect={onSelect}
      />,
    );
    expect(getByTestId("product-scope-header").textContent).toMatch(/unassigned/i);
    fireEvent.click(getByRole("button", { name: /clear scope/i }));
    expect(onSelect).toHaveBeenCalledWith(null);
  });
});

describe("<ProductSwitcher> — accessibility (placement axe check)", () => {
  it("has no axe violations with the menu open at the All scope", async () => {
    const { container, getByTestId } = render(
      <ProductSwitcher
        products={TWO_PRODUCTS}
        activeProductId={null}
        changes={CHANGES}
        onSelect={() => {}}
      />,
    );
    openMenu(getByTestId);
    expect(await axe(container)).toHaveNoViolations();
  });

  it("has no axe violations when scoped to a product (header echo + clear present)", async () => {
    const { container } = render(
      <ProductSwitcher
        products={TWO_PRODUCTS}
        activeProductId={ACME}
        changes={CHANGES}
        onSelect={() => {}}
      />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });

  it("stays token-only — no raw hex colours in ProductSwitcher.module.css", () => {
    const css = readSwitcherCss().replace(/\/\*[\s\S]*?\*\//g, "");
    expect(css).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
  });
});
