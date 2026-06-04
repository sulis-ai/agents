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
    expect(within(menu).getAllByRole("menuitemradio")).toHaveLength(1);
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
