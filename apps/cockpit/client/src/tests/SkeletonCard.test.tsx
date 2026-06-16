// WP-010 — <SkeletonCard> tests (RED first).
//
// The per-card loading placeholder the board renders WHILE the feed is
// resolving, before any real card exists. Transcribed from the
// production-approved visual contract (MOCKUP.html "Alternate card states" →
// LOADING / SKELETON): calm placeholder bars where the handle / probe / step
// dots / two title lines / foot will be — never a spinner — inside the SAME
// card box as a real <ChangeCard> so the swap to real data does not move the
// box (NFR-PERF-5 / BR-24).
//
// The skeleton is INERT: it is `aria-hidden` (a screen reader is told the
// region is loading by the lane's aria-busy + SR line, not by reading
// meaningless bars), and it is NOT focusable (it is not a real card yet — the
// §7c precedence: no real card exists). The shimmer is decorative and respects
// `prefers-reduced-motion: reduce` (static placeholder, no sweep) — verified at
// the CSS layer (BR-25); here we pin the structural a11y contract.

import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { axe } from "jest-axe";
import { SkeletonCard } from "../components/SkeletonCard";

describe("<SkeletonCard>", () => {
  it("renders the calm placeholder bars echoing the real card structure (handle · probe · steps · 2 title lines · foot)", () => {
    const { getByTestId } = render(<SkeletonCard />);
    const card = getByTestId("skeleton-card");
    // Five bar groups: top line (handle + probe), step dots, two title bars,
    // foot bar — the same regions a real card lays out, so the box matches.
    const bars = card.querySelectorAll("[data-skeleton-bar]");
    // handle + probe + steps + title + title.short + foot = 6 bars.
    expect(bars.length).toBe(6);
  });

  it("is inert — aria-hidden and NOT focusable (it is not a real card yet, §7c precedence)", () => {
    const { getByTestId } = render(<SkeletonCard />);
    const card = getByTestId("skeleton-card");
    expect(card).toHaveAttribute("aria-hidden", "true");
    // No interactive element inside — nothing focusable (no link, button, or
    // positive tabindex). The skeleton must never be a tab stop.
    expect(card.querySelector("a, button, [tabindex]")).toBeNull();
    expect(card).not.toHaveAttribute("tabindex");
  });

  it("has no WCAG AA violations (jest-axe, WPF-06)", async () => {
    // The skeleton is aria-hidden, so axe should find no nameable content that
    // needs a role/name — it is purely decorative scaffolding.
    const { container } = render(<SkeletonCard />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
