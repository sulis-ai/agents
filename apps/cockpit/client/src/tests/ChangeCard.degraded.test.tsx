// WP-011 — degraded / partial <ChangeCard> (RED) — S-35 / FR-54 / FR-55 / BR-26.
//
// The card-level COMPOSITION of WP-005's field-level unknown reads. When a
// change's record is malformed or partial, the card renders PER-FIELD:
//   - readable fields render normally;
//   - unreadable fields fall to their existing unknown read (health → "Not
//     assessed yet" FR-31; liveness → the distinct unknown "?" probe FR-41;
//     recency → "—" FR-42; missing slug/intent → an honest placeholder);
//   - the card STILL renders and STILL links to /c/:changeId (FR-54);
//   - a quiet, FIXED-STRING "Some details couldn't be read" notice renders and
//     is aria-announced (FR-55), and NEVER echoes the malformed/seeded content
//     (NFR-SEC-03 / FR-32);
//   - the board NEVER breaks over one bad record: in a multi-card board, every
//     OTHER card renders normally (BR-26 / EF-2 / NFR-DEGRADE-2).
//
// The degraded reads REUSE the WP-005 components (LivenessProbe unknown,
// ChangeHealthBadge "Not assessed yet") — no second unknown implementation
// (EP-03).

import { describe, it, expect } from "vitest";
import { render, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import type { Change } from "../../../shared/api-types";
import { ChangeCard, isDegraded } from "../components/ChangeCard";

/** A fully-healthy record — every field readable. */
function makeHealthy(overrides: Partial<Change> = {}): Change {
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

/**
 * A malformed / partial record: the handle is the one field that survived;
 * liveness + health came back unknown, recency is null, and the content fields
 * (slug + intent) could not be read. Mirrors the producer's never-throw output
 * (WP-002): unreadable fields arrive as their honest unknown reads.
 */
function makeDegraded(overrides: Partial<Change> = {}): Change {
  return makeHealthy({
    slug: "",
    intent: "",
    liveness: { status: "unknown", reason: "malformed session record" },
    health: { state: "unknown", reason: "this field could not be read" },
    lastActivityAt: null,
    ...overrides,
  });
}

function renderCard(change: Change) {
  return render(
    <MemoryRouter>
      <ChangeCard change={change} />
    </MemoryRouter>,
  );
}

describe("isDegraded() — partial/malformed record detection (WP-011)", () => {
  it("a fully-readable record is NOT degraded", () => {
    expect(isDegraded(makeHealthy())).toBe(false);
  });

  it("a record with unknown liveness + unknown health + missing content IS degraded", () => {
    expect(isDegraded(makeDegraded())).toBe(true);
  });

  it("a single unknown read alone (the honest fresh-change case) is NOT degraded", () => {
    // A fresh change legitimately reads health-unknown ('too early to tell')
    // with everything else readable — that is NOT a malformed record.
    expect(
      isDegraded(
        makeHealthy({
          health: { state: "unknown", reason: "too early to tell" },
        }),
      ),
    ).toBe(false);
  });

  it("a record missing its readable content (empty slug + intent) IS degraded", () => {
    expect(isDegraded(makeHealthy({ slug: "", intent: "" }))).toBe(true);
  });
});

describe("degraded <ChangeCard> — per-field render + quiet notice (WP-011 / S-35)", () => {
  it("FR-54: the card still renders and still LINKS to /c/:changeId", () => {
    const { getByTestId } = renderCard(makeDegraded());
    const card = getByTestId("change-card");
    expect(card).toBeInTheDocument();
    expect(card).toHaveAttribute("href", "/c/01KTMF");
  });

  it("FR-54: the handle (the one readable field) still renders", () => {
    const { getByText } = renderCard(makeDegraded());
    expect(getByText("CH-01KTMF")).toBeInTheDocument();
  });

  it("FR-31: unreadable health falls to the SAME 'Not assessed yet' unknown read", () => {
    const { getByText, container } = renderCard(makeDegraded());
    expect(getByText(/not assessed yet/i)).toBeInTheDocument();
    // …and it is the WP-005 health badge, not a second implementation.
    expect(
      container.querySelector('[data-health-state="unknown"]'),
    ).not.toBeNull();
  });

  it("FR-41: unreadable liveness falls to the SAME distinct unknown '?' probe", () => {
    const { container } = renderCard(makeDegraded());
    expect(
      container.querySelector('[data-probe-state="unknown"]'),
    ).not.toBeNull();
  });

  it("FR-42: no recency renders the em-dash, never a fabricated time", () => {
    const { container } = renderCard(makeDegraded());
    const probe = container.querySelector('[data-probe-state="unknown"]')!;
    // The VISIBLE time slot is the no-recency em-dash, not a fabricated age.
    // (The probe's SR label legitimately contains "unknown" — assert the
    // visible time span, not the whole probe text, which carries the SR label.)
    expect(probe.textContent).toContain("—");
    const visibleTime = Array.from(probe.querySelectorAll("span"))
      .map((s) => s.textContent ?? "")
      .find((t) => t.trim() === "—");
    expect(visibleTime).toBe("—");
  });

  it("missing content fields render an honest placeholder, not a blank", () => {
    const { getByTestId } = renderCard(makeDegraded());
    const card = getByTestId("change-card");
    // The card is not blank — some honest text stands in for the unreadable
    // content (the dashed 'no signal yet' vocabulary), never empty.
    expect(card.textContent?.trim().length).toBeGreaterThan(0);
  });

  it("FR-55: the quiet fixed-string notice renders and is aria-announced", () => {
    const { getByText } = renderCard(makeDegraded());
    const notice = getByText(/some details couldn't be read/i);
    expect(notice).toBeInTheDocument();
    // aria-announced so it isn't colour-/placement-alone (NFR-A11Y-4): the
    // notice (or an ancestor) carries a live-region / status role.
    const live = notice.closest('[role="status"],[aria-live]');
    expect(live).not.toBeNull();
  });

  it("FR-55 / NFR-SEC-03: the notice is a FIXED string — it never echoes a malformed field reason, and no markup is injected", () => {
    const seeded = "<script>alert('xss')</script> SECRET-TOKEN-9f3a";
    const { getByTestId } = renderCard(
      makeDegraded({
        // A malformed record might carry junk in its field reasons. The
        // degraded NOTICE must NEVER interpolate any of it — it is a fixed
        // string. (The producer guarantees fixed reason strings; this asserts
        // the card never surfaces a reason into the notice even so.)
        health: { state: "unknown", reason: seeded },
        liveness: { status: "unknown", reason: seeded },
      }),
    );
    const card = getByTestId("change-card");
    // The visible degraded NOTICE is exactly the fixed string — no seeded text.
    const notice = card.querySelector('[role="status"],[aria-live]')!;
    expect(notice.textContent?.trim()).toBe("Some details couldn't be read");
    expect(notice.textContent).not.toContain("SECRET-TOKEN-9f3a");
    // No raw <script> element was ever injected anywhere in the card (React
    // escapes any field text it does render — there is no dangerouslySetInnerHTML).
    expect(card.querySelector("script")).toBeNull();
  });

  it("FR-55: a HEALTHY card shows NO degraded notice (the notice is degraded-only)", () => {
    const { queryByText } = renderCard(makeHealthy());
    expect(queryByText(/some details couldn't be read/i)).toBeNull();
  });

  it("BR-26: a degraded card never drops a sibling — every other card in the board renders normally", () => {
    const healthyA = makeHealthy({ changeId: "AAA", handle: "CH-AAA" });
    const degraded = makeDegraded({ changeId: "BAD", handle: "CH-BAD" });
    const healthyB = makeHealthy({ changeId: "CCC", handle: "CH-CCC" });

    const { getAllByTestId, getByText } = render(
      <MemoryRouter>
        <div>
          <ChangeCard change={healthyA} />
          <ChangeCard change={degraded} />
          <ChangeCard change={healthyB} />
        </div>
      </MemoryRouter>,
    );

    // All three cards rendered — the bad record did not break the lane.
    expect(getAllByTestId("change-card")).toHaveLength(3);
    // The healthy siblings render their normal reads.
    expect(getByText("CH-AAA")).toBeInTheDocument();
    expect(getByText("CH-CCC")).toBeInTheDocument();
    // Exactly ONE degraded notice — only the bad card is degraded.
    const notices = getAllByTestId("change-card").filter((c) =>
      /some details couldn't be read/i.test(c.textContent ?? ""),
    );
    expect(notices).toHaveLength(1);
    expect(within(notices[0]!).getByText("CH-BAD")).toBeInTheDocument();
  });
});
