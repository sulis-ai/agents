// WP-011 — degraded <ChangeCard> accessibility audit (RED) — NFR-A11Y-1 / -4.
//
// jest-axe on the degraded card in BOTH light and dark. jsdom doesn't compute
// layout, so axe validates the structural a11y (roles / names / aria) — which
// is exactly where the dashed 'no signal' reads + the aria-announced degraded
// notice make the SR surface load-bearing (the notice must not be conveyed by
// colour/placement alone).

import { describe, it, expect, afterEach } from "vitest";
import { render } from "@testing-library/react";
import { axe } from "jest-axe";
import { MemoryRouter } from "react-router-dom";
import type { Change } from "../../../shared/api-types";
import { ChangeCard } from "../components/ChangeCard";

function makeDegraded(overrides: Partial<Change> = {}): Change {
  return {
    changeId: "01KTMF",
    handle: "CH-01KTMF",
    slug: "",
    primitive: "fix",
    branch: "feat/x",
    worktreePath: "/w",
    intent: "",
    baseBranch: "dev",
    baseSha: null,
    createdAt: "2026-06-09T10:00:00Z",
    updatedAt: "2026-06-09T11:00:00Z",
    stage: "implement",
    liveness: { status: "unknown", reason: "malformed session record" },
    needsAttention: { flagged: false, reason: null },
    health: { state: "unknown", reason: "this field could not be read" },
    lastActivityAt: null,
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
      <ChangeCard change={makeDegraded()} />
    </MemoryRouter>,
  );
  expect(await axe(container)).toHaveNoViolations();
}

describe("degraded <ChangeCard> a11y audit (WP-011)", () => {
  it("has no axe violations in LIGHT theme", async () => {
    await expectNoAxe("light");
  });

  it("has no axe violations in DARK theme", async () => {
    await expectNoAxe("dark");
  });
});
