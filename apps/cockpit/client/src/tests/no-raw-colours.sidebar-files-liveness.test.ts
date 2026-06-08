// WP-008 — characterisation test: no raw colour literals in the
// navigation-chrome straggler styles (sidebar + files panel + liveness dot).
//
// TDD §2 (audit finding) + acceptance criterion 4: every colour a component
// renders must come from the token system (`var(--*)`), never a raw literal,
// so it re-themes under `:root[data-theme="dark"]`. This sweep covers the four
// modules the original tokenisation missed:
//   - components/SidebarItem.module.css   (active-item highlight)
//   - components/Sidebar.module.css       (error text)
//   - components/LivenessDot.module.css   (running / terminal status dots)
//   - styles/FilesPanel.module.css        (`var(--x, #raw)` fallbacks)
//
// What counts as a violation:
//   (1) a raw hex literal           — #abc / #aabbcc / #aabbccdd
//   (2) a functional colour literal — rgb()/rgba()/hsl()/hsla()
//   (3) a CSS named colour          — e.g. `red`, `white` (a small denylist of
//       the names actually plausible in these files; we don't need the full
//       148-name list, just the ones a human would reach for)
//   (4) a `var(--x, <raw>)` fallback whose fallback arm is itself a raw
//       literal (1)/(2)/(3) — the raw fallback still bypasses the theme.
//
// What is NOT a violation:
//   - `var(--token)` (token-only)
//   - `var(--token, var(--other-token))` (token-only fallback chain)
//   - non-colour values (px, %, transparent, inherit, currentColor, 50%, etc.)
//   - a line carrying the documented status-exception marker
//     `/* status-exception */` (per the WP Contract: a LivenessDot status hue
//     may be retained as a conscious exception if the brightened token fails
//     AA on the dark dot). Today no exception is taken, so the allow-list is
//     empty in practice — but the mechanism is here so a future fixed-hue
//     decision is explicit rather than a silent regression.
//
// The test parses the modules as text (no runtime CSS engine). It is the RED
// half of the RGB cycle: it fails today (the four modules carry raw literals)
// and goes green once every literal is replaced by a token.

import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";

const SRC = path.resolve(__dirname, "..");

const MODULES = {
  "SidebarItem.module.css": path.join(SRC, "components", "SidebarItem.module.css"),
  "Sidebar.module.css": path.join(SRC, "components", "Sidebar.module.css"),
  "LivenessDot.module.css": path.join(SRC, "components", "LivenessDot.module.css"),
  "FilesPanel.module.css": path.join(SRC, "styles", "FilesPanel.module.css"),
} as const;

// The conscious-exception marker. A declaration line carrying this comment is
// allow-listed (a deliberately-retained fixed status hue, per WP Contract).
const EXCEPTION_MARKER = "status-exception";

// Raw hex: #rgb, #rgba, #rrggbb, #rrggbbaa.
const HEX = /#[0-9a-fA-F]{3,8}\b/;
// Functional colour notations.
const FUNCTIONAL = /\b(?:rgb|rgba|hsl|hsla)\s*\(/;
// CSS named colours plausible in these files. Word-boundaried; case-insensitive.
// Deliberately a denylist of human-reachable names, not the full CSS set —
// false-negatives on exotic names (`gainsboro`) are acceptable; these modules
// never used them.
const NAMED = new RegExp(
  "\\b(?:" +
    [
      "white", "black", "red", "green", "blue", "yellow", "orange",
      "grey", "gray", "silver", "navy", "teal", "purple", "maroon",
      "lime", "olive", "aqua", "fuchsia", "pink", "gold", "crimson",
    ].join("|") +
    ")\\b",
  "i",
);

/**
 * Strip the value side of a declaration of any `var(...)` references whose
 * fallback arm is token-only, so the literal scanners only see genuinely-raw
 * arms. We do this by collapsing `var(--x, var(--y))` and `var(--x)` to a
 * placeholder, while LEAVING `var(--x, #raw)` intact so the raw fallback is
 * still detected. The approach: repeatedly replace the innermost
 * `var(--name)` (no comma) and `var(--name, var(...))` (token-only fallback)
 * with a neutral token until none remain.
 */
function stripTokenOnlyVars(value: string): string {
  let prev: string;
  let out = value;
  // Collapse token-only `var(--name)` (no fallback).
  const tokenOnly = /var\(\s*--[\w-]+\s*\)/g;
  // Collapse `var(--name, <already-collapsed>)` where the fallback contains no
  // raw literal — we approximate "no raw literal" by "no #, no rgb/hsl, no
  // named colour" in the fallback arm.
  do {
    prev = out;
    out = out.replace(tokenOnly, "TOKEN");
  } while (out !== prev);
  // Now handle one level of fallback: var(--name, X). If X (after the above
  // collapse) has no raw literal, the whole thing is token-only → collapse.
  do {
    prev = out;
    out = out.replace(/var\(\s*--[\w-]+\s*,\s*([^()]*?)\)/g, (m, fallback: string) => {
      const f = String(fallback);
      const hasRaw = HEX.test(f) || FUNCTIONAL.test(f) || NAMED.test(f);
      return hasRaw ? m : "TOKEN";
    });
  } while (out !== prev);
  return out;
}

/** Lines (1-based) in a CSS string that carry a raw colour literal. */
function rawColourLines(css: string): { line: number; text: string }[] {
  const offenders: { line: number; text: string }[] = [];
  const lines = css.split("\n");
  lines.forEach((raw, i) => {
    // Skip pure comment lines and blank lines fast.
    const line = raw;
    if (line.trim().startsWith("/*") || line.trim().startsWith("*")) return;
    if (line.includes(EXCEPTION_MARKER)) return; // allow-listed conscious exception
    // Only the value side of a declaration can carry a colour. Look at text
    // after the first ':' on the line (selectors/property names don't carry
    // colour literals we care about).
    const colon = line.indexOf(":");
    const value = colon === -1 ? line : line.slice(colon + 1);
    const stripped = stripTokenOnlyVars(value);
    if (HEX.test(stripped) || FUNCTIONAL.test(stripped) || NAMED.test(stripped)) {
      offenders.push({ line: i + 1, text: raw.trim() });
    }
  });
  return offenders;
}

describe("no raw colour literals — nav-chrome stragglers (WP-008)", () => {
  for (const [name, file] of Object.entries(MODULES)) {
    it(`${name} carries no raw colour literal (only var(--*))`, () => {
      const css = readFileSync(file, "utf8");
      const offenders = rawColourLines(css);
      expect(
        offenders,
        `${name} still has raw colour literals (tokenise to var(--*)):\n` +
          offenders.map((o) => `  L${o.line}: ${o.text}`).join("\n"),
      ).toEqual([]);
    });
  }

  it("the var(--x, #raw) fallback scanner actually fires on a raw fallback (guards the scanner)", () => {
    // Self-check: the detector must flag a raw fallback arm, else a green run
    // could be a false negative.
    const sample = ".x { color: var(--text-muted, #888); }";
    expect(rawColourLines(sample).length).toBe(1);
  });

  it("the scanner does NOT flag a token-only fallback chain (guards against false positives)", () => {
    const sample = ".x { border: 1px solid var(--border, var(--foreground)); }";
    expect(rawColourLines(sample)).toEqual([]);
  });

  it("the scanner ignores non-colour values and keywords", () => {
    const sample =
      ".x { width: 50%; opacity: 0.5; background: transparent; color: inherit; border-color: currentColor; }";
    expect(rawColourLines(sample)).toEqual([]);
  });
});
