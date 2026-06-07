// WP-003 (fix-forward) — <ChangeCard> intent-clamp regression pin.
//
// A real-app screenshot revealed a render defect the green unit suite
// missed: a card with a very long intent dumped its ENTIRE description as a
// wall of text, blowing the card out of its calm fixed shape. The SIGNED
// visual contract (sulis-app.html, board panel) shows the card as
// handle + a single-line-ish intent + a footer — a calm fixed height
// regardless of intent length.
//
// jsdom does not run layout, so a computed-height assertion is not
// meaningful here; the REAL gate is the calling session re-driving the app
// and screenshotting. These tests are the necessary-not-sufficient pin:
//   1. the rendered long-intent card keeps the full text reachable
//      (aria-label + title) — accessibility is not sacrificed to the clamp;
//   2. the intent element carries the clamping module class;
//   3. the ChangeCard stylesheet actually clamps `.intent` (line-clamp +
//      -webkit-box) so the calm shape cannot silently regress.

import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import type { Change } from "../../../shared/api-types";
import { ChangeCard } from "../components/ChangeCard";

const LONG_INTENT =
  "Deploy the founder web app to production behind the cockpit so the " +
  "whole team can see every in-flight change at a glance, wire the staging " +
  "smoke tests, and document the rollback runbook end to end before the " +
  "launch window closes on Friday afternoon.";

function makeChange(overrides: Partial<Change> = {}): Change {
  return {
    changeId: "01LONG",
    handle: "CH-01LONG",
    slug: "deploy-founder-web-app",
    primitive: "feat",
    branch: "feat/deploy",
    worktreePath: "/tmp/worktree",
    intent: LONG_INTENT,
    baseBranch: "main",
    baseSha: "abc123",
    createdAt: "2026-05-26T11:00:00Z",
    updatedAt: "2026-05-26T11:55:00Z",
    stage: "implement",
    liveness: { status: "unknown", reason: "no session" },
    ...overrides,
  };
}

function renderCard(change: Change) {
  return render(
    <MemoryRouter>
      <ChangeCard change={change} />
    </MemoryRouter>,
  );
}

describe("<ChangeCard> intent clamp (fix-forward render defect)", () => {
  it("keeps a long intent's full text reachable (aria-label + title) despite the visual clamp", () => {
    const { getByText, getByRole } = renderCard(makeChange());
    // The text node still contains the FULL intent (the clamp is visual-only,
    // via CSS overflow — the DOM text and the accessible name are complete).
    const intent = getByText(LONG_INTENT);
    expect(intent).toBeInTheDocument();
    expect(intent).toHaveAttribute("title", LONG_INTENT);
    // The card link's accessible name carries the full intent too.
    expect(
      getByRole("link", { name: new RegExp(LONG_INTENT.slice(0, 40)) }),
    ).toBeInTheDocument();
  });

  it("applies the clamping module class to the intent element", () => {
    const { getByText } = renderCard(makeChange());
    const intent = getByText(LONG_INTENT);
    // CSS-module classes are hashed; the source class name survives as a
    // substring of the generated identifier.
    expect(intent.className).toMatch(/intent/);
  });

  it("clamps .intent in the stylesheet so the calm card shape cannot regress", () => {
    // vitest may run from the client dir or the cockpit workspace root;
    // resolve the stylesheet from whichever cwd is in effect.
    const candidates = [
      resolve(process.cwd(), "src/components/ChangeCard.module.css"),
      resolve(process.cwd(), "client/src/components/ChangeCard.module.css"),
    ];
    const cssPath = candidates.find((p) => existsSync(p));
    expect(cssPath, "ChangeCard.module.css must be locatable").toBeTruthy();
    const css = readFileSync(cssPath as string, "utf8");
    const intentBlock = css.slice(css.indexOf(".intent"));
    expect(intentBlock).toMatch(/-webkit-line-clamp:\s*2/);
    expect(intentBlock).toMatch(/line-clamp:\s*2/);
    expect(intentBlock).toMatch(/display:\s*-webkit-box/);
    expect(intentBlock).toMatch(/overflow:\s*hidden/);
  });
});
