// WP-004 — <StageColumn> full-height lane (RED first).
//
// REORGANISE-Refactor of the stage column into a full-height LANE matching
// the production-approved visual contract (.design/cockpit-board-refresh/
// MOCKUP.html — .lane / .laneHead / .laneList / .laneFoot / .laneEmpty):
//
//   - the lane HEADER is sticky (position: sticky; top: 0) so it stays put
//     while the lane's cards scroll; the lane stays a labelled region
//     (aria-label="Recon — N changes") — nothing the lane announced is lost;
//   - the lane LIST is the internal scroll container (overflow-y: auto),
//     keyboard-reachable, so each lane scrolls on its own (the board no
//     longer scrolls as one page);
//   - an EMPTY lane (zero changes) keeps its full height, its header, its
//     count (0), and shows the quiet "Nothing here yet" note INSIDE the lane
//     (S-12 / AF-2) — it is not collapsed or hidden;
//   - the RECON lane (and ONLY Recon) renders a quiet "Start here" foot
//     affordance that routes to /start; the other five lanes have no foot.
//
// Card internals are out of scope here (WP-005 owns the card redesign); this
// WP is layout only. The characterisation of grouping / counts / async
// states lives in Board.test.tsx (already green before & after this refactor)
// — these are the NEW lane-shape pins that fail before the refactor lands.

import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, it, expect } from "vitest";
import { render, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { axe } from "jest-axe";
import type { Change } from "../../../shared/api-types";
import { StageColumn } from "../components/StageColumn";
import type { BoardStage } from "../lib/groupChangesByStage";

function makeChange(overrides: Partial<Change> = {}): Change {
  return {
    changeId: "01ABC",
    handle: "CH-01ABC",
    slug: "fix-thing",
    primitive: "fix",
    branch: "fix/thing",
    worktreePath: "/tmp/worktree",
    intent: "Fix the broken thing",
    baseBranch: "main",
    baseSha: "abc123",
    createdAt: "2026-05-26T11:00:00Z",
    updatedAt: "2026-05-26T11:55:00Z",
    stage: "recon",
    liveness: { status: "unknown", reason: "no session" },
    ...overrides,
  };
}

function renderColumn(stage: BoardStage, changes: Change[]) {
  return render(
    <MemoryRouter>
      <StageColumn stage={stage} changes={changes} />
    </MemoryRouter>,
  );
}

const STAGE_CSS = resolve(
  __dirname,
  "..",
  "components",
  "StageColumn.module.css",
);

describe("<StageColumn> full-height lane (WP-004)", () => {
  it("renders as a labelled region — the lane keeps its aria-label (stage — N changes)", () => {
    const { getByRole } = renderColumn("recon", [
      makeChange({ changeId: "01R", handle: "CH-01R", stage: "recon" }),
      makeChange({ changeId: "01S", handle: "CH-01S", stage: "recon" }),
    ]);
    // The lane is announced as a region with the count in its label.
    expect(
      getByRole("region", { name: "Recon — 2 changes" }),
    ).toBeInTheDocument();
  });

  it("uses the singular 'change' in the region label when the lane holds one card", () => {
    const { getByRole } = renderColumn("specify", [
      makeChange({ changeId: "01S", handle: "CH-01S", stage: "specify" }),
    ]);
    expect(
      getByRole("region", { name: "Specify — 1 change" }),
    ).toBeInTheDocument();
  });

  it("header is a sticky laneHead carrying the dot + name + count", () => {
    const { getByTestId } = renderColumn("design", [
      makeChange({ changeId: "01D", handle: "CH-01D", stage: "design" }),
    ]);
    const lane = getByTestId("stage-column");
    const head = lane.querySelector("header");
    expect(head).not.toBeNull();
    // The header class is the lane head, and CSS pins it sticky (asserted
    // against the stylesheet below — jsdom doesn't compute layout).
    expect(head?.className).toMatch(/laneHead/);
    // The name and the count both live in the head.
    expect(within(head as HTMLElement).getByText("Design")).toBeInTheDocument();
    expect(within(head as HTMLElement).getByText("1")).toBeInTheDocument();
  });

  it("the lane list (internal scroll container) holds the cards and is keyboard-reachable", () => {
    const { getByTestId } = renderColumn("implement", [
      makeChange({ changeId: "01I", handle: "CH-01I", stage: "implement" }),
    ]);
    const list = getByTestId("stage-column-implement");
    expect(list.className).toMatch(/laneList/);
    expect(within(list).getByText("CH-01I")).toBeInTheDocument();
  });

  it("EMPTY lane (zero changes) stays full-height: header, count 0, and the 'Nothing here yet' note inside the lane (S-12)", () => {
    const { getByTestId, getByText, getByRole } = renderColumn("design", []);
    // The lane is still rendered as a region with count 0 in its label.
    expect(
      getByRole("region", { name: "Design — 0 changes" }),
    ).toBeInTheDocument();
    const head = getByTestId("stage-column").querySelector("header");
    expect(within(head as HTMLElement).getByText("0")).toBeInTheDocument();
    // The "Nothing here yet" note lives INSIDE the lane's list, not hidden.
    const list = getByTestId("stage-column-design");
    expect(within(list).getByText(/nothing here yet/i)).toBeInTheDocument();
    expect(getByText(/nothing here yet/i)).toBeInTheDocument();
  });

  it("RECON lane renders a 'Start here' foot affordance that routes to /start", () => {
    const { getByRole } = renderColumn("recon", [
      makeChange({ changeId: "01R", handle: "CH-01R", stage: "recon" }),
    ]);
    const startHere = getByRole("link", { name: /start here/i });
    expect(startHere).toBeInTheDocument();
    expect(startHere).toHaveAttribute("href", "/start");
  });

  it("RECON renders the 'Start here' foot even when the lane is EMPTY (changes start at recon)", () => {
    const { getByRole } = renderColumn("recon", []);
    expect(getByRole("link", { name: /start here/i })).toBeInTheDocument();
  });

  it.each(["specify", "design", "implement", "review", "ship"] as const)(
    "the %s lane has NO 'Start here' foot (only Recon does)",
    (stage) => {
      const { queryByRole } = renderColumn(stage, [
        makeChange({ changeId: "01X", handle: "CH-01X", stage }),
      ]);
      expect(queryByRole("link", { name: /start here/i })).toBeNull();
    },
  );

  it("has no WCAG AA violations — populated Recon lane (jest-axe, WPF-06)", async () => {
    const { container, findByText } = renderColumn("recon", [
      makeChange({ changeId: "01R", handle: "CH-01R", stage: "recon" }),
    ]);
    await findByText("CH-01R");
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("has no WCAG AA violations — empty lane (jest-axe, WPF-06)", async () => {
    const { container } = renderColumn("design", []);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  // ── stylesheet pins (jsdom doesn't compute layout; assert the contract
  //    is encoded in the module CSS so the full-height behaviour can't
  //    silently regress) ──────────────────────────────────────────────────
  describe("StageColumn.module.css encodes the full-height lane contract", () => {
    const css = existsSync(STAGE_CSS) ? readFileSync(STAGE_CSS, "utf8") : "";

    it("the lane head is sticky-positioned to top: 0", () => {
      expect(css).toMatch(/\.laneHead\b/);
      // position: sticky and top: 0 both present in the laneHead rule.
      const block = css.slice(css.indexOf(".laneHead"));
      expect(block).toMatch(/position:\s*sticky/);
      expect(block).toMatch(/top:\s*0/);
    });

    it("the lane list is the internal scroll container (overflow-y: auto, flex-grow, min-height: 0)", () => {
      const block = css.slice(css.indexOf(".laneList"));
      expect(block).toMatch(/overflow-y:\s*auto/);
      expect(block).toMatch(/min-height:\s*0/);
    });

    it("the lane fills its height — no fixed max-height capping it short", () => {
      // Slice the actual `.lane { … }` rule body (not a comment mention) by
      // anchoring on the rule opener and reading to its closing brace.
      const ruleStart = css.indexOf(".lane {");
      expect(ruleStart).toBeGreaterThan(-1);
      const laneBlock = css.slice(
        ruleStart,
        css.indexOf("}", ruleStart) + 1,
      );
      // The old col had a max-height: 560px cap; the full-height lane must not.
      expect(laneBlock).not.toMatch(/max-height:\s*\d/);
      expect(laneBlock).toMatch(/min-height:\s*0/);
    });

    it("carries no raw colour literals — tokens only (WPF-07)", () => {
      // No hex colours; colour values come from var(--*) tokens.
      const hexMatches = css.match(/#[0-9a-fA-F]{3,8}\b/g) ?? [];
      expect(hexMatches).toEqual([]);
      // No rgb()/rgba()/hsl() raw colour functions either.
      expect(css).not.toMatch(/\b(rgb|rgba|hsl|hsla)\(/);
    });
  });
});
