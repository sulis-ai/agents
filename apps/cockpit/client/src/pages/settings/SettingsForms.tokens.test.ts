// WP-009 — token-consumption scan on SettingsForms.module.css.
//
// WPF-07 / spec acceptance: the settings forms + dialog consume design tokens
// only (var(--*)) — never a raw hex / rgb() / hsl() colour literal that would
// ignore the theme. This parses the module as text (no runtime CSS engine,
// mirroring no-raw-colours.badges.test.ts) and asserts:
//
//   1. The file references at least the tokens the mockup uses (so the scan is
//      meaningful, not vacuously passing on an empty file).
//   2. There is NO raw colour literal anywhere outside a comment.

import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const CSS_PATH = resolve(__dirname, "SettingsForms.module.css");

/** Strip /* … *\/ block comments so commented examples never trip the scan. */
function stripComments(css: string): string {
  return css.replace(/\/\*[\s\S]*?\*\//g, "");
}

describe("SettingsForms.module.css — tokens, not raw colours", () => {
  const css = stripComments(readFileSync(CSS_PATH, "utf8"));

  it("references the semantic colour tokens the signed mockup uses", () => {
    for (const token of [
      "--card",
      "--border",
      "--destructive",
      "--bg-positive",
      "--bg-positive-border",
    ]) {
      expect(css).toContain(`var(${token})`);
    }
  });

  it("contains no raw hex colour literal", () => {
    // Any #rgb / #rrggbb / #rrggbbaa outside a comment fails the scan.
    const hex = css.match(/#[0-9a-fA-F]{3,8}\b/g) ?? [];
    expect(hex).toEqual([]);
  });

  it("contains no raw rgb()/rgba()/hsl()/hsla() colour literal", () => {
    const fns = css.match(/\b(rgb|rgba|hsl|hsla)\s*\(/g) ?? [];
    expect(fns).toEqual([]);
  });
});
