import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { ProductPicker } from "./ProductPicker";

const ACME = "dna:product:01ACME00000000000000000000";
const HARP = "dna:product:01HARP00000000000000000000";
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

function renderPicker(currentProductId: string | null) {
  return render(
    <QueryClientProvider client={client()}>
      <ProductPicker changeId={CHANGE_ID} currentProductId={currentProductId} />
    </QueryClientProvider>,
  );
}

describe("<ProductPicker>", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockReset();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("lists products with the current one selected, and assigns on change", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(async (url, init) => {
        const u = String(url);
        if (u.includes("/api/products")) {
          return jsonRes({
            products: [
              { productId: ACME, name: "Acme" },
              { productId: HARP, name: "Helpdesk" },
            ],
            activeProductId: null,
          });
        }
        if (u.includes(`/api/changes/`) && init?.method === "PUT") {
          return jsonRes({ ok: true, id: `dna:change:${CHANGE_ID}`, forProduct: HARP });
        }
        return jsonRes({});
      });

    const { findByTestId } = renderPicker(ACME);
    const select = (await findByTestId(
      "change-product-picker",
    )) as HTMLSelectElement;
    // The current Product is pre-selected.
    expect(select.value).toBe(ACME);

    // Picking another Product fires the assignment PUT to the right path.
    fireEvent.change(select, { target: { value: HARP } });
    await waitFor(() => {
      const put = fetchMock.mock.calls.find(
        ([u, i]) =>
          String(u).includes(`/api/changes/${CHANGE_ID}/product`) &&
          (i as RequestInit | undefined)?.method === "PUT",
      );
      expect(put).toBeTruthy();
    });
  });

  it("renders nothing when there are no products to assign to", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonRes({ products: [], activeProductId: null }),
    );
    const { queryByTestId } = renderPicker(null);
    await waitFor(() =>
      expect(queryByTestId("change-product-picker")).toBeNull(),
    );
  });
});
