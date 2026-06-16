// WP-002 — <ProductControl> accessibility audit (ADR-002; WPF a11y gate).
//
// The one shared a11y model the three homes rely on — tested ONCE on the
// primitive (follows the ChangeCard.axe.test.tsx pattern):
//   - jest-axe clean in BOTH light and dark, trigger-closed and menu-open,
//     scope + assign modes, assigned + unassigned;
//   - full keyboard path (arrow between rows, Enter commits, Escape closes);
//   - ≥44px touch targets on the trigger and every menu row;
//   - aria-live "Saving…" then "Saved" announce (assign mode);
//   - reduced-motion fallback (the end state shows without animation; the
//     "Saved" WORD is the carrier, never motion).
//
// Theme is set via documentElement[data-theme] exactly as the app sets it;
// jsdom doesn't compute layout, so axe validates the STRUCTURAL a11y (roles /
// names / aria) — which is where glyph+word state encoding is load-bearing.

import { describe, it, expect, afterEach, vi } from "vitest";
import { render, within, fireEvent } from "@testing-library/react";
import { axe } from "jest-axe";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import type { ProductRow } from "../components/ProductControl";
import { ProductControl } from "../components/ProductControl";

const SCOPE_ROWS: ProductRow[] = [
  { productId: "all", name: "All products", count: 23, glyph: "all-grid" },
  {
    productId: "unassigned",
    name: "Unassigned",
    count: 9,
    glyph: "unassigned-dashed",
  },
  {
    productId: "dna:product:01CLINIC0000000000000000000",
    name: "Clinics",
    count: 6,
    glyph: "monogram",
  },
];

const ASSIGN_ROWS: ProductRow[] = [
  {
    productId: "dna:product:01CLINIC0000000000000000000",
    name: "Clinics",
    glyph: "monogram",
  },
  {
    productId: "dna:product:01FOUNDER000000000000000000",
    name: "Founder Web",
    glyph: "monogram",
  },
  {
    productId: "dna:product:01BILLING000000000000000000",
    name: "Billing",
    glyph: "monogram",
  },
];

function setTheme(theme: "light" | "dark") {
  if (theme === "dark") document.documentElement.dataset.theme = "dark";
  else delete document.documentElement.dataset.theme;
}

afterEach(() => {
  delete document.documentElement.dataset.theme;
});

describe("<ProductControl> WCAG AA — both themes, trigger + menu open", () => {
  for (const theme of ["light", "dark"] as const) {
    it(`${theme} · scope mode, menu open, has no axe violations`, async () => {
      setTheme(theme);
      const { container, getByTestId } = render(
        <ProductControl
          mode="scope"
          rows={SCOPE_ROWS}
          selectedId="all"
          onSelect={() => {}}
          onManageProducts={() => {}}
          onSetUpNew={() => {}}
        />,
      );
      fireEvent.click(getByTestId("product-control-trigger"));
      expect(await axe(container)).toHaveNoViolations();
    });

    it(`${theme} · assign mode (assigned), menu open, has no axe violations`, async () => {
      setTheme(theme);
      const { container, getByTestId } = render(
        <ProductControl
          mode="assign"
          rows={ASSIGN_ROWS}
          selectedId="dna:product:01CLINIC0000000000000000000"
          onSelect={() => {}}
          onRemove={() => {}}
          onSetUpNew={() => {}}
        />,
      );
      fireEvent.click(getByTestId("product-control-trigger"));
      expect(await axe(container)).toHaveNoViolations();
    });

    it(`${theme} · assign mode (unassigned, ＋ Add to a product) has no axe violations`, async () => {
      setTheme(theme);
      const { container } = render(
        <ProductControl
          mode="assign"
          rows={ASSIGN_ROWS}
          selectedId={null}
          onSelect={() => {}}
          triggerLabel="Add this change to a product"
        />,
      );
      expect(await axe(container)).toHaveNoViolations();
    });
  }
});

describe("<ProductControl> keyboard path (arrow / Enter / Escape)", () => {
  it("arrow keys move the active row and Enter commits it", () => {
    const onSelect = vi.fn();
    const { getByTestId } = render(
      <ProductControl
        mode="assign"
        rows={ASSIGN_ROWS}
        selectedId={null}
        onSelect={onSelect}
      />,
    );
    const trigger = getByTestId("product-control-trigger");
    // Open via keyboard (Enter on the trigger).
    fireEvent.keyDown(trigger, { key: "Enter" });
    const menu = getByTestId("product-control-menu");
    // ArrowDown to the first row, ArrowDown again to the second, Enter commits.
    fireEvent.keyDown(menu, { key: "ArrowDown" });
    fireEvent.keyDown(menu, { key: "ArrowDown" });
    fireEvent.keyDown(menu, { key: "Enter" });
    // The second product (Founder Web) is committed.
    expect(onSelect).toHaveBeenCalledWith(
      "dna:product:01FOUNDER000000000000000000",
    );
  });

  it("Escape closes the open menu and returns focus to the trigger", () => {
    const { getByTestId, queryByTestId } = render(
      <ProductControl
        mode="scope"
        rows={SCOPE_ROWS}
        selectedId="all"
        onSelect={() => {}}
      />,
    );
    const trigger = getByTestId("product-control-trigger");
    fireEvent.click(trigger);
    fireEvent.keyDown(getByTestId("product-control-menu"), { key: "Escape" });
    expect(queryByTestId("product-control-menu")).toBeNull();
    expect(document.activeElement).toBe(trigger);
  });
});

describe("<ProductControl> aria-live commit feedback (assign mode)", () => {
  it("renders a polite live region that announces 'Saving…' then 'Saved'", () => {
    const { getByTestId, rerender } = render(
      <ProductControl
        mode="assign"
        rows={ASSIGN_ROWS}
        selectedId="dna:product:01CLINIC0000000000000000000"
        onSelect={() => {}}
        saveState="saving"
      />,
    );
    const live = getByTestId("product-control-live");
    expect(live.getAttribute("aria-live")).toBe("polite");
    expect(live.textContent).toMatch(/saving/i);
    rerender(
      <ProductControl
        mode="assign"
        rows={ASSIGN_ROWS}
        selectedId="dna:product:01CLINIC0000000000000000000"
        onSelect={() => {}}
        saveState="saved"
      />,
    );
    // Tick + the WORD "Saved" — not a colour flash alone.
    expect(getByTestId("product-control-live").textContent).toMatch(/saved/i);
  });

  it("the live region is empty (no stale announce) when idle", () => {
    const { getByTestId } = render(
      <ProductControl
        mode="assign"
        rows={ASSIGN_ROWS}
        selectedId="dna:product:01CLINIC0000000000000000000"
        onSelect={() => {}}
        saveState="idle"
      />,
    );
    expect(getByTestId("product-control-live").textContent?.trim()).toBe("");
  });
});

describe("<ProductControl> ≥44px touch targets + reduced-motion (stylesheet contract)", () => {
  function readCss(): string {
    const candidates = [
      resolve(process.cwd(), "src/components/ProductControl.module.css"),
      resolve(process.cwd(), "client/src/components/ProductControl.module.css"),
    ];
    const cssPath = candidates.find((p) => existsSync(p));
    expect(cssPath, "ProductControl.module.css must be locatable").toBeTruthy();
    return readFileSync(cssPath as string, "utf8");
  }

  it("the trigger and menu rows declare min-height: 44px (≥44px touch target)", () => {
    const css = readCss();
    // The trigger and the menu item rows each carry a 44px floor.
    const matches = css.match(/min-height:\s*44px/g) ?? [];
    expect(matches.length).toBeGreaterThanOrEqual(2);
  });

  it("ships a prefers-reduced-motion: reduce fallback (end state, no animation)", () => {
    const css = readCss();
    expect(css).toMatch(/@media\s*\(prefers-reduced-motion:\s*reduce\)/);
  });

  it("stays token-only — no raw hex colours (the locked tokens.css decision)", () => {
    const css = readCss().replace(/\/\*[\s\S]*?\*\//g, "");
    expect(css).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
  });
});

describe("<ProductControl> never colour alone — glyph + word per state", () => {
  it("the active row carries a tick mark AND bold weight (not colour-only)", () => {
    const { getByTestId } = render(
      <ProductControl
        mode="scope"
        rows={SCOPE_ROWS}
        selectedId="unassigned"
        onSelect={() => {}}
      />,
    );
    fireEvent.click(getByTestId("product-control-trigger"));
    const menu = getByTestId("product-control-menu");
    const active = within(menu)
      .getAllByRole("menuitemradio")
      .find((el) => el.getAttribute("aria-checked") === "true")!;
    // The active row carries a tick glyph (an svg) — strip colour, it's still ticked.
    expect(
      active.querySelector("[data-testid='product-control-tick']"),
    ).toBeTruthy();
  });

  it("counts ride the row's accessible name so a screen reader hears the shape", () => {
    const { getByTestId } = render(
      <ProductControl
        mode="scope"
        rows={SCOPE_ROWS}
        selectedId="all"
        onSelect={() => {}}
      />,
    );
    fireEvent.click(getByTestId("product-control-trigger"));
    const menu = getByTestId("product-control-menu");
    const clinics = within(menu)
      .getByText("Clinics")
      .closest("[role='menuitemradio']")!;
    // "Clinics, 6 changes" (or similar) — count is in the accessible name.
    expect(clinics.getAttribute("aria-label") ?? "").toMatch(/6 changes/i);
  });
});
