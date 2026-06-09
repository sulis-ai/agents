// WP-005 — redesigned <ChangeCard> (RED).
//
// The whole-card redesign per the production-approved MOCKUP. Every card has
// the SAME reading order, top to bottom:
//   handle (left) · probe + time (right)  →  ·N/6 step dots  →  intent  →
//   slug  →  the ONE foot verdict (waiting XOR health, never both).
//
// The load-bearing rule (TDD §5 / BR-1): the foot shows EXACTLY ONE of
// WaitingOnYou (flagged) or ChangeHealthBadge (not flagged) — enforced by a
// single branch, asserted mutually exclusive in the DOM (S-10, S-11).

import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import type { Change } from "../../../shared/api-types";
import { ChangeCard } from "../components/ChangeCard";

function makeChange(overrides: Partial<Change> = {}): Change {
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
    createdAt: "2026-06-09T10:00:00Z",
    updatedAt: "2026-06-09T11:00:00Z",
    stage: "implement",
    liveness: { status: "not-running" },
    needsAttention: { flagged: false, reason: null },
    health: { state: "on-track", reason: "tests green" },
    lastActivityAt: "2026-06-09T10:45:00Z",
    ...overrides,
  };
}

function renderCard(change: Change) {
  return render(
    <MemoryRouter>
      <ChangeCard change={change} />
    </MemoryRouter>,
  );
}

describe("redesigned <ChangeCard> — single foot verdict (WP-005)", () => {
  it("S-10: a FLAGGED card shows WaitingOnYou and HIDES health (no health node)", () => {
    const { getByText, container } = renderCard(
      makeChange({
        needsAttention: { flagged: true, reason: "waiting-on-decision" },
        health: { state: "on-track", reason: "tests green" },
      }),
    );
    // The loud waiting read is present…
    expect(getByText(/waiting on you/i)).toBeInTheDocument();
    // …and the health badge is NOT rendered (mutually exclusive).
    expect(container.querySelector("[data-health-state]")).toBeNull();
  });

  it("S-11: a NON-flagged card shows the health badge and NO waiting node", () => {
    const { container } = renderCard(
      makeChange({
        needsAttention: { flagged: false, reason: null },
        health: { state: "off-track", reason: "tests failing" },
      }),
    );
    expect(container.querySelector('[data-health-state="off-track"]')).toBeTruthy();
    expect(container.querySelector("[data-waiting-why]")).toBeNull();
  });

  it("S-16 (render side): a non-flagged card with health.state 'unknown' shows the NEUTRAL badge (one foot read, still mutually exclusive)", () => {
    const { container } = renderCard(
      makeChange({
        needsAttention: { flagged: false, reason: null },
        health: { state: "unknown", reason: "too early to tell" },
      }),
    );
    expect(container.querySelector('[data-health-state="unknown"]')).toBeTruthy();
    expect(container.querySelector("[data-waiting-why]")).toBeNull();
  });

  it("renders slim ·N/6 step dots with an accessible 'Step N of 6' label keyed off the stage", () => {
    const { getByRole } = renderCard(makeChange({ stage: "implement" }));
    // implement is the 4th of the six stages.
    expect(getByRole("img", { name: /step 4 of 6/i })).toBeInTheDocument();
  });

  it("the card link's accessible name carries the FULL handle + intent ('Change CH-… : <intent>')", () => {
    const { getByRole } = renderCard(makeChange());
    const link = getByRole("link", {
      name: /change ch-01ktmf.*make change resolution refuse a dirty worktree/i,
    });
    expect(link).toBeInTheDocument();
  });

  it("renders the fixed reading order: handle → probe → steps → intent → slug → foot", () => {
    const { container } = renderCard(
      makeChange({
        liveness: { status: "running", pid: 1 },
        lastActivityAt: "2026-06-09T10:59:50Z",
      }),
    );
    const card = container.querySelector('[data-testid="change-card"]') as HTMLElement;
    // Measure DOM document order (one coordinate system) of the landmark
    // elements, not mixed string indices: the handle span, the probe, the
    // step-dots img, the intent paragraph, the slug, and the foot row.
    const landmarks = [
      card.querySelector('[class*="handle"]'),
      card.querySelector("[data-probe-state]"),
      card.querySelector('[role="img"]'),
      card.querySelector("p"), // the intent
      card.querySelector('[class*="slug"]'),
      card.querySelector('[class*="footRow"]'),
    ];
    // Every landmark is present…
    for (const el of landmarks) expect(el).toBeTruthy();
    // …and each appears strictly after the previous in document order
    // (compareDocumentPosition returns FOLLOWING for a later node).
    for (let i = 1; i < landmarks.length; i++) {
      const prev = landmarks[i - 1] as Node;
      const cur = landmarks[i] as Node;
      const rel = prev.compareDocumentPosition(cur);
      expect(rel & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    }
  });

  it("does NOT render a StageBadge pill on the card (the lane already says the stage)", () => {
    const { queryByText } = renderCard(makeChange({ stage: "implement" }));
    // The old pill rendered "Implement · 4/6" as text; the redesign drops it.
    expect(queryByText(/implement · 4\/6/i)).not.toBeInTheDocument();
  });

  it("no-recency change still renders the card (probe em-dash, no crash) — S-18 at the card level", () => {
    const { container, getByText } = renderCard(
      makeChange({
        liveness: { status: "unknown", reason: "no session" },
        lastActivityAt: null,
        needsAttention: { flagged: false, reason: null },
        health: { state: "unknown", reason: "too early to tell" },
      }),
    );
    expect(container.querySelector('[data-testid="change-card"]')).toBeTruthy();
    expect(getByText("—")).toBeInTheDocument();
  });

  it("a terminal-stage (shipped) card renders step dots with the 'past the workflow' label (no current step)", () => {
    const { getByRole } = renderCard(makeChange({ stage: "shipped" }));
    expect(getByRole("img", { name: /past the workflow/i })).toBeInTheDocument();
  });

  it.each([
    ["blocked", /blocked/i],
    ["waiting-on-decision", /picking an approach/i],
    ["stopped-mid-reply", /stopped mid-reply/i],
  ] as const)(
    "maps the '%s' attention reason to a plain-English why on the waiting chip",
    (reason, expected) => {
      const { getByText } = renderCard(
        makeChange({
          needsAttention: { flagged: true, reason },
        }),
      );
      expect(getByText(expected)).toBeInTheDocument();
    },
  );
});
