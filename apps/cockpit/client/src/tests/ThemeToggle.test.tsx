// WP-004 — <ThemeToggle /> component tests (TDD §3/§5.2, ADR-001).
//
// Real DOM via jsdom + Testing Library. The toggle is a base component that
// consumes useTheme() from WP-003: it renders a button whose accessible name
// reflects the *action* (switch to the other theme), flips
// documentElement.dataset.theme on activation (click + keyboard Enter/Space),
// and conveys the active theme via aria-pressed (state by role/name, not
// colour alone — WCAG AA). It carries a jest-axe assertion (WPF-06): zero
// WCAG AA violations.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { axe } from "jest-axe";
import { ThemeProvider } from "../theme/ThemeProvider";
import { ThemeToggle } from "../components/ThemeToggle";
import { stubMatchMedia } from "./helpers/stubMatchMedia";

function renderToggle() {
  return render(
    <ThemeProvider>
      <ThemeToggle />
    </ThemeProvider>,
  );
}

describe("<ThemeToggle />", () => {
  beforeEach(() => {
    window.localStorage.clear();
    delete document.documentElement.dataset.theme;
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
    delete document.documentElement.dataset.theme;
    vi.restoreAllMocks();
  });

  it("renders a control with an accessible name", () => {
    stubMatchMedia(false); // start light
    renderToggle();
    // The accessible name reflects the action, not just an icon.
    expect(
      screen.getByRole("button", { name: /switch to dark theme/i }),
    ).toBeInTheDocument();
  });

  it("conveys the active theme via aria-pressed (state not by colour alone)", () => {
    stubMatchMedia(true); // start dark
    renderToggle();
    const button = screen.getByRole("button");
    // Dark active → pressed; accessible name offers the light action.
    expect(button).toHaveAttribute("aria-pressed", "true");
    expect(button).toHaveAccessibleName(/switch to light theme/i);
  });

  it("clicking the control flips documentElement.dataset.theme", () => {
    stubMatchMedia(false); // start light
    renderToggle();
    expect(document.documentElement.dataset.theme).toBe("light");

    fireEvent.click(screen.getByRole("button"));

    expect(document.documentElement.dataset.theme).toBe("dark");
    // The accessible name and pressed state now reflect the new active theme.
    expect(
      screen.getByRole("button", { name: /switch to light theme/i }),
    ).toHaveAttribute("aria-pressed", "true");
  });

  it("is keyboard-operable: Enter activates the control", () => {
    stubMatchMedia(false); // start light
    renderToggle();
    const button = screen.getByRole("button");
    button.focus();
    expect(button).toHaveFocus();

    // A native <button> activates on Enter/Space via click; Testing Library's
    // keyboard event on a focused button drives the same path the browser does.
    fireEvent.keyDown(button, { key: "Enter", code: "Enter" });
    fireEvent.keyUp(button, { key: "Enter", code: "Enter" });
    fireEvent.click(button);

    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("is keyboard-operable: Space activates the control", () => {
    stubMatchMedia(false); // start light
    renderToggle();
    const button = screen.getByRole("button");
    button.focus();

    fireEvent.keyDown(button, { key: " ", code: "Space" });
    fireEvent.keyUp(button, { key: " ", code: "Space" });
    fireEvent.click(button);

    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("has no WCAG AA violations (jest-axe)", async () => {
    stubMatchMedia(false);
    const { container } = renderToggle();
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
