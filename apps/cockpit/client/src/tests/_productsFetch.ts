// WP-008 — shared fetch doubles for the board's products query.
//
// The board now fetches BOTH the change feed AND the products list (the latter
// threaded to every card for the assign-from-card placement). Every board test
// that doubles `fetch` therefore has to answer /api/products too — otherwise
// the products query consumes one of a sequenced mock's slots, re-reads a
// single shared Response body, or skews a feed-call counter.
//
// This is the ONE place that owns those doubles so the 5 board/dashboard test
// files don't each duplicate the wrapper (EP-03 — extract at the 2nd consumer).
//
// - `jsonResponse(status, body)` — a fresh JSON Response (a body is single-read,
//   so each call must return a new instance).
// - `withProductsRoute(inner)` — intercept /api/products with a fresh empty
//   ProductList and delegate every other URL to the inner feed double. Keeps the
//   products query OUT of the inner double, so feed sequences + call counts stay
//   exact.
// - `boardFetch(body, status?)` — a feed double that returns a FRESH Response of
//   `body` per call and answers /api/products separately.

import { vi } from "vitest";

export function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

export function withProductsRoute(
  inner: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>,
) {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : String(input);
    if (url.includes("/api/products")) {
      return jsonResponse(200, { products: [], activeProductId: null });
    }
    return inner(input, init);
  });
}

export function boardFetch(body: unknown, status = 200) {
  return withProductsRoute(async () => jsonResponse(status, body));
}
