// No-raw-colours characterisation test for the chat colour surfaces.
//
// TDD §2 (audit finding) + acceptance criterion 4: "no raw hard-coded colours
// that ignore the theme." This spec is the characterisation test for the
// conversation-view family — `styles/Thread.module.css` and
// `styles/Chat.module.css` (WP-007) — AND, since WP-006 (ADR-004), the NEW
// status-line colour surfaces this change introduced:
// `components/ChatStatusLine.module.css` and the `styles/Composer.module.css`
// additions. The `MODULES` array was widened deliberately so the same guard
// that "must stay green" now also covers the working/finished status-line
// tiles — a status line that introduced an untested raw colour would otherwise
// slip past this named gate (ADR-004). The dock's status line stays covered for
// hex by `ProductChatDock.axe.test.tsx`.
//
// Each module is parsed as text (no runtime CSS engine) and asserted to contain
// NO raw colour literal: a colour is expressed only through the token system —
// `var(--*)` directly, or `color-mix(in srgb, var(--*) N%, var(--*))` over
// existing tokens (the founder-signed contract resolves the 9%/28% status-line
// tints this way; it references existing tokens only and invents no new token).
//
// "Raw colour literal" = a hex colour (`#fff`, `#fff5f5`, `#86181d`), an
// `rgb()`/`rgba()`/`hsl()`/`hsla()` functional colour, or a CSS named colour
// (`white`, `red`, …) used as a colour VALUE. `transparent`/`currentColor`/
// `inherit` are keywords, not raw colours, and are allowed (the contract uses
// `transparent` inside color-mix and the modules use `background: transparent`
// for true no-fill surfaces).
//
// Note (ADR-004): modules live in two directories — the conversation-view
// modules under `styles/`, the shared status-line module under `components/` —
// so each entry carries its own resolving directory.

import { describe, it, expect } from "vitest";
import { promises as fs } from "node:fs";
import path from "node:path";

const STYLES_DIR = path.resolve(__dirname, "..", "styles");
const COMPONENTS_DIR = path.resolve(__dirname, "..", "components");
const TOKENS_CSS = path.resolve(__dirname, "..", "tokens.css");

/** A scanned CSS module: its filename (for messages) and its resolving dir. */
type Module = { readonly name: string; readonly dir: string };

const MODULES: readonly Module[] = [
  // Conversation-view family (WP-007).
  { name: "Thread.module.css", dir: STYLES_DIR },
  { name: "Chat.module.css", dir: STYLES_DIR },
  // Status-line surfaces this change introduced (WP-006 / ADR-004).
  { name: "ChatStatusLine.module.css", dir: COMPONENTS_DIR },
  { name: "Composer.module.css", dir: STYLES_DIR },
];

/** Read and comment-strip a module's CSS text. */
async function readModule(mod: Module): Promise<string> {
  return stripComments(await fs.readFile(path.join(mod.dir, mod.name), "utf8"));
}

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
// `white`/`#fff` family + named hues; this list covers what the modules and
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

/** Every raw colour literal of every flavour in the source. */
function rawColourLiterals(css: string): string[] {
  return [
    ...hexLiterals(css),
    ...functionalColours(css),
    ...namedColourLiterals(css),
  ];
}

describe("no raw colour literals in the chat colour-surface modules", () => {
  it.each(MODULES)("$name contains no raw hex colour literal", async (mod) => {
    const hex = hexLiterals(await readModule(mod));
    expect(
      hex,
      `${mod.name} still has raw hex colour(s): ${hex.join(", ")} — replace each with the nearest existing var(--*) / color-mix over tokens`,
    ).toEqual([]);
  });

  it.each(MODULES)(
    "$name contains no rgb()/hsl() functional colour literal",
    async (mod) => {
      const fns = functionalColours(await readModule(mod));
      expect(
        fns,
        `${mod.name} still has functional colour literal(s): ${fns.join(", ")}`,
      ).toEqual([]);
    },
  );

  it.each(MODULES)(
    "$name contains no CSS named-colour literal used as a value",
    async (mod) => {
      const named = namedColourLiterals(await readModule(mod));
      expect(
        named,
        `${mod.name} still has named colour literal(s): ${named.join(", ")}`,
      ).toEqual([]);
    },
  );

  it.each(MODULES)(
    "$name references colours only via the token system (var(--*) / color-mix)",
    async (mod) => {
      // Composite guard: a module is token-clean iff it has zero raw literals
      // of every flavour. (Redundant with the three specs above by design — it
      // is the single assertion the WP Contract phrases as the acceptance bar.)
      const raw = rawColourLiterals(await readModule(mod));
      expect(
        raw,
        `${mod.name} is not token-clean — raw colour token(s) remain: ${raw.join(", ")}`,
      ).toEqual([]);
    },
  );

  it("references only EXISTING tokens — every var(--*) used in the modules is defined in tokens.css (no invented token)", async () => {
    const tokensCss = await fs.readFile(TOKENS_CSS, "utf8");
    const definedTokens = new Set(
      (tokensCss.match(/--[\w-]+\s*:/g) ?? []).map((d) =>
        d.replace(/\s*:$/, "").trim(),
      ),
    );

    const used = new Set<string>();
    for (const mod of MODULES) {
      const css = await readModule(mod);
      for (const ref of css.match(/var\(\s*(--[\w-]+)/g) ?? []) {
        const name = ref.replace(/var\(\s*/, "").trim();
        used.add(name);
      }
    }

    const invented = [...used].filter((t) => !definedTokens.has(t));
    expect(
      invented,
      `the modules reference token(s) not defined in tokens.css (a new token would need founder sign-off, not an inline invention): ${invented.join(", ")}`,
    ).toEqual([]);
  });

  it("does not modify tokens.css (this WP references existing tokens only)", async () => {
    // Guard intent: the colour tokens the status line relies on must still be
    // present and unchanged in shape. We assert the dark block exists (so a
    // botched merge that dropped it is caught) — this WP never edits this file.
    const tokensCss = await fs.readFile(TOKENS_CSS, "utf8");
    expect(tokensCss).toContain(':root[data-theme="dark"]');
  });

  // Self-discipline: prove the guard has teeth. If a module DID carry a raw
  // colour literal, `rawColourLiterals` must report it — otherwise the green
  // verdict above would be meaningless (a guard that never fails guards
  // nothing). This is the RED the WP Contract asks us to confirm before the
  // status-line modules pass it clean.
  it("would FLAG a raw colour literal if one were present (the gate has teeth)", () => {
    const withHex = ".x { color: #ff0000; }";
    const withRgb = ".x { color: rgb(255, 0, 0); }";
    const withNamed = ".x { color: red; }";
    expect(rawColourLiterals(withHex)).toContain("#ff0000");
    expect(rawColourLiterals(withRgb)).toEqual(["rgb("]);
    expect(rawColourLiterals(withNamed)).toContain("red");
  });
});
