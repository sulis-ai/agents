// WP-012 — shipped <ChangeCard> accessibility audit (RED) — NFR-A11Y-1.
//
// jest-axe on the shipped/terminal card in BOTH light and dark. jsdom doesn't
// compute layout, so axe validates the structural a11y (roles / names / aria) —
// which is where the static "Shipped" marker + the "shipped Nd ago" recency
// must carry their meaning in text (never colour/placement alone), so a screen
// reader hears "archived", not silence.

import { describe, it, expect, afterEach } from "vitest";
import { render } from "@testing-library/react";
import { axe } from "jest-axe";
import { MemoryRouter } from "react-router-dom";
import type { Change } from "../../../shared/api-types";
import { ChangeCard } from "../components/ChangeCard";

function makeShipped(overrides: Partial<Change> = {}): Change {
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
    createdAt: "2026-05-20T10:00:00Z",
    updatedAt: "2026-06-04T12:00:00Z",
    stage: "shipped",
    liveness: { status: "running", pid: 4242 },
    needsAttention: { flagged: true, reason: "blocked" },
    health: { state: "off-track", reason: "tests red" },
    lastActivityAt: "2026-06-09T11:59:00Z",
    ...overrides,
  };
}

afterEach(() => {
  document.documentElement.removeAttribute("data-theme");
});

async function expectNoAxe(theme: "light" | "dark") {
  document.documentElement.setAttribute("data-theme", theme);
  const { container } = render(
    <MemoryRouter>
      <ChangeCard
        change={makeShipped()}
        now={new Date("2026-06-09T12:00:00Z")}
      />
    </MemoryRouter>,
  );
  expect(await axe(container)).toHaveNoViolations();
}

describe("shipped <ChangeCard> a11y audit (WP-012)", () => {
  it("has no axe violations in LIGHT theme", async () => {
    await expectNoAxe("light");
  });

  it("has no axe violations in DARK theme", async () => {
    await expectNoAxe("dark");
  });
});
