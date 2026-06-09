// WP-012 — shipped / terminal <ChangeCard> (RED) — S-36, FR-56, BR-27, BR-28.
//
// A change in the terminal stage (stage === "shipped") reads as ARCHIVED, not
// active. The card is MUTED; the LivenessProbe is replaced by a static
// "Shipped" marker (no working/live/idle, no pulse); it shows NEITHER live foot
// (no "Waiting on you", no change-health badge — BR-28 mutual suppression); and
// recency reads "shipped Nd ago" (Q-7 default), not a live-activity age.
//
// Detected from the SAME `stage === "shipped"` predicate the Sidebar split +
// StageBadge already use (BR-27 — reused, not reinvented). Shipped wins the
// foot/probe treatment over the degraded (WP-011) reads, but any unreadable
// IDENTITY field (slug/intent) still falls to its existing unknown read + the
// degraded notice (SRD §7c precedence).

import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import type { Change } from "../../../shared/api-types";
import { ChangeCard } from "../components/ChangeCard";

// `now` is fixed so the "shipped Nd ago" bucket is deterministic. The change
// shipped 5 days before "now".
const NOW = new Date("2026-06-09T12:00:00Z");
const SHIPPED_AT = "2026-06-04T12:00:00Z"; // 5 days before NOW

function makeShipped(overrides: Partial<Change> = {}): Change {
  return {
    changeId: "01KTMF",
    handle: "CH-01KTMF",
    slug: "safe-change-resolution",
    primitive: "fix",
    branch: "feat/x",
    worktreePath: "/w",
    intent: "make change resolution refuse a dirty worktree",
    baseBranch: "dev",
    baseSha: null,
    createdAt: "2026-05-20T10:00:00Z",
    updatedAt: SHIPPED_AT,
    stage: "shipped",
    // A live session/health on a shipped record MUST be suppressed (BR-28): the
    // fixture deliberately sets a running probe + a flagged attention + an
    // off-track health to prove none of them surfaces on a shipped card.
    liveness: { status: "running", pid: 4242 },
    needsAttention: { flagged: true, reason: "blocked" },
    health: { state: "off-track", reason: "tests red" },
    lastActivityAt: "2026-06-09T11:59:00Z",
    ...overrides,
  };
}

function renderCard(change: Change) {
  return render(
    <MemoryRouter>
      <ChangeCard change={change} now={NOW} />
    </MemoryRouter>,
  );
}

describe("shipped / terminal <ChangeCard> — archived treatment (WP-012)", () => {
  it("FR-56: a shipped card is MUTED and carries the shipped marker", () => {
    const { getByTestId } = renderCard(makeShipped());

    const card = getByTestId("change-card");
    expect(card.getAttribute("data-shipped")).toBe("true");
  });

  it("FR-56: the liveness probe is REPLACED by a static 'Shipped' marker (no probe motion/state)", () => {
    const { getByTestId, queryByTestId } = renderCard(makeShipped());

    // The static marker is present and reads "Shipped".
    const marker = getByTestId("shipped-marker");
    expect(marker.textContent).toMatch(/shipped/i);

    // No live probe: the LivenessProbe's dot carries `data-probe-dot`; a shipped
    // card MUST NOT render it (no pulse, no working/live/idle state).
    expect(
      queryByTestId("shipped-marker")!.querySelector("[data-probe-dot]"),
    ).toBeNull();
    expect(
      renderCard(makeShipped()).container.querySelector("[data-probe-state]"),
    ).toBeNull();
  });

  it("BR-28 MUST: no 'Waiting on you' foot on a shipped card (live signal suppressed)", () => {
    const { queryByText } = renderCard(makeShipped());
    expect(queryByText(/waiting on you/i)).toBeNull();
  });

  it("BR-28 MUST: no change-health badge on a shipped card (live signal suppressed)", () => {
    const { container } = renderCard(makeShipped());
    // The health badge carries `data-health-state`; a shipped card shows none.
    expect(container.querySelector("[data-health-state]")).toBeNull();
  });

  it("FR-56: recency reads 'shipped Nd ago', not a live-activity age", () => {
    const { getByTestId } = renderCard(makeShipped());

    const recency = getByTestId("shipped-recency");
    expect(recency.textContent).toMatch(/shipped\s+5d\s+ago/i);
    // It is NOT the live compact age ("now"/"1m"/etc.) used by the live probe.
    expect(recency.textContent).not.toMatch(/^\s*(now|\d+[mhdw])\s*$/i);
  });

  it("SRD §7c precedence: shipped suppresses the feet even when degraded, but an unreadable identity field still falls to its unknown read", () => {
    // A shipped record whose slug came back unreadable: shipped still wins the
    // foot/probe (no feet, static marker), AND the degraded per-field read +
    // notice still surface for the unreadable identity field.
    const { container, queryByText, getByTestId } = renderCard(
      makeShipped({ slug: "" }),
    );

    // Feet still suppressed (shipped precedence).
    expect(queryByText(/waiting on you/i)).toBeNull();
    expect(container.querySelector("[data-health-state]")).toBeNull();

    // Static marker still present.
    expect(getByTestId("shipped-marker")).toBeTruthy();

    // The unreadable slug still falls to its honest placeholder.
    expect(queryByText(/slug unavailable/i)).toBeTruthy();
  });

  it("BR-27: the card still LINKS to the change page (a shipped card is reachable)", () => {
    const { getByTestId } = renderCard(makeShipped());
    expect(getByTestId("change-card").getAttribute("href")).toBe("/c/01KTMF");
  });
});
