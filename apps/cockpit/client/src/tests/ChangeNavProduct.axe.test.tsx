// WP-006 — change-nav product property accessibility audit (ADR-002; WPF gate).
//
// The placement of <ProductControl mode="assign"> in the change nav inherits the
// primitive's shared a11y model (exhaustively tested in ProductControl.axe.test
// .tsx). Here we pin that the PLACEMENT is axe-clean in both themes, assigned +
// unassigned — i.e. wiring the hooks + the "Product" label at the placement
// introduces no violation. jsdom doesn't compute layout, so axe validates the
// structural a11y (roles / names / aria) where glyph+word state encoding is
// load-bearing.

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { axe } from "jest-axe";
import type { ReactNode } from "react";

import { ChangeProductProperty } from "../components/ChangeProductProperty";

const ACME = "dna:product:01ACME00000000000000000000";
const HELP = "dna:product:01HELP00000000000000000000";
const CHANGE_ID = "01CHG0000000000000000000AA";

function jsonRes(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}

function client() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
  });
}

function wrap(ui: ReactNode) {
  return render(<QueryClientProvider client={client()}>{ui}</QueryClientProvider>);
}

function mockProducts() {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (url) => {
    if (String(url).includes("/api/products")) {
      return jsonRes({
        products: [
          { productId: ACME, name: "Acme Checkout" },
          { productId: HELP, name: "Helpdesk" },
        ],
        activeProductId: null,
      });
    }
    return jsonRes({});
  });
}

function setTheme(theme: "light" | "dark") {
  if (theme === "dark") document.documentElement.dataset.theme = "dark";
  else delete document.documentElement.dataset.theme;
}

describe("<ChangeProductProperty> WCAG AA — both themes, assigned + unassigned", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockReset();
  });
  afterEach(() => {
    vi.restoreAllMocks();
    delete document.documentElement.dataset.theme;
  });

  for (const theme of ["light", "dark"] as const) {
    it(`${theme} · assigned has no axe violations`, async () => {
      setTheme(theme);
      mockProducts();
      const { container, findByTestId } = wrap(
        <ChangeProductProperty changeId={CHANGE_ID} currentProductId={ACME} />,
      );
      await findByTestId("product-control-trigger");
      expect(await axe(container)).toHaveNoViolations();
    });

    it(`${theme} · unassigned (＋ Add to a product) has no axe violations`, async () => {
      setTheme(theme);
      mockProducts();
      const { container, findByTestId } = wrap(
        <ChangeProductProperty changeId={CHANGE_ID} currentProductId={null} />,
      );
      await findByTestId("product-control-trigger");
      expect(await axe(container)).toHaveNoViolations();
    });

    it(`${theme} · assigned, menu open has no axe violations`, async () => {
      setTheme(theme);
      mockProducts();
      const { container, findByTestId } = wrap(
        <ChangeProductProperty changeId={CHANGE_ID} currentProductId={ACME} />,
      );
      const trigger = await findByTestId("product-control-trigger");
      trigger.click();
      await waitFor(() =>
        expect(
          container.querySelector("[data-testid='product-control-menu']"),
        ).toBeTruthy(),
      );
      expect(await axe(container)).toHaveNoViolations();
    });
  }
});
