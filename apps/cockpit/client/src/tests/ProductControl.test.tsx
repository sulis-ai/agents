// WP-002 — <ProductControl> the one shared product vocabulary (ADR-002, EP-03).
//
// One presentation/interaction-only primitive — a chip trigger + a searchable
// popover — placed identically in three homes (the scope switcher, the change
// nav product property, the board card). This file pins the SHARED behaviour:
// the two modes (scope / assign), the rows + counts + glyph tiles, tick-on-
// select, typeahead filtering, the assign-mode foot actions (Remove / Set up /
// Manage), and the unassigned trigger label. The full a11y model (axe, keyboard,
// aria-live, ≥44px, reduced-motion) lives in ProductControl.axe.test.tsx.
//
// The primitive NEVER calls the network — each home injects its onSelect /
// mutation handler. Built to the SIGNED visual contract
// (.design/cockpit-product-experience/MOCKUP.html), tokens.css only.

import { describe, it, expect, vi } from "vitest";
import { render, within, fireEvent } from "@testing-library/react";
import type { ProductRow } from "../components/ProductControl";
import { ProductControl } from "../components/ProductControl";

// Scope-mode rows: the synthetic "All products" (grid tile) + "Unassigned"
// (dashed tile) + each product (monogram), each with a live count.
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
  {
    productId: "dna:product:01FOUNDER000000000000000000",
    name: "Founder Web",
    count: 5,
    glyph: "monogram",
  },
];

// Assign-mode rows: the founder's products (monogram tiles), no synthetic rows.
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

function openMenu(getByTestId: (id: string) => HTMLElement) {
  const trigger = getByTestId("product-control-trigger");
  fireEvent.click(trigger);
  return getByTestId("product-control-menu");
}

describe("<ProductControl> — menu placement (chat-ux Fix 1)", () => {
  it("defaults to opening downward (data-placement='down') — the top-of-page usages keep dropping DOWN", () => {
    const { getByTestId } = render(
      <ProductControl
        mode="scope"
        rows={SCOPE_ROWS}
        selectedId="all"
        onSelect={() => {}}
      />,
    );
    const menu = openMenu(getByTestId);
    expect(menu.getAttribute("data-placement")).toBe("down");
  });

  it("placement='up' opens the menu upward (drop-up) — for the composer-foot agent picker", () => {
    const { getByTestId } = render(
      <ProductControl
        mode="scope"
        rows={SCOPE_ROWS}
        selectedId="all"
        onSelect={() => {}}
        placement="up"
      />,
    );
    const menu = openMenu(getByTestId);
    expect(menu.getAttribute("data-placement")).toBe("up");
    // The drop-up CSS variant is applied (hash-prefixed local name).
    expect(menu.className).toMatch(/pmenuUp/);
  });
});

describe("<ProductControl> — shared behaviour (ADR-002)", () => {
  describe("scope mode", () => {
    it("renders the trigger as a real button with aria-haspopup=menu and aria-expanded", () => {
      const { getByTestId } = render(
        <ProductControl
          mode="scope"
          rows={SCOPE_ROWS}
          selectedId="all"
          onSelect={() => {}}
        />,
      );
      const trigger = getByTestId("product-control-trigger");
      expect(trigger.tagName).toBe("BUTTON");
      expect(trigger.getAttribute("aria-haspopup")).toBe("menu");
      expect(trigger.getAttribute("aria-expanded")).toBe("false");
    });

    it("opens the menu and lists every row with its live count", () => {
      const { getByTestId } = render(
        <ProductControl
          mode="scope"
          rows={SCOPE_ROWS}
          selectedId="all"
          onSelect={() => {}}
        />,
      );
      const menu = openMenu(getByTestId);
      expect(within(menu).getByText("All products")).toBeInTheDocument();
      expect(within(menu).getByText("Unassigned")).toBeInTheDocument();
      expect(within(menu).getByText("Clinics")).toBeInTheDocument();
      // Counts are real text in the row.
      expect(within(menu).getByText("23")).toBeInTheDocument();
      expect(within(menu).getByText("9")).toBeInTheDocument();
      expect(within(menu).getByText("6")).toBeInTheDocument();
    });

    it("ticks the selected row — exactly one menuitemradio is aria-checked", () => {
      const { getByTestId } = render(
        <ProductControl
          mode="scope"
          rows={SCOPE_ROWS}
          selectedId="unassigned"
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

    it("renders the everything-tile (all-grid) and dashed unassigned tile, not two-letter monograms", () => {
      const { getByTestId } = render(
        <ProductControl
          mode="scope"
          rows={SCOPE_ROWS}
          selectedId="all"
          onSelect={() => {}}
        />,
      );
      const menu = openMenu(getByTestId);
      // "All products" carries the grid glyph (an svg), NOT the letters "AL".
      const allRow = within(menu)
        .getByText("All products")
        .closest("[role='menuitemradio']")!;
      expect(allRow.querySelector("[data-glyph='all-grid']")).toBeTruthy();
      const unRow = within(menu)
        .getByText("Unassigned")
        .closest("[role='menuitemradio']")!;
      expect(
        unRow.querySelector("[data-glyph='unassigned-dashed']"),
      ).toBeTruthy();
      // A real product carries its monogram letters.
      const clinicsRow = within(menu)
        .getByText("Clinics")
        .closest("[role='menuitemradio']")!;
      expect(
        clinicsRow.querySelector("[data-glyph='monogram']")?.textContent,
      ).toBe("CL");
    });

    it("fires onSelect with the chosen row id and closes the menu", () => {
      const onSelect = vi.fn();
      const { getByTestId, queryByTestId } = render(
        <ProductControl
          mode="scope"
          rows={SCOPE_ROWS}
          selectedId="all"
          onSelect={onSelect}
        />,
      );
      const menu = openMenu(getByTestId);
      fireEvent.click(within(menu).getByText("Clinics"));
      expect(onSelect).toHaveBeenCalledWith(
        "dna:product:01CLINIC0000000000000000000",
      );
      expect(queryByTestId("product-control-menu")).toBeNull();
    });

    it("offers the 'Manage products' foot action when onManageProducts is provided", () => {
      const onManageProducts = vi.fn();
      const { getByTestId } = render(
        <ProductControl
          mode="scope"
          rows={SCOPE_ROWS}
          selectedId="all"
          onSelect={() => {}}
          onSetUpNew={() => {}}
          onManageProducts={onManageProducts}
        />,
      );
      const menu = openMenu(getByTestId);
      const manage = within(menu).getByText(/manage products/i);
      fireEvent.click(manage);
      expect(onManageProducts).toHaveBeenCalledOnce();
    });
  });

  describe("assign mode", () => {
    it("shows the assigned product's monogram + name on the trigger when selected", () => {
      const { getByTestId } = render(
        <ProductControl
          mode="assign"
          rows={ASSIGN_ROWS}
          selectedId="dna:product:01CLINIC0000000000000000000"
          onSelect={() => {}}
        />,
      );
      const trigger = getByTestId("product-control-trigger");
      expect(trigger.textContent).toContain("Clinics");
      expect(
        trigger.querySelector("[data-glyph='monogram']")?.textContent,
      ).toBe("CL");
    });

    it("shows the '＋ Add to a product' trigger label when unassigned (selectedId null)", () => {
      const { getByTestId } = render(
        <ProductControl
          mode="assign"
          rows={ASSIGN_ROWS}
          selectedId={null}
          onSelect={() => {}}
        />,
      );
      const trigger = getByTestId("product-control-trigger");
      expect(trigger.textContent).toMatch(/add to a product/i);
      // #378 — the unassigned chip leads with the signed mockup's inline "＋"
      // icon (data-glyph="plus"), so it reads "＋ Add to a product". Shape, not
      // colour alone: the plus glyph + the chip's dashed border carry the state.
      expect(trigger.querySelector("[data-glyph='plus']")).toBeTruthy();
    });

    it("uses an explicit triggerLabel for the unassigned trigger's accessible name when given", () => {
      const { getByTestId } = render(
        <ProductControl
          mode="assign"
          rows={ASSIGN_ROWS}
          selectedId={null}
          onSelect={() => {}}
          triggerLabel="Add this change to a product"
        />,
      );
      const trigger = getByTestId("product-control-trigger");
      expect(trigger.getAttribute("aria-label")).toBe(
        "Add this change to a product",
      );
    });

    it("renders a labelled typeahead input that filters the rows", () => {
      const { getByTestId } = render(
        <ProductControl
          mode="assign"
          rows={ASSIGN_ROWS}
          selectedId="dna:product:01CLINIC0000000000000000000"
          onSelect={() => {}}
        />,
      );
      const menu = openMenu(getByTestId);
      const search = within(menu).getByLabelText(
        /find a product/i,
      ) as HTMLInputElement;
      expect(search.tagName).toBe("INPUT");
      // All three present before filtering.
      expect(within(menu).getByText("Founder Web")).toBeInTheDocument();
      expect(within(menu).getByText("Billing")).toBeInTheDocument();
      fireEvent.change(search, { target: { value: "bill" } });
      // Only "Billing" survives the filter (case-insensitive).
      expect(within(menu).getByText("Billing")).toBeInTheDocument();
      expect(within(menu).queryByText("Founder Web")).toBeNull();
      expect(within(menu).queryByText("Clinics")).toBeNull();
    });

    it("fires onRemove from the 'Remove from product' item when assigned", () => {
      const onRemove = vi.fn();
      const { getByTestId } = render(
        <ProductControl
          mode="assign"
          rows={ASSIGN_ROWS}
          selectedId="dna:product:01CLINIC0000000000000000000"
          onSelect={() => {}}
          onRemove={onRemove}
        />,
      );
      const menu = openMenu(getByTestId);
      fireEvent.click(within(menu).getByText(/remove from product/i));
      expect(onRemove).toHaveBeenCalledOnce();
    });

    it("does NOT render 'Remove from product' when unassigned (nothing to remove)", () => {
      const { getByTestId } = render(
        <ProductControl
          mode="assign"
          rows={ASSIGN_ROWS}
          selectedId={null}
          onSelect={() => {}}
          onRemove={() => {}}
        />,
      );
      const menu = openMenu(getByTestId);
      expect(within(menu).queryByText(/remove from product/i)).toBeNull();
    });

    it("offers 'Set up a new product' foot action firing onSetUpNew", () => {
      const onSetUpNew = vi.fn();
      const { getByTestId } = render(
        <ProductControl
          mode="assign"
          rows={ASSIGN_ROWS}
          selectedId={null}
          onSelect={() => {}}
          onSetUpNew={onSetUpNew}
        />,
      );
      const menu = openMenu(getByTestId);
      fireEvent.click(within(menu).getByText(/set up a new product/i));
      expect(onSetUpNew).toHaveBeenCalledOnce();
    });
  });

  describe("menu lifecycle (shared)", () => {
    it("closes on Escape", () => {
      const { getByTestId, queryByTestId } = render(
        <ProductControl
          mode="scope"
          rows={SCOPE_ROWS}
          selectedId="all"
          onSelect={() => {}}
        />,
      );
      openMenu(getByTestId);
      fireEvent.keyDown(document, { key: "Escape" });
      expect(queryByTestId("product-control-menu")).toBeNull();
    });

    it("closes on outside click", () => {
      const { getByTestId, queryByTestId } = render(
        <div>
          <ProductControl
            mode="scope"
            rows={SCOPE_ROWS}
            selectedId="all"
            onSelect={() => {}}
          />
          <button data-testid="outside">elsewhere</button>
        </div>,
      );
      openMenu(getByTestId);
      fireEvent.mouseDown(getByTestId("outside"));
      expect(queryByTestId("product-control-menu")).toBeNull();
    });

    it("performs ZERO network calls — selecting fires only the injected handler", () => {
      const fetchSpy = vi.spyOn(globalThis, "fetch");
      const { getByTestId } = render(
        <ProductControl
          mode="assign"
          rows={ASSIGN_ROWS}
          selectedId="dna:product:01CLINIC0000000000000000000"
          onSelect={() => {}}
        />,
      );
      const menu = openMenu(getByTestId);
      fireEvent.click(within(menu).getByText("Billing"));
      expect(fetchSpy).not.toHaveBeenCalled();
      fetchSpy.mockRestore();
    });

    it("renders nothing interactive-breaking when rows is empty (no products) — trigger still present in assign mode", () => {
      const { getByTestId } = render(
        <ProductControl
          mode="assign"
          rows={[]}
          selectedId={null}
          onSelect={() => {}}
        />,
      );
      // The unassigned trigger is the keyboard-reachable entry point even with
      // no products — the menu just has no product rows + the create foot.
      expect(getByTestId("product-control-trigger")).toBeInTheDocument();
    });

    it("ArrowUp clamps at the first row (never goes negative)", () => {
      const onSelect = vi.fn();
      const { getByTestId } = render(
        <ProductControl
          mode="assign"
          rows={ASSIGN_ROWS}
          selectedId={null}
          onSelect={onSelect}
        />,
      );
      const menu = openMenu(getByTestId);
      // Down to row 0, Up should stay at row 0 (not -1), Enter commits row 0.
      fireEvent.keyDown(menu, { key: "ArrowDown" });
      fireEvent.keyDown(menu, { key: "ArrowUp" });
      fireEvent.keyDown(menu, { key: "ArrowUp" });
      fireEvent.keyDown(menu, { key: "Enter" });
      expect(onSelect).toHaveBeenCalledWith(
        "dna:product:01CLINIC0000000000000000000",
      );
    });

    it("singular count reads '1 change' (not '1 changes') in the row accessible name", () => {
      const rows: ProductRow[] = [
        {
          productId: "dna:product:01SOLO0000000000000000000000",
          name: "Solo",
          count: 1,
          glyph: "monogram",
        },
      ];
      const { getByTestId } = render(
        <ProductControl
          mode="scope"
          rows={rows}
          selectedId={null}
          onSelect={() => {}}
        />,
      );
      const menu = openMenu(getByTestId);
      const row = within(menu)
        .getByText("Solo")
        .closest("[role='menuitemradio']")!;
      expect(row.getAttribute("aria-label")).toMatch(/1 change\b/);
      expect(row.getAttribute("aria-label")).not.toMatch(/1 changes/);
    });
  });

  describe("board-card placement (compact)", () => {
    it("renders the compact trigger and still commits onSelect", () => {
      const onSelect = vi.fn();
      const { getByTestId } = render(
        <ProductControl
          mode="assign"
          rows={ASSIGN_ROWS}
          selectedId="dna:product:01CLINIC0000000000000000000"
          onSelect={onSelect}
          compact
        />,
      );
      const menu = openMenu(getByTestId);
      fireEvent.click(within(menu).getByText("Founder Web"));
      expect(onSelect).toHaveBeenCalledWith(
        "dna:product:01FOUNDER000000000000000000",
      );
    });
  });
});
