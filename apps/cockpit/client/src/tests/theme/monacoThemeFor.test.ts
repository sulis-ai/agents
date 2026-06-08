// WP-005 — monacoThemeFor() unit tests (ADR-002, TDD §5.1).
//
// The pure helper is the single source of truth for the app-theme →
// Monaco-theme-id mapping: dark → "vs-dark", light → "vs" (Monaco's
// shipped built-in themes, CP-01). No React, no DOM — it is the testable
// seam both wrappers (MonacoFileInner / MonacoDiffInner) consume.

import { describe, expect, it } from "vitest";
import { monacoThemeFor } from "../../theme/monacoThemeFor";

describe("monacoThemeFor", () => {
  it("maps the dark app theme to Monaco's built-in dark theme", () => {
    expect(monacoThemeFor("dark")).toBe("vs-dark");
  });

  it("maps the light app theme to Monaco's built-in light theme", () => {
    expect(monacoThemeFor("light")).toBe("vs");
  });
});
