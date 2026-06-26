// WP-003 — switching the product swaps the dock's conversation (ADR-001/002).
//
// One switch moves the board AND the chat together (the dock reads the same
// useActiveProduct store the board reads). Each product keeps its OWN history;
// switching swaps it; switching back returns the first history unchanged — the
// two never blend in the UI.

import { describe, it, expect, vi } from "vitest";
import { within, fireEvent, waitFor } from "@testing-library/react";
import type { ChatScope, ChatThreadResponse } from "../../../shared/api-types";
import { ProductChatDock } from "../components/ProductChatDock";
import { renderWithClient } from "./_renderWithClient";
import { ActiveProductProvider } from "../api/activeProduct";

const CLINICS = "dna:product:01CLINIC0000000000000000000";
const BAKERY = "dna:product:01BAKERY0000000000000000000";

// Per-scope canned histories — physically separate, never blended.
const THREADS: Record<string, ChatThreadResponse> = {
  [`product:${CLINICS}`]: {
    messages: [
      { kind: "user", uuid: "c1", timestamp: "2026-06-25T10:00:00Z", text: "CLINICS ONLY message" },
    ],
    provider: "pty",
    productId: CLINICS,
  },
  [`product:${BAKERY}`]: {
    messages: [
      { kind: "user", uuid: "b1", timestamp: "2026-06-25T11:00:00Z", text: "BAKERY ONLY message" },
    ],
    provider: "agy",
    productId: BAKERY,
  },
};

function renderDock() {
  const fetchChatThread = vi.fn(async (scope: ChatScope) => {
    const t = THREADS[scope];
    if (!t) throw new Error(`no thread for ${scope}`);
    return t;
  });
  const utils = renderWithClient(
    <ActiveProductProvider initialActiveProductId={CLINICS}>
      <ProductChatDock
        products={[
          { productId: CLINICS, name: "Clinics", active: true },
          { productId: BAKERY, name: "Bakery Ops" },
        ]}
        fetchChatThread={fetchChatThread}
        streamProductChat={async () => {}}
        putChatProvider={async () => ({ provider: "pty", applied: "new-work" })}
        streamStartFromIntent={async () => {}}
      />
    </ActiveProductProvider>,
  );
  return { ...utils, fetchChatThread };
}

async function switchTo(getByTestId: (id: string) => HTMLElement, name: RegExp) {
  // The header switcher tile echoes the active product and opens the scope menu.
  // The dock places the ONE menu primitive (ProductControl) under the
  // "dock-switcher" testid home.
  fireEvent.click(getByTestId("dock-switcher-trigger"));
  const menu = getByTestId("dock-switcher-menu");
  const row = within(menu)
    .getAllByRole("menuitemradio")
    .find((r) => name.test(r.getAttribute("aria-label") ?? r.textContent ?? ""));
  if (!row) throw new Error(`no switcher row matching ${name}`);
  fireEvent.click(row);
}

describe("<ProductChatDock> switching product swaps the conversation", () => {
  it("shows the active product's history and swaps it on switch (no blend)", async () => {
    const { getByTestId, queryByText, findByText } = renderDock();

    // Starts on Clinics — Clinics history is shown, Bakery's is not.
    await findByText(/CLINICS ONLY message/);
    expect(queryByText(/BAKERY ONLY message/)).toBeNull();

    // Switch to Bakery Ops → its OWN history replaces Clinics'.
    await switchTo(getByTestId, /bakery/i);
    await findByText(/BAKERY ONLY message/);
    expect(queryByText(/CLINICS ONLY message/)).toBeNull();

    // Switch back to Clinics → history A returns unchanged, still no blend.
    await switchTo(getByTestId, /clinics/i);
    await findByText(/CLINICS ONLY message/);
    expect(queryByText(/BAKERY ONLY message/)).toBeNull();
  });

  it("keys the thread fetch by the active product's chat scope", async () => {
    const { getByTestId, fetchChatThread, findByText } = renderDock();
    await findByText(/CLINICS ONLY message/);
    expect(fetchChatThread).toHaveBeenCalledWith(`product:${CLINICS}` as ChatScope);

    await switchTo(getByTestId, /bakery/i);
    await waitFor(() =>
      expect(fetchChatThread).toHaveBeenCalledWith(`product:${BAKERY}` as ChatScope),
    );
  });
});
