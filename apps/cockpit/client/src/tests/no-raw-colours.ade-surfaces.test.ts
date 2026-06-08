// CH-01KTHP (dark-mode re-fit) — characterisation guard: no raw colour
// literals in the cockpit surfaces #216 ("Autonomous Delivery Environment")
// introduced AFTER dark mode was built.
//
// Dark mode (WP-002..009) tokenised the surfaces that existed when it shipped.
// #216 then landed a tabbed workspace + several new surfaces (the workspace
// shell/top bar, the product switcher, the change workspace, the conversation
// view, the origin/provenance lenses, the live terminal) — and these carried
// raw colour literals (#hex, rgba(), brand hexes in a gradient) that would NOT
// re-theme under `:root[data-theme="dark"]`. The re-fit tokenises them; this
// guard pins that they stay tokenised, so a future #216-area edit can't
// silently reintroduce a light-only literal and break dark mode again.
//
// Same detector contract as no-raw-colours.sidebar-files-liveness.test.ts
// (WP-008): a violation is a raw hex / functional colour / CSS named colour on
// the *value side* of a declaration, including a raw `var(--x, #raw)` fallback
// arm. Token-only `var(--*)` (and `var(--x, var(--y))` chains) are fine; so are
// non-colour values, comments, and lines carrying the `status-exception`
// marker.

import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";

const SRC = path.resolve(__dirname, "..");

// The #216 surfaces tokenised by the dark-mode re-fit. tokens.css is NOT here:
// it is the token DEFINITION file (its literals ARE the token values).
const MODULES = {
  "layouts/WorkspaceShell.module.css": path.join(SRC, "layouts", "WorkspaceShell.module.css"),
  "components/ProductSwitcher.module.css": path.join(SRC, "components", "ProductSwitcher.module.css"),
  "components/LiveTerminal.module.css": path.join(SRC, "components", "LiveTerminal.module.css"),
  "styles/ChangeWorkspace.module.css": path.join(SRC, "styles", "ChangeWorkspace.module.css"),
  "styles/Conversation.module.css": path.join(SRC, "styles", "Conversation.module.css"),
  "styles/Origin.module.css": path.join(SRC, "styles", "Origin.module.css"),
  "styles/ProvenanceView.module.css": path.join(SRC, "styles", "ProvenanceView.module.css"),
} as const;

const EXCEPTION_MARKER = "status-exception";

const HEX = /#[0-9a-fA-F]{3,8}\b/;
const FUNCTIONAL = /\b(?:rgb|rgba|hsl|hsla)\s*\(/;
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

/** Collapse token-only var() references so the scanners only see raw arms. */
function stripTokenOnlyVars(value: string): string {
  let prev: string;
  let out = value;
  const tokenOnly = /var\(\s*--[\w-]+\s*\)/g;
  do {
    prev = out;
    out = out.replace(tokenOnly, "TOKEN");
  } while (out !== prev);
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

/** Lines (1-based) carrying a raw colour literal on the declaration value side. */
function rawColourLines(css: string): { line: number; text: string }[] {
  const offenders: { line: number; text: string }[] = [];
  const lines = css.split("\n");
  lines.forEach((raw, i) => {
    const line = raw;
    if (line.trim().startsWith("/*") || line.trim().startsWith("*")) return;
    if (line.includes(EXCEPTION_MARKER)) return;
    const colon = line.indexOf(":");
    const value = colon === -1 ? line : line.slice(colon + 1);
    const stripped = stripTokenOnlyVars(value);
    if (HEX.test(stripped) || FUNCTIONAL.test(stripped) || NAMED.test(stripped)) {
      offenders.push({ line: i + 1, text: raw.trim() });
    }
  });
  return offenders;
}

describe("no raw colour literals — #216 / ADE surfaces (CH-01KTHP re-fit)", () => {
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

  it("the value-side scanner flags a raw fallback arm (guards the scanner)", () => {
    const sample = ".x { color: var(--text-muted, #888); }";
    expect(rawColourLines(sample).length).toBe(1);
  });

  it("the scanner accepts a theme-derived color-mix (var(--token) ... transparent)", () => {
    const sample =
      ".x { box-shadow: 0 1px 2px color-mix(in srgb, var(--foreground) 6%, transparent); }";
    expect(rawColourLines(sample)).toEqual([]);
  });
});
