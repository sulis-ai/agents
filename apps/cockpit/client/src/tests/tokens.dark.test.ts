// WP-002 — dark token block contract.
//
// tokens.css carries two colour sets: the existing light `:root { ... }`
// block and a `:root[data-theme="dark"] { ... }` block that redefines every
// colour custom property with dark values (ADR-001 theme mechanism; TDD §6).
// Radius / typography / weight tokens are theme-invariant — they live only in
// `:root` and are intentionally NOT redefined in the dark block.
//
// This spec parses tokens.css as text (no runtime CSS engine) and asserts:
//   (a) a `:root[data-theme="dark"]` selector block exists;
//   (b) every colour custom property in the light `:root` block is also
//       present in the dark block (set-equality over the colour-token names);
//   (c) each colour token is defined exactly once in the dark block (no
//       duplicate / contradictory definitions).
//
// The canonical COLOUR_TOKENS list is the complete colour set the WP-002
// Contract enumerates — it is what distinguishes colour vars (which must be
// re-themed) from radius/type/weight vars (which must not appear in the dark
// block).

import { describe, it, expect } from "vitest";
import { promises as fs } from "node:fs";
import path from "node:path";

const TOKENS_CSS = path.resolve(__dirname, "..", "tokens.css");

// The complete colour token set, per the WP-002 Contract ("Variables that
// must appear in the dark block"). These are exactly the colour vars the
// light `:root` defines — and exactly what the dark block must redefine.
const COLOUR_TOKENS = [
  "--background",
  "--foreground",
  "--card",
  "--card-foreground",
  "--popover",
  "--popover-foreground",
  "--muted",
  "--muted-foreground",
  "--secondary",
  "--secondary-foreground",
  "--border",
  "--border-muted",
  "--input",
  "--primary",
  "--primary-foreground",
  "--accent",
  "--accent-foreground",
  "--destructive",
  "--destructive-foreground",
  "--positive",
  "--positive-foreground",
  "--warning",
  "--warning-foreground",
  "--ring",
  "--brand-gold",
  "--brand-depth",
] as const;

// Non-colour tokens that belong ONLY to `:root` — they must NOT leak into the
// dark block (they are theme-invariant).
const THEME_INVARIANT_TOKENS = [
  "--radius-interactive",
  "--radius-button",
  "--radius-container",
  "--radius-badge",
  "--radius-media",
  "--font-sans",
  "--font-display",
  "--font-mono",
  "--weight-body",
  "--weight-heading",
  "--weight-label",
];

/**
 * Return the body (between the outermost braces) of the first block whose
 * selector exactly matches `selector`. Brace-balanced so nested constructs
 * (e.g. functional notations) don't truncate it early. Returns null if the
 * selector is absent.
 */
function blockBody(css: string, selector: string): string | null {
  const selIdx = css.indexOf(selector);
  if (selIdx === -1) return null;
  const open = css.indexOf("{", selIdx);
  if (open === -1) return null;
  let depth = 0;
  for (let i = open; i < css.length; i++) {
    const ch = css[i];
    if (ch === "{") depth++;
    else if (ch === "}") {
      depth--;
      if (depth === 0) return css.slice(open + 1, i);
    }
  }
  return null;
}

/** Count `--name:` definitions of a custom property inside a CSS block body. */
function definitionCount(body: string, name: string): number {
  // Match `--name :` (optional whitespace) at a declaration position. A token
  // is a declaration only when followed (after optional ws) by a colon.
  const re = new RegExp(
    `(^|[;{\\s])${name.replace(/[-]/g, "\\-")}\\s*:`,
    "g",
  );
  const matches = body.match(re);
  return matches ? matches.length : 0;
}

describe("tokens.css — dark token block (WP-002)", () => {
  it("(a) defines a :root[data-theme=\"dark\"] block", async () => {
    const css = await fs.readFile(TOKENS_CSS, "utf8");
    const dark = blockBody(css, ':root[data-theme="dark"]');
    expect(dark, "expected a :root[data-theme=\"dark\"] block in tokens.css").not.toBeNull();
  });

  it("(b) redefines every light colour token in the dark block (set-equality)", async () => {
    const css = await fs.readFile(TOKENS_CSS, "utf8");
    const dark = blockBody(css, ':root[data-theme="dark"]');
    expect(dark).not.toBeNull();
    const body = dark as string;

    const missing = COLOUR_TOKENS.filter((t) => definitionCount(body, t) === 0);
    expect(
      missing,
      `colour tokens defined in light :root but missing from the dark block: ${missing.join(", ")}`,
    ).toEqual([]);
  });

  it("(c) defines each dark colour token exactly once (no duplicates)", async () => {
    const css = await fs.readFile(TOKENS_CSS, "utf8");
    const dark = blockBody(css, ':root[data-theme="dark"]');
    expect(dark).not.toBeNull();
    const body = dark as string;

    const duplicated = COLOUR_TOKENS.filter(
      (t) => definitionCount(body, t) > 1,
    );
    expect(
      duplicated,
      `colour tokens defined more than once in the dark block: ${duplicated.join(", ")}`,
    ).toEqual([]);
  });

  it("does not leak theme-invariant (radius/type/weight) tokens into the dark block", async () => {
    const css = await fs.readFile(TOKENS_CSS, "utf8");
    const dark = blockBody(css, ':root[data-theme="dark"]');
    expect(dark).not.toBeNull();
    const body = dark as string;

    const leaked = THEME_INVARIANT_TOKENS.filter(
      (t) => definitionCount(body, t) > 0,
    );
    expect(
      leaked,
      `theme-invariant tokens that should stay in :root but leaked into the dark block: ${leaked.join(", ")}`,
    ).toEqual([]);
  });

  it("the light :root colour set matches the canonical COLOUR_TOKENS list (guards the contract)", async () => {
    const css = await fs.readFile(TOKENS_CSS, "utf8");
    const light = blockBody(css, ":root {");
    expect(light, "expected a light :root block in tokens.css").not.toBeNull();
    const body = light as string;

    const missingFromLight = COLOUR_TOKENS.filter(
      (t) => definitionCount(body, t) === 0,
    );
    expect(
      missingFromLight,
      `colour tokens the contract expects in light :root but absent: ${missingFromLight.join(", ")}`,
    ).toEqual([]);
  });
});
