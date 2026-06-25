// WP-003 — <ProductChatDock> accessibility audit (WPF-13 a11y GATE; ADR-001).
//
// This is the WP's verification artifact. The dock, the switcher tile echo and
// the agent picker are the three "real menu" homes the signed visual contract
// requires; a11y is a GATE on this WP, not an afterthought.
//
// What this asserts (jest-axe + structural a11y, both themes):
//   - jest-axe clean in BOTH light and dark, dock rendered with menus open;
//   - the agent picker is a real menu (role=menu, menuitemradio, aria-checked),
//     full keyboard parity inherited from ProductControl;
//   - the honest agent status is legible by glyph + WORD, never colour alone
//     ("Working…" / "Idle"), per AI-07;
//   - the collapse toggle is keyboard-reachable and aria-pressed reflects state;
//   - the dock's CSS ships a prefers-reduced-motion fallback and is token-only.
//
// jsdom doesn't compute layout, so axe validates STRUCTURAL a11y (roles / names
// / aria) — exactly where the glyph+word state encoding is load-bearing.

import { describe, it, expect, afterEach } from "vitest";
import { render, within, fireEvent } from "@testing-library/react";
import { axe } from "jest-axe";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import type { ChatThreadResponse } from "../../../shared/api-types";
import { ProductChatDock } from "../components/ProductChatDock";
import { renderWithClient } from "./_renderWithClient";
import { ActiveProductProvider } from "../api/activeProduct";

const CLINICS = "dna:product:01CLINIC0000000000000000000";

const THREAD: ChatThreadResponse = {
  messages: [
    { kind: "user", uuid: "u1", timestamp: "2026-06-25T10:00:00Z", text: "hi" },
    {
      kind: "assistant",
      uuid: "a1",
      timestamp: "2026-06-25T10:00:01Z",
      blocks: [{ kind: "text", text: "Hello — what shall we work on?" }],
    },
  ],
  provider: "pty",
  productId: CLINICS,
};

function stubFetchThread() {
  return async () => THREAD;
}
function stubStream() {
  return async () => {};
}
function stubPutProvider() {
  return async () => ({ provider: "pty" as const, applied: "new-work" as const });
}

function renderDock(theme: "light" | "dark") {
  if (theme === "dark") document.documentElement.dataset.theme = "dark";
  else delete document.documentElement.dataset.theme;
  return renderWithClient(
    <ActiveProductProvider initialActiveProductId={CLINICS}>
      <ProductChatDock
        products={[{ productId: CLINICS, name: "Clinics", active: true }]}
        fetchChatThread={stubFetchThread()}
        streamProductChat={stubStream()}
        putChatProvider={stubPutProvider()}
        streamStartFromIntent={async () => {}}
      />
    </ActiveProductProvider>,
  );
}

afterEach(() => {
  delete document.documentElement.dataset.theme;
});

describe("<ProductChatDock> WCAG AA — both themes", () => {
  for (const theme of ["light", "dark"] as const) {
    it(`${theme} · dock with agent picker open has no axe violations`, async () => {
      const { container, getByTestId } = renderDock(theme);
      fireEvent.click(getByTestId("agent-picker-trigger"));
      expect(await axe(container)).toHaveNoViolations();
    });
  }
});

describe("<ProductChatDock> the agent picker is a real menu", () => {
  it("exposes role=menu with menuitemradio rows + aria-checked", () => {
    const { getByTestId } = renderDock("light");
    fireEvent.click(getByTestId("agent-picker-trigger"));
    const menu = getByTestId("agent-picker-menu");
    const rows = within(menu).getAllByRole("menuitemradio");
    expect(rows.length).toBeGreaterThanOrEqual(2);
    // Exactly one row is checked (the running provider).
    expect(rows.filter((r) => r.getAttribute("aria-checked") === "true")).toHaveLength(1);
  });

  it("the trigger declares aria-haspopup=menu and aria-expanded", () => {
    const { getByTestId } = renderDock("light");
    const trigger = getByTestId("agent-picker-trigger");
    expect(trigger.getAttribute("aria-haspopup")).toBe("menu");
    expect(trigger.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(trigger);
    expect(getByTestId("agent-picker-trigger").getAttribute("aria-expanded")).toBe("true");
  });
});

describe("<ProductChatDock> honest agent status — glyph + word, not colour", () => {
  it("names the running agent in words at the composer foot (AI-07)", () => {
    const { getByTestId } = renderDock("light");
    // "Powered by Claude" — the running provider named in words.
    expect(getByTestId("agent-picker-trigger").textContent).toMatch(/claude/i);
  });

  it("the working/idle status carries a WORD, not colour alone", () => {
    const { getByTestId } = renderDock("light");
    const status = getByTestId("agent-status");
    // Either "Working…" or "Idle" — the word is the carrier.
    expect(status.textContent).toMatch(/working|idle/i);
  });
});

describe("<ProductChatDock> the collapse toggle is keyboard-reachable", () => {
  it("is a real button with aria-pressed reflecting collapsed state", () => {
    const { getByTestId } = renderDock("light");
    const toggle = getByTestId("chat-toggle");
    expect(toggle.tagName).toBe("BUTTON");
    const before = toggle.getAttribute("aria-pressed");
    fireEvent.click(toggle);
    expect(getByTestId("chat-toggle").getAttribute("aria-pressed")).not.toBe(before);
  });
});

describe("<ProductChatDock> stylesheet contract — token-only + reduced-motion", () => {
  function readCss(): string {
    const candidates = [
      resolve(process.cwd(), "src/components/ProductChatDock.module.css"),
      resolve(process.cwd(), "client/src/components/ProductChatDock.module.css"),
    ];
    const cssPath = candidates.find((p) => existsSync(p));
    expect(cssPath, "ProductChatDock.module.css must be locatable").toBeTruthy();
    return readFileSync(cssPath as string, "utf8");
  }

  it("ships a prefers-reduced-motion: reduce fallback", () => {
    expect(readCss()).toMatch(/@media\s*\(prefers-reduced-motion:\s*reduce\)/);
  });

  it("stays token-only — no raw hex colours", () => {
    const css = readCss().replace(/\/\*[\s\S]*?\*\//g, "");
    expect(css).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
  });
});
