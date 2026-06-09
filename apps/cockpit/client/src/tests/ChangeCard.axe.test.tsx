// WP-005 — <ChangeCard> accessibility audit (RED) — S-27.
//
// jest-axe on the card for EVERY content variant, in BOTH light and dark:
//   waiting / on-track / off-track / unknown-health / unknown-liveness /
//   no-recency. The theme is set via documentElement[data-theme] exactly as
//   the app sets it; jsdom doesn't compute layout so axe validates the
//   structural a11y (roles / names / aria), which is where the dropped state
//   WORD makes the SR labels load-bearing.

import { describe, it, expect, afterEach } from "vitest";
import { render } from "@testing-library/react";
import { axe } from "jest-axe";
import { MemoryRouter } from "react-router-dom";
import type { Change } from "../../../shared/api-types";
import { ChangeCard } from "../components/ChangeCard";

function makeChange(overrides: Partial<Change> = {}): Change {
  return {
    changeId: "01KTMF",
    handle: "CH-01KTMF",
    slug: "safe-change-resolution",
    primitive: "fix",
    branch: "feat/x",
    worktreePath: "/w",
    intent: "make change resolution refuse a dirty worktree",
    baseBranch: "dev",
    baseSha: null,
    createdAt: "2026-06-09T10:00:00Z",
    updatedAt: "2026-06-09T11:00:00Z",
    stage: "implement",
    liveness: { status: "running", pid: 1 },
    needsAttention: { flagged: false, reason: null },
    health: { state: "on-track", reason: "tests green" },
    lastActivityAt: "2026-06-09T10:59:50Z",
    ...overrides,
  };
}

const VARIANTS: Record<string, Partial<Change>> = {
  waiting: {
    needsAttention: { flagged: true, reason: "blocked" },
    health: { state: "on-track", reason: "tests green" },
  },
  "on-track": {
    needsAttention: { flagged: false, reason: null },
    health: { state: "on-track", reason: "tests green, on plan" },
  },
  "off-track": {
    needsAttention: { flagged: false, reason: null },
    health: { state: "off-track", reason: "tests failing" },
  },
  "unknown-health": {
    needsAttention: { flagged: false, reason: null },
    health: { state: "unknown", reason: "no checks have run yet" },
  },
  "unknown-liveness": {
    liveness: { status: "unknown", reason: "no session record" },
    needsAttention: { flagged: false, reason: null },
    health: { state: "on-track", reason: "tests green" },
  },
  "no-recency": {
    liveness: { status: "unknown", reason: "no session" },
    lastActivityAt: null,
    needsAttention: { flagged: false, reason: null },
    health: { state: "unknown", reason: "too early to tell" },
  },
};

function setTheme(theme: "light" | "dark") {
  if (theme === "dark") document.documentElement.dataset.theme = "dark";
  else delete document.documentElement.dataset.theme;
}

afterEach(() => {
  delete document.documentElement.dataset.theme;
});

describe("<ChangeCard> WCAG AA across all variants, light + dark (S-27)", () => {
  for (const theme of ["light", "dark"] as const) {
    for (const [name, overrides] of Object.entries(VARIANTS)) {
      it(`${theme} · ${name} variant has no axe violations`, async () => {
        setTheme(theme);
        const { container } = render(
          <MemoryRouter>
            <ChangeCard change={makeChange(overrides)} />
          </MemoryRouter>,
        );
        const results = await axe(container);
        expect(results).toHaveNoViolations();
      });
    }
  }
});
