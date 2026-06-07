// WP-009 — <ConciergePage /> — the concierge front door, routed at /concierge.
//
// Thin page wrapper around <ConciergeChat />. It wires the confirm-gated route
// OFFER (FR-N9) to navigation: on the founder's explicit confirm, it sends them
// to the onboarding (UC-07) or start-from-intent (UC-08) surface — the
// confirm-gated ACT lives THERE, never inline in the concierge turn (ADR-006).
// Those surfaces are delivered by the onboarding / start-from-intent slices
// (WP-010 / WP-011); the concierge only OFFERS the next step.
//
// Scoped to the active Product so the answer reads the founder's current world
// (ADR-009).

import { useNavigate } from "react-router-dom";

import { ConciergeChat } from "../components/ConciergeChat";
import { useActiveProduct } from "../api/activeProduct";

/** Where each route hint sends the founder once they confirm (FR-N9). */
const ROUTE_DESTINATION: Record<"onboarding" | "start-from-intent", string> = {
  onboarding: "/onboarding",
  "start-from-intent": "/start",
};

export function ConciergePage() {
  const navigate = useNavigate();
  const { activeProductId } = useActiveProduct();

  return (
    <ConciergeChat
      {...(activeProductId ? { productId: activeProductId } : {})}
      onRoute={(route) => navigate(ROUTE_DESTINATION[route])}
    />
  );
}
