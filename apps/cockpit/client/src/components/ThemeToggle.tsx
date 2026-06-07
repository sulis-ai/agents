// WP-004 — <ThemeToggle />: the light/dark control in the Shell top bar.
//
// A base component (stateless beyond useTheme() from WP-003): token-consuming,
// accessible, keyboard-operable. It matches the signed-off mockup's toggle
// (mockup/dark-theme.html — a pill button, top-right, icon + label).
//
// Accessibility (WPF-06 / WCAG AA):
//   - It is a real <button>, so it is keyboard-operable (Enter/Space) and
//     focusable by default; the focus ring is provided in the CSS module
//     (never outline:none).
//   - Its accessible name reflects the *action* ("Switch to dark/light
//     theme") via aria-label, so the state is conveyed by name/role — not by
//     colour or icon alone.
//   - aria-pressed mirrors the active theme (pressed === dark) so assistive
//     tech reports the current state as well as the action.
//   - The emoji icon + visible label are decorative (aria-hidden); the
//     aria-label is the single source of the accessible name.

import { useTheme } from "../theme/ThemeProvider";
import styles from "./ThemeToggle.module.css";

export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const isDark = theme === "dark";

  // The accessible name names the action the control performs, not the current
  // state — the convention for a toggle button announced via aria-pressed.
  const actionLabel = isDark ? "Switch to light theme" : "Switch to dark theme";

  return (
    <button
      type="button"
      className={styles.toggle}
      onClick={toggle}
      aria-label={actionLabel}
      aria-pressed={isDark}
    >
      <span className={styles.icon} aria-hidden="true">
        {isDark ? "🌙" : "☀️"}
      </span>
      <span aria-hidden="true">{isDark ? "Dark" : "Light"}</span>
    </button>
  );
}
