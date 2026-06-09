// WP-009 — <ChangeCard> accessibility audit for the SELECTED + FOCUSED states
// (RED-side a11y, Green DoD) — S-27 extension for CS-1 / CS-2.
//
// jest-axe on the card in its WP-009 states, in BOTH light and dark:
//   - selected (aria-current="true" + the non-colour marker)
//   - focused (the card link holds focus → the focus-visible ring)
//   - selected + waiting (the additive precedence composition)
// jsdom computes no layout, so axe validates the STRUCTURAL a11y — that
// aria-current is a valid value on the link, that focus lands on a real
// interactive element, and that the additive marker introduces no role/name
// violation.

import { describe, it, expect, afterEach } from "vitest";
import { render } from "@testing-library/react";
import { axe } from "jest-axe";
import { MemoryRouter } from "react-router-dom";
import type { Change } from "../../../shared/api-types";
import { ChangeCard } from "../components/ChangeCard";

function makeChange(overrides: Partial<Change> = {}): Change {
  return {
    changeId: "01AAA",
    handle: "CH-01AAA",
    slug: "first-change",
    primitive: "fix",
    branch: "feat/a",
    worktreePath: "/w/a",
    intent: "the first in-flight change",
    baseBranch: "dev",
    baseSha: null,
    createdAt: "2026-06-09T10:00:00Z",
    updatedAt: "2026-06-09T11:00:00Z",
    stage: "implement",
    liveness: { status: "running", pid: 1 },
    needsAttention: { flagged: false, reason: null },
    health: { state: "on-track", reason: "tests green" },
    lastActivityAt: "2026-06-09T10:45:00Z",
    ...overrides,
  };
}

function setTheme(theme: "light" | "dark") {
  if (theme === "dark") document.documentElement.dataset.theme = "dark";
  else delete document.documentElement.dataset.theme;
}

afterEach(() => {
  delete document.documentElement.dataset.theme;
});

const VARIANTS: Record<
  string,
  { overrides: Partial<Change>; selected: boolean; focus: boolean }
> = {
  selected: { overrides: {}, selected: true, focus: false },
  focused: { overrides: {}, selected: false, focus: true },
  "selected+focused": { overrides: {}, selected: true, focus: true },
  "selected+waiting": {
    overrides: { needsAttention: { flagged: true, reason: "blocked" } },
    selected: true,
    focus: false,
  },
};

describe("<ChangeCard> selected + focused states have no axe violations, light + dark (WP-009)", () => {
  for (const theme of ["light", "dark"] as const) {
    for (const [name, spec] of Object.entries(VARIANTS)) {
      it(`${theme} · ${name} has no axe violations`, async () => {
        setTheme(theme);
        const { container, getByRole } = render(
          <MemoryRouter>
            <ChangeCard
              change={makeChange(spec.overrides)}
              selected={spec.selected}
            />
          </MemoryRouter>,
        );
        if (spec.focus) {
          (getByRole("link") as HTMLElement).focus();
        }
        const results = await axe(container);
        expect(results).toHaveNoViolations();
      });
    }
  }
});
