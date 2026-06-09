// WP-008 (Blue) — RowActionButton — the one settings-row affordance button.
//
// Product / Project / Repo rows each render the same small affordance buttons
// (Rename, Remove, Edit, Change folder, Attach a folder, + Add project) with
// the same token-driven className composition. That repeated shape is the
// 2+-consumer duplication the Blue step extracts (EP-03 / WPF-13): one base
// button, two visual variants (ghost / danger), so the rows compose affordances
// without re-spelling the class strings. No behaviour is added — this is a pure
// presentational primitive; the rows still own which affordances exist and what
// each does.

import type { ReactNode } from "react";
import styles from "./Settings.module.css";

type Variant = "ghost" | "danger" | "primary";

const VARIANT_CLASS: Record<Variant, string> = {
  // CSS-module classes are known-present at build (non-null assertion is the
  // codebase convention under noUncheckedIndexedAccess — cf. StageBadge.tsx).
  ghost: styles.btnGhost!,
  danger: styles.btnDanger!,
  primary: styles.btnPrimary!,
};

interface Props {
  children: ReactNode;
  /** ghost (default) for neutral actions, danger for destructive ones. */
  variant?: Variant;
  /** Small sizing — the in-row affordances (omit for the page-level CTAs). */
  small?: boolean;
  onClick?: () => void;
  /** An accessible name when the visible label is ambiguous (e.g. "Remove"). */
  ariaLabel?: string;
}

export function RowActionButton({
  children,
  variant = "ghost",
  small = true,
  onClick,
  ariaLabel,
}: Props) {
  const className = [
    styles.btn,
    VARIANT_CLASS[variant],
    small && styles.btnSmall,
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <button
      type="button"
      className={className}
      aria-label={ariaLabel}
      onClick={() => onClick?.()}
    >
      {children}
    </button>
  );
}
