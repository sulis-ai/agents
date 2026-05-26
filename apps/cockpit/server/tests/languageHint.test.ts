// WP-007 — unit tests for the languageHint extension-to-Monaco-id map.
//
// Per TDD §5.1 / WP-007 Contract: a small static map from extension
// to Monaco language id. Lookup is by lowercased extension; unknown
// extensions return null (Monaco will fall back to plain text).

import { describe, it, expect } from "vitest";

import { languageHint, LANGUAGE_HINTS } from "../lib/languageHint";

describe("languageHint", () => {
  it("returns the mapped language id for a TypeScript file", () => {
    expect(languageHint("index.ts")).toBe("typescript");
  });

  it("returns the mapped language id for a TSX file", () => {
    expect(languageHint("Component.tsx")).toBe("typescript");
  });

  it("returns the mapped language id for a Python file", () => {
    expect(languageHint("script.py")).toBe("python");
  });

  it("returns the mapped language id for a Markdown file", () => {
    expect(languageHint("README.md")).toBe("markdown");
  });

  it("returns null for an unknown extension", () => {
    expect(languageHint("data.xyz")).toBeNull();
  });

  it("returns null for a file with no extension", () => {
    expect(languageHint("Makefile")).toBeNull();
  });

  it("is case-insensitive on the extension", () => {
    expect(languageHint("FILE.TS")).toBe("typescript");
    expect(languageHint("INDEX.JS")).toBe("javascript");
    expect(languageHint("data.JSON")).toBe("json");
  });

  it("handles paths with directories", () => {
    expect(languageHint("apps/cockpit/server/index.ts")).toBe("typescript");
    expect(languageHint("/abs/path/foo.py")).toBe("python");
  });

  it("handles dotfiles correctly (no extension → null)", () => {
    expect(languageHint(".gitignore")).toBeNull();
    expect(languageHint(".env")).toBeNull();
  });

  it("returns the mapped language id for every entry in LANGUAGE_HINTS", () => {
    for (const [ext, id] of Object.entries(LANGUAGE_HINTS)) {
      expect(languageHint(`foo${ext}`)).toBe(id);
    }
  });

  it("LANGUAGE_HINTS contains the expected baseline entries from the WP Contract", () => {
    // Spot-check the baseline. Adding entries is an opportunistic
    // improvement (per WP Risks & notes); removing one is a breaking
    // change. This assertion catches accidental removals.
    expect(LANGUAGE_HINTS[".ts"]).toBe("typescript");
    expect(LANGUAGE_HINTS[".tsx"]).toBe("typescript");
    expect(LANGUAGE_HINTS[".js"]).toBe("javascript");
    expect(LANGUAGE_HINTS[".jsx"]).toBe("javascript");
    expect(LANGUAGE_HINTS[".py"]).toBe("python");
    expect(LANGUAGE_HINTS[".json"]).toBe("json");
    expect(LANGUAGE_HINTS[".jsonl"]).toBe("json");
    expect(LANGUAGE_HINTS[".yaml"]).toBe("yaml");
    expect(LANGUAGE_HINTS[".yml"]).toBe("yaml");
    expect(LANGUAGE_HINTS[".md"]).toBe("markdown");
    expect(LANGUAGE_HINTS[".css"]).toBe("css");
    expect(LANGUAGE_HINTS[".html"]).toBe("html");
    expect(LANGUAGE_HINTS[".sh"]).toBe("shell");
    expect(LANGUAGE_HINTS[".sql"]).toBe("sql");
    expect(LANGUAGE_HINTS[".go"]).toBe("go");
    expect(LANGUAGE_HINTS[".rs"]).toBe("rust");
    expect(LANGUAGE_HINTS[".java"]).toBe("java");
    expect(LANGUAGE_HINTS[".rb"]).toBe("ruby");
  });
});
