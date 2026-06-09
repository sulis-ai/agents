// WP-008 — token-consumption scan for the Settings tree surface.
//
// WP-008 Contract (Red checklist item 4) + WPF-07 (design tokens, never
// hardcoded values): every colour/spacing/radius/font in Settings.module.css
// is a `var(--*)` reference — the module carries NO raw colour literal. Tokens
// come from tokens.css v4.2.0 (signed); light + dark theming + pre-validated
// contrast ride for free. Parses CSS as text (no runtime CSS engine), mirroring
// no-raw-colours.badges.test.ts — the established convention for this gate.

import { describe, it, expect } from "vitest";
import { promises as fs } from "node:fs";
import path from "node:path";

const SRC = path.resolve(__dirname, "..");
const SETTINGS_CSS = path.join(SRC, "pages", "settings", "Settings.module.css");

// Raw colour literal detectors. A token reference `var(--x)` is allowed; a raw
// hex / rgb()/rgba() / hsl() / named colour is not. color-mix(in srgb, var(--x)
// …) is allowed because it composes tokens (the mockup itself uses it).
const HEX_RE = /#[0-9a-fA-F]{3,8}\b/;
const RGB_HSL_RE = /\b(?:rgb|rgba|hsl|hsla)\s*\(/i;
const NAMED_COLOURS = [
  "white",
  "black",
  "red",
  "green",
  "blue",
  "yellow",
  "orange",
  "purple",
  "pink",
  "gray",
  "grey",
  "indigo",
  "lime",
  "teal",
  "navy",
  "maroon",
  "olive",
  "silver",
  "gold",
  "crimson",
  "salmon",
  "tomato",
];

/** Find raw colour literals in a CSS body, ignoring var(--*) refs. */
function rawColourLiterals(css: string): string[] {
  const hits: string[] = [];
  for (const rawLine of css.split(/[;\n]/)) {
    const line = rawLine.trim();
    if (!line) continue;
    if (
      line.startsWith("/*") ||
      line.startsWith("*") ||
      line.startsWith("//")
    ) {
      continue;
    }
    const hex = line.match(HEX_RE);
    if (hex) hits.push(`${hex[0]}  ← ${line}`);
    const fn = line.match(RGB_HSL_RE);
    if (fn) hits.push(`${fn[0]}  ← ${line}`);
    const valuePart = line.includes(":")
      ? line.slice(line.indexOf(":") + 1)
      : line;
    for (const name of NAMED_COLOURS) {
      const nameRe = new RegExp(`(^|[\\s(])${name}(?![\\w-])`, "i");
      if (nameRe.test(valuePart)) hits.push(`${name}  ← ${line}`);
    }
  }
  return hits;
}

describe("no raw colours — Settings tree surface (WP-008, WPF-07)", () => {
  it("Settings.module.css contains no raw colour literal — every colour is a var(--*)", async () => {
    const css = await fs.readFile(SETTINGS_CSS, "utf8");
    const offenders = rawColourLiterals(css);
    expect(
      offenders,
      `Settings.module.css contains raw colour literals (use var(--*) tokens):\n${offenders.join("\n")}`,
    ).toEqual([]);
  });

  it("Settings.module.css consumes the three semantic pill token families (positive / warning / neutral)", async () => {
    const css = await fs.readFile(SETTINGS_CSS, "utf8");
    // The three repo-state pills ride the semantic token families from the
    // signed mockup: positive (Git repo), warning (Not a git repo yet), and a
    // neutral/muted family (No folder attached).
    expect(css, "must reference the positive token family").toMatch(
      /var\(--(bg-)?positive/,
    );
    expect(css, "must reference the warning token family").toMatch(
      /var\(--(bg-)?warning/,
    );
    expect(css, "must reference the muted/border neutral family").toMatch(
      /var\(--muted/,
    );
  });
});
