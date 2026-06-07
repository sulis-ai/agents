// WP-010 — <OnboardingPage /> — the cold-start setup surface, routed at
// /onboarding (UC-07). It is where the concierge's confirm-gated onboarding
// OFFER lands (ConciergePage navigates here on `route: "onboarding"`), and
// where the ProductSwitcher's "set up a new product" goes.
//
// Thin page wrapper around <OnboardingChat />. On success ("your product is set
// up"), it sends the founder to the board — where the new Product is selectable
// in the switcher (the UC-07 postcondition).

import { useNavigate } from "react-router-dom";

import { OnboardingChat } from "../components/OnboardingChat";

export function OnboardingPage() {
  const navigate = useNavigate();
  return <OnboardingChat onDone={() => navigate("/")} />;
}
