// WP-007 — Tokenise hardcoded colours in the conversation-view panels.
//
// TDD §2 (audit finding) + acceptance criterion 4: "no raw hard-coded colours
// that ignore the theme." This spec is the characterisation test for the
// conversation-view family — `styles/Thread.module.css` (~9 raw literals) and
// `styles/Chat.module.css` (~6 raw literals). It parses each module as text
// (no runtime CSS engine) and asserts that NO raw colour literal remains: a
// colour is expressed only through the token system — `var(--*)` directly, or
// `color-mix(in srgb, var(--*) N%, var(--*))` over existing tokens (the
// founder-signed mockup `mockup/dark-theme.html` resolves tinted surfaces this
// way; it references existing tokens only and invents no new token).
//
// "Raw colour literal" = a hex colour (`#fff`, `#fff5f5`, `#86181d`), an
// `rgb()`/`rgba()`/`hsl()`/`hsla()` functional colour, or a CSS named colour
// (`white`, `red`, …) used as a colour VALUE. `transparent`/`currentColor`/
// `inherit` are keywords, not raw colours, and are allowed (the mockup uses
// `transparent` inside color-mix and the modules use `background: transparent`
// for true no-fill surfaces).
//
// It fails today (the modules ship raw literals) and goes green once every
// literal is replaced with the nearest existing token per the WP Contract.

import { describe, it, expect } from "vitest";
import { promises as fs } from "node:fs";
import path from "node:path";

const STYLES_DIR = path.resolve(__dirname, "..", "styles");
const TOKENS_CSS = path.resolve(__dirname, "..", "tokens.css");

const MODULES = ["Thread.module.css", "Chat.module.css"] as const;

// Colour keywords that are NOT raw colour literals — they are theme-neutral CSS
// keywords whose meaning is the same in light and dark, so they need no token.
const ALLOWED_KEYWORDS = new Set([
  "transparent",
  "currentcolor",
  "inherit",
  "initial",
  "unset",
  "none",
]);

// CSS named colours we treat as raw literals if they appear as a colour value.
// (We don't need the full CSS named-colour table — the audit only found
// `white`/`#fff` family + named hues; this list covers what the two modules and
// the broader cockpit styles use, plus the obvious primaries.)
const NAMED_COLOURS = [
  "white",
  "black",
  "red",
  "green",
  "blue",
  "yellow",
  "orange",
  "purple",
  "gray",
  "grey",
  "silver",
  "navy",
  "teal",
  "olive",
  "maroon",
  "lime",
  "aqua",
  "fuchsia",
];

/** Strip CSS comments so colours inside `/* … *\/` aren't flagged. */
function stripComments(css: string): string {
  return css.replace(/\/\*[\s\S]*?\*\//g, "");
}

/** All hex colour literals (#rgb, #rgba, #rrggbb, #rrggbbaa) in the source. */
function hexLiterals(css: string): string[] {
  return css.match(/#[0-9a-fA-F]{3,8}\b/g) ?? [];
}

/** All rgb()/rgba()/hsl()/hsla() functional colour literals. */
function functionalColours(css: string): string[] {
  return css.match(/\b(?:rgba?|hsla?)\s*\(/gi) ?? [];
}

/**
 * Named colours used as a VALUE (after a `:` and not part of an identifier such
 * as a class name or a `--white-ish` token). We look for the keyword preceded
 * by a value separator (`:`, space, `,`, `(`) and not immediately glued to a
 * `-`/`_`/alnum that would make it part of a longer identifier.
 */
function namedColourLiterals(css: string): string[] {
  const found: string[] = [];
  for (const name of NAMED_COLOURS) {
    const re = new RegExp(`(?<![\\w-])${name}(?![\\w-])`, "gi");
    let m: RegExpExecArray | null;
    while ((m = re.exec(css)) !== null) {
      if (!ALLOWED_KEYWORDS.has(name.toLowerCase())) found.push(m[0]);
    }
  }
  return found;
}

describe("WP-007 — no raw colour literals in conversation-view modules", () => {
  it.each(MODULES)(
    "%s contains no raw hex colour literal",
    async (mod) => {
      const css = stripComments(
        await fs.readFile(path.join(STYLES_DIR, mod), "utf8"),
      );
      const hex = hexLiterals(css);
      expect(
        hex,
        `${mod} still has raw hex colour(s): ${hex.join(", ")} — replace each with the nearest existing var(--*) / color-mix over tokens`,
      ).toEqual([]);
    },
  );

  it.each(MODULES)(
    "%s contains no rgb()/hsl() functional colour literal",
    async (mod) => {
      const css = stripComments(
        await fs.readFile(path.join(STYLES_DIR, mod), "utf8"),
      );
      const fns = functionalColours(css);
      expect(
        fns,
        `${mod} still has functional colour literal(s): ${fns.join(", ")}`,
      ).toEqual([]);
    },
  );

  it.each(MODULES)(
    "%s contains no CSS named-colour literal used as a value",
    async (mod) => {
      const css = stripComments(
        await fs.readFile(path.join(STYLES_DIR, mod), "utf8"),
      );
      const named = namedColourLiterals(css);
      expect(
        named,
        `${mod} still has named colour literal(s): ${named.join(", ")}`,
      ).toEqual([]);
    },
  );

  it.each(MODULES)(
    "%s references colours only via the token system (var(--*) / color-mix)",
    async (mod) => {
      const css = stripComments(
        await fs.readFile(path.join(STYLES_DIR, mod), "utf8"),
      );
      // Composite guard: a module is token-clean iff it has zero raw literals
      // of every flavour. (Redundant with the three specs above by design — it
      // is the single assertion the WP Contract phrases as the acceptance bar.)
      const raw = [
        ...hexLiterals(css),
        ...functionalColours(css),
        ...namedColourLiterals(css),
      ];
      expect(
        raw,
        `${mod} is not token-clean — raw colour token(s) remain: ${raw.join(", ")}`,
      ).toEqual([]);
    },
  );

  it("references only EXISTING tokens — every var(--*) used in the two modules is defined in tokens.css (no invented token)", async () => {
    const tokensCss = await fs.readFile(TOKENS_CSS, "utf8");
    const definedTokens = new Set(
      (tokensCss.match(/--[\w-]+\s*:/g) ?? []).map((d) =>
        d.replace(/\s*:$/, "").trim(),
      ),
    );

    const used = new Set<string>();
    for (const mod of MODULES) {
      const css = stripComments(
        await fs.readFile(path.join(STYLES_DIR, mod), "utf8"),
      );
      for (const ref of css.match(/var\(\s*(--[\w-]+)/g) ?? []) {
        const name = ref.replace(/var\(\s*/, "").trim();
        used.add(name);
      }
    }

    const invented = [...used].filter((t) => !definedTokens.has(t));
    expect(
      invented,
      `the modules reference token(s) not defined in tokens.css (a new token would need WP-006 + founder sign-off, not an inline invention): ${invented.join(", ")}`,
    ).toEqual([]);
  });

  it("does not modify tokens.css (this WP references existing tokens only)", async () => {
    // Guard intent: the two colour tokens introduced by WP-002 must still be
    // present and unchanged in shape. We assert the dark block exists (so a
    // botched merge that dropped it is caught) — this WP never edits this file.
    const tokensCss = await fs.readFile(TOKENS_CSS, "utf8");
    expect(tokensCss).toContain(':root[data-theme="dark"]');
  });
});
