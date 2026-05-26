// WP-015 — diff-toggle copy.
//
// The toolbar's diff-toggle label lives here (not inline in
// <FileToolbar>) so a future surface change — or an i18n pass — has a
// single place to edit the strings rather than hunting through JSX.
// Per the WP-015 Blue requirement.

export const DIFF_TOGGLE_LABELS = {
  /** Shown when the diff is OFF — clicking turns it on. */
  showDiff: "Show diff",
  /** Shown when the diff is ON — clicking returns to the file view. */
  showCurrent: "Show current",
} as const;
