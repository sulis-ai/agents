// WP-006 — characterisation: no raw colours in the dashboard change-card
// surface (stage badges + dashboard chrome).
//
// TDD §2 audit finding + spec acceptance criterion 4 ("no raw hard-coded
// colours that ignore the theme"). This spec parses the two CSS modules that
// make up the dashboard's change-card surface and asserts they carry NO raw
// colour literal — only `var(--*)` references — for:
//   - the six ACTIVE stage classes in StageBadge.module.css
//     (recon / specify / design / implement / review / ship); the terminal
//     `shipped` / `unknown` classes already use var(--muted*) and are out of
//     scope for new work.
//   - the dashboard error chrome in Dashboard.module.css (errorBox /
//     errorMessage).
//
// It also pins the regression baseline: each new --stage-*-{bg,fg,border}
// token must be defined in BOTH the light `:root` block and the dark
// `:root[data-theme="dark"]` block of tokens.css, with the EXACT values from
// the WP-006 Contract table (which mirror the founder-signed mockup,
// .architecture/feat-dark-mode/mockup/dark-theme.html). The light values
// equal today's literals → light-mode is pixel-unchanged; the dark values
// are the founder-signed net-new pairings.
//
// Parses CSS as text (no runtime CSS engine), mirroring tokens.dark.test.ts.

import { describe, it, expect } from "vitest";
import { promises as fs } from "node:fs";
import path from "node:path";

const SRC = path.resolve(__dirname, "..");
const TOKENS_CSS = path.join(SRC, "tokens.css");
const STAGE_BADGE_CSS = path.join(SRC, "components", "StageBadge.module.css");
const DASHBOARD_CSS = path.join(SRC, "pages", "Dashboard.module.css");

// The six active workflow stages this WP tokenises (terminal shipped/unknown
// already use tokens and are excluded).
const ACTIVE_STAGES = [
  "recon",
  "specify",
  "design",
  "implement",
  "review",
  "ship",
] as const;

// The exact stage-badge token values, from the WP-006 Contract table (which
// mirrors the signed-off mockup). Suffix convention: -bg / -fg / -border.
// light = today's literals (pixel-unchanged); dark = founder-signed pairings.
const STAGE_TOKENS: Record<
  (typeof ACTIVE_STAGES)[number],
  {
    light: { bg: string; fg: string; border: string };
    dark: { bg: string; fg: string; border: string };
  }
> = {
  recon: {
    light: { bg: "#f1f8ff", fg: "#2563EB", border: "#c8e1ff" },
    dark: { bg: "#16263a", fg: "#7fb0ff", border: "#234a73" },
  },
  specify: {
    light: { bg: "#fff5b1", fg: "#735c0f", border: "#ffd33d" },
    dark: { bg: "#332b10", fg: "#f0c75a", border: "#5c4d1e" },
  },
  design: {
    light: { bg: "#e6e6fa", fg: "#4b0082", border: "#c5c5e6" },
    dark: { bg: "#241c3a", fg: "#b79cff", border: "#3d2f63" },
  },
  implement: {
    light: { bg: "#e1ffe1", fg: "#22863a", border: "#c0e6c0" },
    dark: { bg: "#1a3014", fg: "#9bd86a", border: "#345526" },
  },
  review: {
    light: { bg: "#fff0e6", fg: "#c04a00", border: "#ffd0b0" },
    dark: { bg: "#3a2310", fg: "#f2a368", border: "#63401f" },
  },
  ship: {
    light: { bg: "#d4edda", fg: "#155724", border: "#a5d6a7" },
    dark: { bg: "#13301d", fg: "#73d391", border: "#245636" },
  },
};

/**
 * Return the body (between the outermost braces) of the first block whose
 * selector matches `selector`. Brace-balanced so nested constructs don't
 * truncate early. Returns null if absent. (Mirrors tokens.dark.test.ts.)
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

/** Extract the declaration block body for a CSS-module class `.name { ... }`. */
function classBody(css: string, className: string): string | null {
  // Match `.className` as a whole word (not `.classNameLong`) followed by `{`.
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

// Raw colour literal detectors. A token reference `var(--x)` is allowed; a
// raw hex / rgb()/rgba() / hsl() / named colour in a colour-bearing property
// is not. We scan the declaration body for the literal forms directly.
const HEX_RE = /#[0-9a-fA-F]{3,8}\b/;
const RGB_HSL_RE = /\b(?:rgb|rgba|hsl|hsla)\s*\(/i;
// A conservative set of CSS named colours that could appear as stage tints /
// error chrome. We don't need the full 148-name list — only ones plausibly
// used here — but include the common ones to catch regressions.
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

/** Find raw colour literals in a declaration body, ignoring var(--*) refs. */
function rawColourLiterals(body: string): string[] {
  const hits: string[] = [];
  // Inspect each declaration line independently.
  for (const rawLine of body.split(/[;\n]/)) {
    const line = rawLine.trim();
    if (!line) continue;
    // Skip comment-only fragments.
    if (line.startsWith("/*") || line.startsWith("*")) continue;
    const hex = line.match(HEX_RE);
    if (hex) hits.push(hex[0]);
    const fn = line.match(RGB_HSL_RE);
    if (fn) hits.push(fn[0]);
    // Named colours: only flag when used as a property value (after a `:`),
    // as a standalone word, and not inside a var() name.
    const valuePart = line.includes(":")
      ? line.slice(line.indexOf(":") + 1)
      : line;
    for (const name of NAMED_COLOURS) {
      const nameRe = new RegExp(`(^|[\\s(])${name}(?![\\w-])`, "i");
      if (nameRe.test(valuePart)) hits.push(name);
    }
  }
  return hits;
}

/** Count `--name:` definitions of a custom property inside a CSS block body. */
function definitionValue(body: string, name: string): string | null {
  const re = new RegExp(
    `(?:^|[;{\\s])${name.replace(/-/g, "\\-")}\\s*:\\s*([^;}]+)`,
  );
  const m = re.exec(body);
  const captured = m?.[1];
  return captured !== undefined ? captured.trim() : null;
}

describe("no raw colours — dashboard change-card surface (WP-006)", () => {
  it("StageBadge.module.css: each active stage class uses only var(--*) (no raw literal)", async () => {
    const css = await fs.readFile(STAGE_BADGE_CSS, "utf8");
    const offenders: Record<string, string[]> = {};
    for (const stage of ACTIVE_STAGES) {
      const body = classBody(css, stage);
      expect(body, `expected a .${stage} class in StageBadge.module.css`).not.toBeNull();
      const raw = rawColourLiterals(body as string);
      if (raw.length) offenders[stage] = raw;
    }
    expect(
      offenders,
      `active stage classes still contain raw colour literals: ${JSON.stringify(offenders)}`,
    ).toEqual({});
  });

  it("StageBadge.module.css: each active stage references its --stage-*-{bg,fg,border} tokens", async () => {
    const css = await fs.readFile(STAGE_BADGE_CSS, "utf8");
    for (const stage of ACTIVE_STAGES) {
      const body = classBody(css, stage);
      expect(body).not.toBeNull();
      const b = body as string;
      expect(b, `.${stage} must reference --stage-${stage}-bg`).toContain(
        `var(--stage-${stage}-bg)`,
      );
      expect(b, `.${stage} must reference --stage-${stage}-fg`).toContain(
        `var(--stage-${stage}-fg)`,
      );
      expect(b, `.${stage} must reference --stage-${stage}-border`).toContain(
        `var(--stage-${stage}-border)`,
      );
    }
  });

  it("Dashboard.module.css: the error chrome uses only var(--*) (no raw literal)", async () => {
    const css = await fs.readFile(DASHBOARD_CSS, "utf8");
    const offenders: Record<string, string[]> = {};
    for (const cls of ["errorBox", "errorMessage"]) {
      const body = classBody(css, cls);
      expect(body, `expected a .${cls} class in Dashboard.module.css`).not.toBeNull();
      const raw = rawColourLiterals(body as string);
      if (raw.length) offenders[cls] = raw;
    }
    expect(
      offenders,
      `dashboard error chrome still contains raw colour literals: ${JSON.stringify(offenders)}`,
    ).toEqual({});
  });

  it("Dashboard.module.css: error chrome maps to the existing --destructive* tokens", async () => {
    const css = await fs.readFile(DASHBOARD_CSS, "utf8");
    const errorBox = classBody(css, "errorBox");
    expect(errorBox).not.toBeNull();
    // The error surface must reference the destructive token family rather
    // than raw literals (the exact mapping is bg/border/text → destructive*).
    expect(errorBox as string).toContain("var(--destructive");
  });

  it("tokens.css: all 18 LIGHT stage-badge tokens are defined with the exact Contract values (pixel-unchanged baseline)", async () => {
    const css = await fs.readFile(TOKENS_CSS, "utf8");
    const light = blockBody(css, ":root {");
    expect(light, "expected a light :root block in tokens.css").not.toBeNull();
    const body = light as string;

    const mismatches: string[] = [];
    for (const stage of ACTIVE_STAGES) {
      for (const part of ["bg", "fg", "border"] as const) {
        const name = `--stage-${stage}-${part}`;
        const got = definitionValue(body, name);
        const want = STAGE_TOKENS[stage].light[part];
        if (got?.toLowerCase() !== want.toLowerCase()) {
          mismatches.push(`${name}: got ${got ?? "MISSING"}, want ${want}`);
        }
      }
    }
    expect(mismatches, mismatches.join("\n")).toEqual([]);
  });

  it("tokens.css: all 18 DARK stage-badge tokens are defined with the exact signed-off values", async () => {
    const css = await fs.readFile(TOKENS_CSS, "utf8");
    const dark = blockBody(css, ':root[data-theme="dark"]');
    expect(dark, "expected a dark :root[data-theme=\"dark\"] block").not.toBeNull();
    const body = dark as string;

    const mismatches: string[] = [];
    for (const stage of ACTIVE_STAGES) {
      for (const part of ["bg", "fg", "border"] as const) {
        const name = `--stage-${stage}-${part}`;
        const got = definitionValue(body, name);
        const want = STAGE_TOKENS[stage].dark[part];
        if (got?.toLowerCase() !== want.toLowerCase()) {
          mismatches.push(`${name}: got ${got ?? "MISSING"}, want ${want}`);
        }
      }
    }
    expect(mismatches, mismatches.join("\n")).toEqual([]);
  });

  it("tokens.css: uses the reconciled -border suffix, never the retired -bd shorthand", async () => {
    const css = await fs.readFile(TOKENS_CSS, "utf8");
    expect(
      /--stage-[a-z]+-bd\b/.test(css),
      "found a retired -bd stage-badge token; the reconciled suffix is -border",
    ).toBe(false);
  });
});
