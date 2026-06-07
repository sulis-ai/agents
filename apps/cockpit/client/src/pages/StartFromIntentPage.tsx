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

export function StartFromIntentPage() {
  const navigate = useNavigate();
  const { activeProductId } = useActiveProduct();

  // The start needs a Product to start a change against (UC-08 precondition —
  // onboarding mints one). Until one is active, send the founder to onboarding.
  if (!activeProductId) {
    return (
      <StartFromIntent
        productId=""
        onStarted={() => navigate("/")}
      />
    );
  }

  return (
    <StartFromIntent
      productId={activeProductId}
      onStarted={() => navigate("/")}
    />
  );
}
