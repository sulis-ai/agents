// WP-008 — GET /api/products (FR-38, ADR-009).
//
// Lists the Tenant's Products with the active one marked, for the product
// switcher (FR-38). Read-only; the single-Product Tenant is the trivial case
// (one Product, shown active — synthesised by readProducts when the brain has
// none). The active Product is honoured from the optional `?product=` value
// (the stateless all-GET scope variant, ADR-009) — there is NO
// POST /api/products/active, so the read-only gate needs no scope-selection
// classification (builder's choice, recorded in the WP journal).
//
// GET-only; reading it starts no `claude` process (FR-N4) and writes nothing
// — the read-only gate proves no mutation verb lives here.

import { Router } from "express";

import type { ChangeStoreReader } from "../ports/ChangeStoreReader";
import { readProducts } from "../lib/products/readProducts";

import { asyncHandler } from "./_async";
import { readProductQuery } from "./_product-scope";

export interface ProductsRouterDeps {
  changeStore: ChangeStoreReader;
  sulisStateDir: string;
}

export function createProductsRouter(deps: ProductsRouterDeps): Router {
  const router = Router();
  router.get(
    "/",
    asyncHandler(async (req, res) => {
      const requested = readProductQuery(req.query.product);
      const { list } = await readProducts({
        sulisStateDir: deps.sulisStateDir,
        activeProductId: requested,
      });
      res.json(list);
    }),
  );
  return router;
}
