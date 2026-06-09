// WP-009 — <ChangeCard> INTERACTION / FOCUS (RED) — S-33.
//
// CS-2 / FR-51 / BR-22 / BR-23 / NFR-A11Y-5. The card-as-<Link> is natively
// focusable and Enter-activates (the ARIA link pattern). This WP PINS the
// behaviour:
//   - the card is in tab order and shows a VISIBLE :focus-visible ring (never
//     outline:none — WPF-06);
//   - Enter on the focused card navigates to /c/:changeId;
//   - the inner "Open terminal" control (when present) is a SEPARATE tab stop
//     and does NOT navigate the card link (stopPropagation);
//   - NO signal depends on hover — everything reachable on hover is reachable
//     on focus (the focus ring + the selected marker are not hover-only).
//
// Clicks/keys use `fireEvent` (the cockpit client-test convention — the
// workspace doesn't vendor user-event). Navigation is asserted with a real
// <Routes> + a location probe.

import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, it, expect, vi } from "vitest";
import { render, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route, useLocation } from "react-router-dom";
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

/** A probe that surfaces the current pathname so a navigation can be asserted. */
function LocationProbe() {
  const loc = useLocation();
  return <div data-testid="location">{loc.pathname}</div>;
}

function renderRouted(change: Change, onOpenTerminal?: (id: string) => void) {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <Routes>
        <Route
          path="/"
          element={<ChangeCard change={change} onOpenTerminal={onOpenTerminal} />}
        />
        {/* The change route renders the probe so we can read the landed path. */}
        <Route path="/c/:changeId" element={<LocationProbe />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("WP-009 — <ChangeCard> interaction / focus (S-33)", () => {
  it("the card is a focusable link in tab order (a real <a href>, no negative tabindex)", () => {
    const { getByRole } = render(
      <MemoryRouter>
        <ChangeCard change={makeChange()} />
      </MemoryRouter>,
    );
    const link = getByRole("link");
    // A react-router <Link> renders an <a href>, which is natively focusable
    // and in tab order. It must NOT be removed from the tab order.
    expect(link.tagName).toBe("A");
    expect(link).toHaveAttribute("href", "/c/01AAA");
    expect(link.getAttribute("tabindex")).not.toBe("-1");
    // It can actually receive focus.
    link.focus();
    expect(document.activeElement).toBe(link);
  });

  it("the stylesheet pins a visible :focus-visible ring on the card (never outline:none)", () => {
    const cssPath = resolve(__dirname, "../components/ChangeCard.module.css");
    expect(existsSync(cssPath)).toBe(true);
    const css = readFileSync(cssPath, "utf8");
    // A .card:focus-visible rule exists…
    expect(css).toMatch(/\.card:focus-visible\s*\{[^}]*\}/s);
    const focusBlock = css.match(/\.card:focus-visible\s*\{[^}]*\}/s)?.[0] ?? "";
    // …with a real outline/ring (NOT `outline: none`), token-coloured.
    expect(focusBlock).toMatch(/outline|box-shadow/);
    expect(focusBlock).not.toMatch(/outline:\s*none/);
    expect(focusBlock).toMatch(/var\(--ring\)/);
  });

  it("Enter on the focused card navigates to /c/:changeId (native ARIA link activation)", () => {
    const { getByRole, getByTestId } = renderRouted(makeChange());
    const link = getByRole("link");
    link.focus();
    // jsdom doesn't translate Enter-on-<a> into a click the way a browser
    // does, so model the native link activation explicitly: Enter activates
    // the link. We assert the link is a real href target (the browser's
    // activation contract) AND that clicking it — the same activation path —
    // lands on the change route.
    fireEvent.keyDown(link, { key: "Enter", code: "Enter" });
    fireEvent.click(link);
    expect(getByTestId("location").textContent).toBe("/c/01AAA");
  });

  it("the inner 'Open terminal' control is a SEPARATE tab stop and does NOT navigate the card", () => {
    const onOpenTerminal = vi.fn();
    const { getByRole, queryByTestId } = renderRouted(makeChange(), onOpenTerminal);
    const button = getByRole("button", { name: /open terminal/i });
    // It's its own focusable control, distinct from the card link.
    const link = getByRole("link");
    expect(button).not.toBe(link);
    button.focus();
    expect(document.activeElement).toBe(button);
    // Activating it fires its callback and STOPS the card navigation
    // (stopPropagation + preventDefault) — we stay on "/".
    fireEvent.click(button);
    expect(onOpenTerminal).toHaveBeenCalledWith("01AAA");
    expect(queryByTestId("location")).toBeNull();
  });

  it("the card does NOT trap/swallow Space (ARIA link pattern — Space is not required to activate)", () => {
    const { getByRole, queryByTestId } = renderRouted(makeChange());
    const link = getByRole("link");
    link.focus();
    // Space on a link must not be hijacked into an activation, and must not be
    // prevented (a link is not a button). Pressing Space leaves us on "/".
    const ev = fireEvent.keyDown(link, { key: " ", code: "Space" });
    // fireEvent returns false if a handler called preventDefault. The card
    // must NOT preventDefault on Space.
    expect(ev).toBe(true);
    expect(queryByTestId("location")).toBeNull();
  });

  it("no signal depends on hover: the focus ring + selected marker are keyed off :focus-visible / data-selected, not :hover", () => {
    const cssPath = resolve(__dirname, "../components/ChangeCard.module.css");
    const css = readFileSync(cssPath, "utf8");
    // The focus ring is on :focus-visible (reachable by keyboard), not on :hover.
    expect(css).toMatch(/\.card:focus-visible/);
    // The selected marker is on the data-selected attribute, not on a :hover rule.
    const hoverBlocks = css.match(/\.card:hover\s*\{[^}]*\}/gs) ?? [];
    for (const block of hoverBlocks) {
      // A :hover rule must not be the ONLY place a load-bearing marker lives:
      // it must not set aria-driven structure like the selected box-shadow.
      // (Hover may tweak the border for feedback — that's fine — but the
      // selected/focus signals are not hover-gated.)
      expect(block).not.toMatch(/\[data-selected/);
    }
  });
});
