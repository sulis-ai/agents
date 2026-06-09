// WP-011 — <StartFromIntentPage /> — the start-from-intent surface, routed at
// /start (UC-08 / UC-10). It is where the concierge's confirm-gated
// start-from-intent OFFER lands (ConciergePage navigates here on
// `route: "start-from-intent"`), and a direct intent box for starting a change
// (or a contained investigation) from plain English.
//
// Thin page wrapper around <StartFromIntent />, scoped to the active Product
// (its Project repo is where the change starts, FR-29). On a started change it
// sends the founder to the board — where the new change shows at Recon.

import { useNavigate } from "react-router-dom";

import { StartFromIntent } from "../components/StartFromIntent";
import { useActiveProduct } from "../api/activeProduct";
import { useProducts } from "../api/useProducts";

export function StartFromIntentPage() {
  const navigate = useNavigate();
  const { activeProductId } = useActiveProduct();
  const products = useProducts();

  // The client-side active-product context is `null` until the founder
  // explicitly switches product; `null` means "use the server's active
  // Product" (the single-Product trivial case / the tenant default) — the SAME
  // fallback the top bar applies (`activeProductId ?? serverActiveProductId`).
  // Resolve the EFFECTIVE active Product so the start always carries a real id:
  // an empty id can't resolve a Project repo and 502s the start (CH-01KTPF).
  const effectiveProductId =
    activeProductId ?? products.data?.activeProductId ?? "";

  return (
    <StartFromIntent
      productId={effectiveProductId}
      onStarted={() => navigate("/")}
    />
  );
}
