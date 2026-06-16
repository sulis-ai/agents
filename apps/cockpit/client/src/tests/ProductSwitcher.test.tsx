// WP-008 — <ProductSwitcher> tests (FR-38, UC-11; ADR-009).
//
// Journey K round-trip, client half: a top-left active-Product control —
// a neutral two-letter monogram tile + the active Product's name + a
// chevron — that opens a menu listing the Tenant's Products (active one
// ticked) plus "set up a new product". Selecting another Product re-scopes
// the board + search/filters to it (the parent owns the active-product
// state; the switcher emits onSelect).
//
// Matches the SIGNED visual contract (sulis-app.html .pswitch/.pmenu): the
// avatar is a NEUTRAL monogram tile (deliberately not brand-coloured —
// chrome, not decoration), consumes tokens.css only.
//
// Read-only (FR-38): selecting a Product performs ZERO writes/mints/
// session-starts — it only re-scopes what the seam returns. The switcher
// itself fires only its onSelect callback; it never calls fetch with a
// mutation verb.

import { describe, it, expect, vi } from "vitest";
import { render, within, fireEvent } from "@testing-library/react";
import { axe } from "jest-axe";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import type { Product } from "../../../shared/api-types";
import { ProductSwitcher } from "../components/ProductSwitcher";

function product(overrides: Partial<Product> = {}): Product {
  return {
    productId: "dna:product:01ACME00000000000000000000",
    name: "Acme Checkout",
    ...overrides,
  };
}

const TWO_PRODUCTS: Product[] = [
  product({ productId: "dna:product:01ACME00000000000000000000", name: "Acme Checkout", active: true }),
  product({ productId: "dna:product:01HELP00000000000000000000", name: "Helpdesk" }),
];

describe("<ProductSwitcher>", () => {
  it("renders the active Product's name and a neutral two-letter monogram tile", () => {
    const { getByTestId, getByText } = render(
      <ProductSwitcher
        products={TWO_PRODUCTS}
        activeProductId="dna:product:01ACME00000000000000000000"
        onSelect={() => {}}
      />,
    );
    expect(getByText("Acme Checkout")).toBeInTheDocument();
    // Neutral two-letter monogram (locked decision): "AC" for "Acme Checkout".
    const avatar = getByTestId("product-switcher-avatar");
    expect(avatar.textContent).toBe("AC");
  });

  it("opens a menu listing the Tenant's Products with the active one marked", () => {
    const { getByTestId } = render(
      <ProductSwitcher
        products={TWO_PRODUCTS}
        activeProductId="dna:product:01ACME00000000000000000000"
        onSelect={() => {}}
      />,
    );
    const trigger = getByTestId("product-switcher-trigger");
    expect(trigger.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(trigger);
    expect(trigger.getAttribute("aria-expanded")).toBe("true");

    const menu = getByTestId("product-switcher-menu");
    expect(within(menu).getByText("Acme Checkout")).toBeInTheDocument();
    expect(within(menu).getByText("Helpdesk")).toBeInTheDocument();
    // The active Product is marked (aria-checked) — exactly one.
    const checked = within(menu)
      .getAllByRole("menuitemradio")
      .filter((el) => el.getAttribute("aria-checked") === "true");
    expect(checked).toHaveLength(1);
    expect(checked[0]?.textContent).toContain("Acme Checkout");
  });

  it("re-scopes on select — emits onSelect with the chosen Product id (the switch)", () => {
    const onSelect = vi.fn();
    const { getByTestId } = render(
      <ProductSwitcher
        products={TWO_PRODUCTS}
        activeProductId="dna:product:01ACME00000000000000000000"
        onSelect={onSelect}
      />,
    );
    fireEvent.click(getByTestId("product-switcher-trigger"));
    const menu = getByTestId("product-switcher-menu");
    fireEvent.click(within(menu).getByText("Helpdesk"));
    expect(onSelect).toHaveBeenCalledWith("dna:product:01HELP00000000000000000000");
  });

  it("offers a 'set up a new product' action (the menu's last item)", () => {
    const { getByTestId } = render(
      <ProductSwitcher
        products={TWO_PRODUCTS}
        activeProductId="dna:product:01ACME00000000000000000000"
        onSelect={() => {}}
      />,
    );
    fireEvent.click(getByTestId("product-switcher-trigger"));
    const menu = getByTestId("product-switcher-menu");
    expect(within(menu).getByText(/set up a new product/i)).toBeInTheDocument();
  });

  it("renders the single-Product trivial case (one Product, shown active)", () => {
    const { getByText, getByTestId } = render(
      <ProductSwitcher
        products={[product({ name: "Sulis", active: true })]}
        activeProductId="dna:product:01ACME00000000000000000000"
        onSelect={() => {}}
      />,
    );
    expect(getByText("Sulis")).toBeInTheDocument();
    fireEvent.click(getByTestId("product-switcher-trigger"));
    const menu = getByTestId("product-switcher-menu");
    // The menu always offers "All" (every change) plus each Product: 1 + 1 = 2.
    expect(within(menu).getAllByRole("menuitemradio")).toHaveLength(2);
    expect(within(menu).getByText("All")).toBeInTheDocument();
  });

  it("defaults to the 'All' scope when activeProductId is null — the trigger reads 'All'", () => {
    const { getByText, getByTestId } = render(
      <ProductSwitcher
        products={TWO_PRODUCTS}
        activeProductId={null}
        onSelect={() => {}}
      />,
    );
    // Null scope is "All" — every change shows; Products are filters on top.
    expect(getByText("All")).toBeInTheDocument();
    fireEvent.click(getByTestId("product-switcher-trigger"));
    // "All" is the checked option in the menu.
    expect(getByTestId("product-switcher-all")).toHaveAttribute("aria-checked", "true");
  });

  it("picking a Product filters to it (onSelect(productId))", () => {
    const onSelect = vi.fn();
    const { getByText, getByTestId } = render(
      <ProductSwitcher
        products={TWO_PRODUCTS}
        activeProductId={null}
        onSelect={onSelect}
      />,
    );
    fireEvent.click(getByTestId("product-switcher-trigger"));
    fireEvent.click(getByText("Helpdesk"));
    expect(onSelect).toHaveBeenCalledWith("dna:product:01HELP00000000000000000000");
  });

  it("picking 'All' from a filtered state clears the filter (onSelect(null))", () => {
    const onSelect = vi.fn();
    const { getByTestId } = render(
      <ProductSwitcher
        products={TWO_PRODUCTS}
        activeProductId="dna:product:01HELP00000000000000000000"
        onSelect={onSelect}
      />,
    );
    fireEvent.click(getByTestId("product-switcher-trigger"));
    fireEvent.click(getByTestId("product-switcher-all"));
    expect(onSelect).toHaveBeenCalledWith(null);
  });

  it("performs no mutation — selecting fires only onSelect, never a fetch", () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const { getByTestId } = render(
      <ProductSwitcher
        products={TWO_PRODUCTS}
        activeProductId="dna:product:01ACME00000000000000000000"
        onSelect={() => {}}
      />,
    );
    fireEvent.click(getByTestId("product-switcher-trigger"));
    fireEvent.click(within(getByTestId("product-switcher-menu")).getByText("Helpdesk"));
    expect(fetchSpy).not.toHaveBeenCalled();
    fetchSpy.mockRestore();
  });

  it("has no axe violations", async () => {
    const { container, getByTestId } = render(
      <ProductSwitcher
        products={TWO_PRODUCTS}
        activeProductId="dna:product:01ACME00000000000000000000"
        onSelect={() => {}}
      />,
    );
    fireEvent.click(getByTestId("product-switcher-trigger"));
    expect(await axe(container)).toHaveNoViolations();
  });
});

// ─── Top-bar fit (#216) ────────────────────────────────────────────────
//
// The switcher's styles were ported VERBATIM from the OLD vertical sidebar
// and don't fit the new horizontal 48px top bar (.topbar in
// WorkspaceShell.module.css). The asymmetric vertical margin pushed the
// control up and the trigger's tall padding overflowed the bar so it poked
// out above the top edge. These pin the corrected geometry so the
// regression cannot return. Structural (read the stylesheet text) rather
// than a brittle pixel-render assertion: CSS modules are class-name-mapped
// in jsdom, so computed-style is unreliable — the source IS the contract.
describe("ProductSwitcher.module.css — fits the 48px horizontal top bar", () => {
  function readSwitcherCss(): string {
    // vitest may run from the client dir or the cockpit workspace root;
    // resolve the stylesheet from whichever cwd is in effect (mirrors the
    // ChangeCard stylesheet test).
    const candidates = [
      resolve(process.cwd(), "src/components/ProductSwitcher.module.css"),
      resolve(process.cwd(), "client/src/components/ProductSwitcher.module.css"),
    ];
    const cssPath = candidates.find((p) => existsSync(p));
    expect(cssPath, "ProductSwitcher.module.css must be locatable").toBeTruthy();
    return readFileSync(cssPath as string, "utf8");
  }

  it(".pswitch uses a symmetric zero vertical margin so .brand (align-items:center) centres it", () => {
    const css = readSwitcherCss();
    const block = css.slice(css.indexOf(".pswitch"), css.indexOf(".pstrigger"));
    // The corrected value: no top/bottom margin, 4px sides.
    expect(block).toMatch(/margin:\s*0 4px;/);
    // The OLD vertical-sidebar margin must be gone (it pushed the control up).
    expect(block).not.toMatch(/margin:\s*2px 4px 14px;/);
  });

  it(".pstrigger padding fits the control within 48px with breathing room", () => {
    const css = readSwitcherCss();
    const block = css.slice(css.indexOf(".pstrigger"));
    expect(block).toMatch(/padding:\s*6px 10px;/);
    // The OLD too-tall padding must be gone (it overflowed the 48px bar).
    expect(block).not.toMatch(/padding:\s*9px 10px;/);
  });

  it("stays token-only — no raw hex colours (the locked tokens.css decision)", () => {
    // Strip /* … */ comments first so an issue reference like "(#216)" in a
    // rationale comment isn't mistaken for a hex colour — only DECLARED
    // values are the contract here.
    const css = readSwitcherCss().replace(/\/\*[\s\S]*?\*\//g, "");
    expect(css).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
  });
});
