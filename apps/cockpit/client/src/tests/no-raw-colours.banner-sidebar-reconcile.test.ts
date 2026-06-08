// WP-009 — characterisation: reconcile two surfaces back to the founder-signed
// visual contract after the colour clean-up drifted them.
//
// Source of truth: the signed-off mockup
// `.architecture/feat-dark-mode/mockup/dark-theme.html`.
//
// Two surfaces drifted during the WP-006/007/008 colour clean-up:
//
//   1. Dashboard error banner (pages/Dashboard.module.css `.errorBox`)
//      The mockup's `.banner.error` is a SOFT TINT, not a solid fill:
//        background: color-mix(in srgb, var(--destructive) 16%, var(--card));
//        border:     1px solid color-mix(in srgb, var(--destructive) 45%, var(--card));
//        color:      var(--foreground);   // readable over the tint, both themes
//      The drifted code used a solid `background: var(--destructive)` with
//      `color: var(--destructive-foreground)` — louder than the mockup and
//      inconsistent with the thread/chat banner, which already uses this
//      color-mix approach (styles/Thread.module.css).
//
//   2. Active sidebar item (components/SidebarItem.module.css)
//      The mockup's `.navitem.active` is a SOLID PRIMARY highlight:
//        background: var(--primary); color: var(--primary-foreground);
//        .navitem.active .dim { color: var(--primary-foreground); opacity: .8; }
//      The drifted code used `background: var(--secondary); color: var(--primary)`
//      — a quiet lifted surface, not the mockup's solid-blue highlight.
//
// Both reconciliations use EXISTING tokens only (--destructive, --card,
// --primary, --primary-foreground, --foreground), so they re-theme for free and
// introduce no raw literal — the no-raw-colours guards stay green.
//
// This spec parses the two CSS modules as text (no runtime CSS engine), mirroring
// the existing no-raw-colours.*.test.ts characterisation specs. It is the RED
// half of the RGB cycle: it fails today (solid banner / --secondary active) and
// goes green once each surface matches the mockup.

import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";

const SRC = path.resolve(__dirname, "..");
const DASHBOARD_CSS = path.join(SRC, "pages", "Dashboard.module.css");
const SIDEBAR_ITEM_CSS = path.join(SRC, "components", "SidebarItem.module.css");

/** Extract the declaration block body for a CSS-module class `.name { ... }`. */
function classBody(css: string, className: string): string | null {
  const re = new RegExp(`\\.${className}(?![\\w-])\\s*\\{`);
  const m = re.exec(css);
  if (!m) return null;
  const open = css.indexOf("{", m.index);
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

/**
 * Extract the body of the active-item rule. SidebarItem expresses the active
 * state via an attribute selector `.item[data-active="true"] { ... }`, so the
 * plain classBody (which stops at the first non-word char after the class name)
 * is the right matcher: `.item` is followed by `[`, which the (?![\w-]) lookahead
 * permits. We therefore match the attribute-qualified rule explicitly.
 */
function attrRuleBody(css: string, selectorPrefix: string): string | null {
  const idx = css.indexOf(selectorPrefix);
  if (idx === -1) return null;
  const open = css.indexOf("{", idx);
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

/** Normalise whitespace so brittle spacing doesn't break the assertion. */
function norm(s: string): string {
  return s.replace(/\s+/g, " ").trim();
}

const HEX_RE = /#[0-9a-fA-F]{3,8}\b/;
const RGB_HSL_RE = /\b(?:rgba?|hsla?)\s*\(/i;

describe("WP-009 — reconcile Dashboard banner + active sidebar item to the signed mockup", () => {
  it("Dashboard .errorBox uses the color-mix soft tint over var(--destructive)/var(--card) (not a solid fill)", () => {
    const css = readFileSync(DASHBOARD_CSS, "utf8");
    const body = classBody(css, "errorBox");
    expect(body, "expected a .errorBox class in Dashboard.module.css").not.toBeNull();
    const b = norm(body as string);

    // Background must be the 16% destructive tint over the card surface.
    expect(
      b,
      "errorBox background must be the mockup's color-mix soft tint, not a solid var(--destructive) fill",
    ).toMatch(
      /background:\s*color-mix\(\s*in srgb\s*,\s*var\(--destructive\)\s*16%\s*,\s*var\(--card\)\s*\)/,
    );

    // Border must be the 45% destructive tint over the card surface.
    expect(
      b,
      "errorBox border must be the mockup's 45% color-mix tint",
    ).toMatch(
      /border:\s*1px solid color-mix\(\s*in srgb\s*,\s*var\(--destructive\)\s*45%\s*,\s*var\(--card\)\s*\)/,
    );

    // It must NOT carry a bare solid destructive background (the drifted state).
    expect(
      /background:\s*var\(--destructive\)\s*;/.test(body as string),
      "errorBox must no longer use the solid var(--destructive) background",
    ).toBe(false);
  });

  it("Dashboard error text uses readable var(--foreground) over the tint (matches the mockup)", () => {
    const css = readFileSync(DASHBOARD_CSS, "utf8");
    const box = norm(classBody(css, "errorBox") as string);
    const msg = norm(classBody(css, "errorMessage") as string);

    // The mockup sets the whole .banner.error to color: var(--foreground).
    expect(box, "errorBox text colour must be var(--foreground)").toContain(
      "color: var(--foreground)",
    );
    // errorMessage must read over the tint too — foreground (not the solid
    // destructive-foreground pairing that only works on a solid fill).
    expect(msg, "errorMessage text colour must be var(--foreground)").toContain(
      "color: var(--foreground)",
    );
    expect(
      msg.includes("var(--destructive-foreground)"),
      "errorMessage must not keep the solid-fill var(--destructive-foreground)",
    ).toBe(false);
  });

  it("active sidebar item uses the solid var(--primary) highlight with var(--primary-foreground) text", () => {
    const css = readFileSync(SIDEBAR_ITEM_CSS, "utf8");
    const body = attrRuleBody(css, '.item[data-active="true"]');
    expect(
      body,
      'expected a .item[data-active="true"] rule in SidebarItem.module.css',
    ).not.toBeNull();
    const b = norm(body as string);

    expect(
      b,
      "active item background must be the solid var(--primary) highlight",
    ).toMatch(/background:\s*var\(--primary\)\s*;/);
    expect(
      b,
      "active item text must be var(--primary-foreground)",
    ).toMatch(/color:\s*var\(--primary-foreground\)\s*;/);

    // It must NOT keep the drifted --secondary background / --primary text.
    expect(
      /background:\s*var\(--secondary\)/.test(body as string),
      "active item must no longer use the var(--secondary) surface",
    ).toBe(false);
  });

  it("active item dim child text is readable on primary (var(--primary-foreground), reduced opacity)", () => {
    const css = readFileSync(SIDEBAR_ITEM_CSS, "utf8");
    // The dim child inside an active item: `.item[data-active="true"] .slug`.
    const body = attrRuleBody(css, '.item[data-active="true"] .slug');
    expect(
      body,
      'expected a .item[data-active="true"] .slug rule so the dim slug reads on primary',
    ).not.toBeNull();
    const b = norm(body as string);
    expect(
      b,
      "active dim slug must use var(--primary-foreground)",
    ).toContain("color: var(--primary-foreground)");
  });

  it("neither reconciled surface introduces a raw colour literal (keeps the no-raw-colours guards green)", () => {
    for (const file of [DASHBOARD_CSS, SIDEBAR_ITEM_CSS]) {
      const css = readFileSync(file, "utf8")
        // strip comments so prose colour words don't false-positive
        .replace(/\/\*[\s\S]*?\*\//g, "");
      expect(HEX_RE.test(css), `${file} must carry no raw hex literal`).toBe(false);
      expect(
        RGB_HSL_RE.test(css),
        `${file} must carry no rgb()/hsl() functional colour literal`,
      ).toBe(false);
    }
  });
});
