// WP-009 — <ChangeCard> SELECTED (route-derived) marker (RED) — S-32.
//
// CS-1 / FR-50 / BR-20 / BR-21. A board card is MARKED SELECTED when its
// change is the one open in the active route (/c/:changeId). The marker is:
//   - route-DERIVED (the parent reads the route the SAME way the shell does —
//     useMatch("/c/:changeId") → activeChangeId — and threads a `selected`
//     boolean down; nothing is stored on the feed or the card);
//   - NOT colour-alone — it carries aria-current="true" + a persistent
//     non-colour signal (an inset/left-edge marker class), so it is
//     distinguishable in greyscale (NFR-A11Y-1);
//   - AT MOST ONE — exactly the card whose changeId === activeChangeId;
//   - additive — it composes onto any content/degraded/shipped card without
//     hiding health, waiting, the probe, recency, or a degraded notice.
//
// jsdom runs no layout, so the marker is asserted via aria-current + the
// non-colour marker class + the stylesheet rule (a styling regression cannot
// pass silently) — the same pattern the WP-005 clamp pin uses.

import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, it, expect } from "vitest";
import { render, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import type { Change } from "../../../shared/api-types";
import { ChangeCard } from "../components/ChangeCard";

function makeChange(overrides: Partial<Change> = {}): Change {
  return {
    changeId: "01AAA",
    handle: "CH-01AAA",
    slug: "first-change",
    primitive: "fix",
    branch: "feat/a",
    worktreePath: "/w/a",
    intent: "the first in-flight change",
    baseBranch: "dev",
    baseSha: null,
    createdAt: "2026-06-09T10:00:00Z",
    updatedAt: "2026-06-09T11:00:00Z",
    stage: "implement",
    liveness: { status: "running", pid: 1 },
    needsAttention: { flagged: false, reason: null },
    health: { state: "on-track", reason: "tests green" },
    lastActivityAt: "2026-06-09T10:45:00Z",
    ...overrides,
  };
}

function renderCard(change: Change, selected: boolean) {
  return render(
    <MemoryRouter>
      <ChangeCard change={change} selected={selected} />
    </MemoryRouter>,
  );
}

describe("WP-009 — <ChangeCard> selected marker (route-derived, S-32)", () => {
  it("a SELECTED card carries aria-current=\"true\" and the non-colour marker", () => {
    const { getByTestId } = renderCard(makeChange(), true);
    const card = getByTestId("change-card");
    expect(card.getAttribute("aria-current")).toBe("true");
    // The non-colour marker is exposed as data-selected for both styling and
    // test selection (mirrors SidebarItem's data-active).
    expect(card.getAttribute("data-selected")).toBe("true");
  });

  it("a NON-selected card carries no aria-current and no selected marker", () => {
    const { getByTestId } = renderCard(makeChange(), false);
    const card = getByTestId("change-card");
    expect(card.getAttribute("aria-current")).toBeNull();
    expect(card.getAttribute("data-selected")).toBeNull();
  });

  it("the selected prop defaults to false when omitted (existing usages unchanged)", () => {
    const { getByTestId } = render(
      <MemoryRouter>
        <ChangeCard change={makeChange()} />
      </MemoryRouter>,
    );
    const card = getByTestId("change-card");
    expect(card.getAttribute("aria-current")).toBeNull();
    expect(card.getAttribute("data-selected")).toBeNull();
  });

  it("S-32: at most ONE card is selected — only the card whose id matches the active route", () => {
    // Two cards rendered as a parent would: selected = (id === activeChangeId).
    const activeChangeId = "01BBB";
    const changes = [
      makeChange({ changeId: "01AAA", handle: "CH-01AAA" }),
      makeChange({ changeId: "01BBB", handle: "CH-01BBB" }),
      makeChange({ changeId: "01CCC", handle: "CH-01CCC" }),
    ];
    const { container } = render(
      <MemoryRouter>
        {changes.map((c) => (
          <ChangeCard
            key={c.changeId}
            change={c}
            selected={c.changeId === activeChangeId}
          />
        ))}
      </MemoryRouter>,
    );
    const marked = container.querySelectorAll('[data-selected="true"]');
    expect(marked).toHaveLength(1);
    const ariaCurrent = container.querySelectorAll('[aria-current="true"]');
    expect(ariaCurrent).toHaveLength(1);
    // …and it is the CH-01BBB card.
    const onlyMarked = marked[0] as HTMLElement;
    expect(within(onlyMarked).getByText("CH-01BBB")).toBeInTheDocument();
  });

  it("S-32: on a non-change route (no active change) NO card is selected", () => {
    // Parent passes selected=false to every card (activeChangeId === null).
    const changes = [
      makeChange({ changeId: "01AAA" }),
      makeChange({ changeId: "01BBB" }),
    ];
    const { container } = render(
      <MemoryRouter>
        {changes.map((c) => (
          <ChangeCard key={c.changeId} change={c} selected={false} />
        ))}
      </MemoryRouter>,
    );
    expect(container.querySelectorAll('[data-selected="true"]')).toHaveLength(0);
    expect(container.querySelectorAll('[aria-current]')).toHaveLength(0);
  });

  it("selection SURVIVES a feed re-poll: same route → still marked (route-derived, not stored)", () => {
    const change = makeChange({ changeId: "01AAA" });
    const { getByTestId, rerender } = render(
      <MemoryRouter>
        <ChangeCard change={change} selected={true} />
      </MemoryRouter>,
    );
    expect(getByTestId("change-card").getAttribute("aria-current")).toBe("true");
    // A re-poll hands the parent a fresh Change object (new identity, updated
    // fields) but the SAME route → the parent still computes selected=true.
    const repolled = makeChange({
      changeId: "01AAA",
      lastActivityAt: "2026-06-09T10:59:00Z",
      health: { state: "off-track", reason: "a check went red" },
    });
    rerender(
      <MemoryRouter>
        <ChangeCard change={repolled} selected={true} />
      </MemoryRouter>,
    );
    expect(getByTestId("change-card").getAttribute("aria-current")).toBe("true");
    expect(getByTestId("change-card").getAttribute("data-selected")).toBe("true");
  });

  it("the marker is ADDITIVE: a selected + waiting card still shows the waiting read", () => {
    const { getByTestId, getByText } = renderCard(
      makeChange({
        needsAttention: { flagged: true, reason: "blocked" },
      }),
      true,
    );
    // selected marker present…
    expect(getByTestId("change-card").getAttribute("data-selected")).toBe("true");
    // …AND the waiting read is not suppressed (precedence: additive).
    expect(getByText(/waiting on you/i)).toBeInTheDocument();
  });

  it("the marker is ADDITIVE over a degraded card: the degraded notice still renders", () => {
    const { getByTestId, getByText } = renderCard(
      makeChange({
        slug: "", // unreadable content → degraded
        liveness: { status: "unknown", reason: "no session" },
        health: { state: "unknown", reason: "too early" },
      }),
      true,
    );
    expect(getByTestId("change-card").getAttribute("data-selected")).toBe("true");
    expect(getByText(/some details couldn't be read/i)).toBeInTheDocument();
  });

  it("the stylesheet defines the non-colour selected marker via a token (not colour-alone, not a literal)", () => {
    const cssPath = resolve(
      __dirname,
      "../components/ChangeCard.module.css",
    );
    expect(existsSync(cssPath)).toBe(true);
    const css = readFileSync(cssPath, "utf8");
    // A selected marker rule keyed off the data-selected attribute…
    expect(css).toMatch(/\[data-selected="true"\]/);
    // …whose persistent non-colour signal is a box-shadow inset ring / an
    // outline / a left-edge marker (a structural cue, present in greyscale),
    // and whose colour comes from a token, not a raw hex.
    const selectedBlock =
      css.match(/\[data-selected="true"\][^}]*\{[^}]*\}/s)?.[0] ?? "";
    expect(selectedBlock).toMatch(/box-shadow|outline|border-left|inset/);
    expect(selectedBlock).toMatch(/var\(--/);
    // No raw hex literal inside the selected marker block (WPF-07).
    expect(selectedBlock).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
  });
});
