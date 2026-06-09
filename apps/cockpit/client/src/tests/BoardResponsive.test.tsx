// WP-008 — Board responsive breakpoints (RED first).
//
// Three breakpoints, all CSS-media-query driven per ADR-004 + IDEAS.md
// Concern 4 (the signed MOCKUP.html proves them with real media queries):
//
//   - Desktop ≥ 1100px : the six full-height lanes side by side (WP-004,
//     unchanged) — a 6-column grid.
//   - Tablet 600–1099px : lanes stay side-by-side but the board scrolls
//     HORIZONTALLY at a comfortable lane min-width (~260px) so none is
//     squished, lightly snapping.
//   - Mobile < 600px : ONE full-width lane at a time — a horizontally-
//     snapping track where each lane is exactly one screen wide (100%),
//     firm snap (mandatory). The card itself is unchanged (EP-03) — it
//     just fills the lane.
//
// jsdom does not compute layout or evaluate media queries, so the
// breakpoints are pinned against the stylesheet SOURCE (the same discipline
// StageColumn.test.tsx uses for the full-height lane). The live behaviour
// (tap-a-chip-switches-lane, swipe-follows-rail, no 390px overflow, axe at
// all three viewports) is driven by the Playwright journey (S-8/S-13/S-28).
//
// WP-013's lane virtualisation sits BEHIND the lane API and is untouched by
// these layout rules — the board grid only governs how the lanes are laid
// out, never the lane's internal scroll.

import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, it, expect } from "vitest";

const BOARD_CSS = resolve(__dirname, "..", "pages", "Board.module.css");
const css = existsSync(BOARD_CSS) ? readFileSync(BOARD_CSS, "utf8") : "";

/** Slice the body of the first `@media (...max-width: <px>...)` block. */
function mediaBlock(maxWidth: number): string {
  const re = new RegExp(`@media[^{]*max-width:\\s*${maxWidth}px[^{]*\\{`);
  const m = re.exec(css);
  if (!m) return "";
  // Walk braces from the opener to find the matching close of the @media block.
  let depth = 0;
  let i = m.index + m[0].length - 1; // at the opening brace
  const start = i + 1;
  for (; i < css.length; i++) {
    if (css[i] === "{") depth++;
    else if (css[i] === "}") {
      depth--;
      if (depth === 0) return css.slice(start, i);
    }
  }
  return "";
}

describe("Board.module.css encodes the three responsive breakpoints (WP-008)", () => {
  it("desktop (default): the board is the six-lane grid (unchanged WP-004 baseline)", () => {
    const ruleStart = css.indexOf(".board {");
    expect(ruleStart).toBeGreaterThan(-1);
    const block = css.slice(ruleStart, css.indexOf("}", ruleStart) + 1);
    expect(block).toMatch(/display:\s*grid/);
    expect(block).toMatch(/repeat\(6,/);
  });

  it("tablet (≤1099px): the board scrolls horizontally with comfortable lane min-width (~260px) and snaps", () => {
    const block = mediaBlock(1099);
    expect(block).not.toEqual("");
    // Lanes flow into columns that keep a comfortable min-width (no 1fr crush),
    // and the board overflows/scrolls horizontally rather than squishing six.
    expect(block).toMatch(/grid-auto-flow:\s*column/);
    expect(block).toMatch(/minmax\(\s*260px/);
    expect(block).toMatch(/scroll-snap-type:\s*x/);
  });

  it("mobile (≤599px): one full-width lane at a time — a firm horizontal snap track", () => {
    const block = mediaBlock(599);
    expect(block).not.toEqual("");
    // Each lane is exactly one screen wide (100%) and the track snaps firmly so
    // only one lane is shown at a time.
    expect(block).toMatch(/grid-auto-columns:\s*100%/);
    expect(block).toMatch(/scroll-snap-type:\s*x\s+mandatory/);
    expect(block).toMatch(/overflow-x:\s*auto/);
  });

  it("carries no raw colour literals — tokens only (WPF-07)", () => {
    const hexMatches = css.match(/#[0-9a-fA-F]{3,8}\b/g) ?? [];
    expect(hexMatches).toEqual([]);
    expect(css).not.toMatch(/\b(rgb|rgba|hsl|hsla)\(/);
  });
});
