// WP-004 — <StageColumn> — one lifecycle-stage column rendered as a
// FULL-HEIGHT LANE (REORGANISE-Refactor).
//
// Matches the production-approved visual contract
// (.design/cockpit-board-refresh/MOCKUP.html — .lane / .laneHead /
// .laneList / .laneFoot / .laneEmpty): the lane fills the board row top to
// bottom, its header is sticky (stays put while the cards scroll), and its
// card list is the internal-scroll container — so each lane scrolls on its
// own and the board no longer scrolls as one page. An empty lane keeps its
// full height, its header, its count (0), and shows a quiet "Nothing here
// yet" note inside the lane (S-12 / AF-2) — it is never collapsed or hidden.
//
// The Recon lane (and only Recon) carries a quiet "Start here" foot
// affordance that routes to /start, because changes start at Recon. It is a
// keyboard-reachable <Link> with a visible focus ring (never mouse-only,
// never outline:none — WPF-06).
//
// The lane stays a labelled region (aria-label="Recon — N changes"); the dot
// is the board's only colour (ADR-005), is decorative reinforcement
// (aria-hidden), and the stage is also carried by the name + position so
// colour is never the sole cue (WCAG 1.4.1). Card internals are out of scope
// here (WP-005 owns the card redesign); this WP is layout only. Reuses
// ChangeCard (EP-03 — restyle/compose, not rebuild); the stage colour comes
// from the shared --stage-* tokens (tokens.css), the same scale the
// StageBadge palette draws on — no parallel palette.
//
// WP-013 — Lane scale (REINFORCE-Harden + EXPAND-Create). A single lane must
// absorb up to 200 cards (NFR-PERF-2 / S-15) via its internal scroll at 60fps
// with no long-frame > 50 ms. The budget was MEASURED breached on a plain
// scroll of 200 mounted cards (a ~6 s main-thread long-task in the Playwright
// trace: every card is a react-router <Link> with several child probes, and
// 200 live at once overwhelm layout/paint). Per the WP's Q-6 decision we
// therefore virtualise the lane's card list — but ONLY because the budget
// demanded it (boring-code: no speculative machinery). Virtualisation sits
// BEHIND the existing lane API: the props, the sticky header, the truthful
// count (changes.length — NEVER a windowed subset), the empty-lane note and
// the Recon foot are all unchanged, and ChangeCard is untouched (EP-03).
// @tanstack/react-virtual is the established convention — same maintainer
// family as the @tanstack/react-query already in the tree, headless, no new
// vendor (CP-01). The `.laneList` div stays the internal-scroll container with
// its data-testid; the virtualiser windows the rows inside it.

import { useRef } from "react";
import { Link } from "react-router-dom";
import {
  useVirtualizer,
  type VirtualizerOptions,
} from "@tanstack/react-virtual";
import type { Change } from "../../../shared/api-types";
import type { BoardStage } from "../lib/groupChangesByStage";
import { ChangeCard } from "./ChangeCard";
import styles from "./StageColumn.module.css";

/** Title-cased display name for each board stage. */
const STAGE_NAME: Record<BoardStage, string> = {
  recon: "Recon",
  specify: "Specify",
  design: "Design",
  implement: "Implement",
  review: "Review",
  ship: "Ship",
};

/** Fixed row height (px) for a card slot: a card's calm resting height (top
 *  line + step dots + 2-line clamped intent + meta + exactly one foot verdict)
 *  plus the 12px inter-card gap. The card's shape is deliberately fixed (WP-005
 *  — intent clamps to 2 lines, exactly one foot verdict), so a constant row
 *  height is correct AND keeps the virtualiser's total size deterministic
 *  (count × this) — no per-card measurement pass, which is both simpler
 *  (boring-code) and free of layout dependence (works in a browser, in jsdom
 *  unit tests, and under SSR). */
const CARD_ROW_PX = 180;

/** Extra rows rendered above/below the viewport so a fast scroll never reveals
 *  a blank gap before the next window mounts. */
const OVERSCAN = 6;

/** Fallback lane-viewport height (px) used ONLY when the environment reports a
 *  zero-height scroll element — i.e. jsdom unit tests and SSR, which compute no
 *  layout. In a real browser the element's measured height is non-zero and is
 *  used as-is, so this never affects production rendering; it only guarantees
 *  the virtualiser computes a real window (and mounts rows) where there is no
 *  layout engine. Tall enough to cover a typical lane so the first window is
 *  complete. */
const NO_LAYOUT_FALLBACK_HEIGHT = 720;

/**
 * Measure the scroll element's rect, falling back to a fixed lane viewport when
 * the environment reports zero height (jsdom / SSR — no layout). This keeps the
 * virtualiser deterministic in tests while using the genuine measured rect in a
 * browser. Mirrors @tanstack/react-virtual's default rect observer (a
 * ResizeObserver when available, else a one-shot read) and only substitutes the
 * height when it would otherwise be 0.
 */
const observeLaneRect: VirtualizerOptions<
  HTMLDivElement,
  Element
>["observeElementRect"] = (instance, cb) => {
  const el = instance.scrollElement;
  if (!el) return;

  const report = () => {
    const rect = el.getBoundingClientRect();
    cb({
      width: rect.width,
      height: rect.height > 0 ? rect.height : NO_LAYOUT_FALLBACK_HEIGHT,
    });
  };

  report();

  if (typeof ResizeObserver === "undefined") return;
  const observer = new ResizeObserver(report);
  observer.observe(el);
  return () => observer.disconnect();
};

export interface StageColumnProps {
  stage: BoardStage;
  changes: Change[];
}

/**
 * The lane's virtualised card list (WP-013). Mounts only the cards in (and
 * just around) the viewport while sizing a spacer to the FULL count, so a
 * 200-card lane scrolls smoothly with a small, bounded DOM. The scroll
 * container is the `.laneList` div the lane already owned; the virtualiser
 * reads it via `scrollRef`. Cards are unchanged (EP-03).
 */
function LaneCardList({
  stage,
  changes,
}: {
  stage: BoardStage;
  changes: Change[];
}) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const virtualizer = useVirtualizer({
    count: changes.length,
    getScrollElement: () => scrollRef.current,
    // Fixed row height — the card's shape is constant, so the total scroll
    // size is exactly count × CARD_ROW_PX with no per-card measurement pass.
    estimateSize: () => CARD_ROW_PX,
    overscan: OVERSCAN,
    // Identity by changeId so a re-poll that reorders cards keeps stable keys.
    // (index is always in range — the virtualiser only asks for 0..count-1 —
    // but the codebase's noUncheckedIndexedAccess makes the lookup optional, so
    // fall back to the index for the key if it ever isn't present.)
    getItemKey: (index) => changes[index]?.changeId ?? index,
    // Measure the lane viewport with a browser-correct rect observer that
    // falls back to a fixed height only where there is no layout (jsdom / SSR),
    // so the virtualiser always computes a real window and mounts rows.
    observeElementRect: observeLaneRect,
  });

  const items = virtualizer.getVirtualItems();

  return (
    <div
      ref={scrollRef}
      className={styles.laneList}
      data-testid={`stage-column-${stage}`}
    >
      {/* Full-height spacer: its height is the total of every card, so the
       * lane's internal scroll covers all N changes (the header count's truth)
       * even though only the windowed rows are in the DOM. */}
      <div
        className={styles.laneVirtualSpacer}
        style={{ height: virtualizer.getTotalSize() }}
      >
        {items.map((item) => {
          // The virtualiser only windows real indices (0..count-1); the guard
          // satisfies noUncheckedIndexedAccess without a non-null assertion.
          const change = changes[item.index];
          if (!change) return null;
          return (
            <div
              key={item.key}
              data-index={item.index}
              className={styles.laneVirtualRow}
              style={{
                height: `${item.size}px`,
                transform: `translateY(${item.start}px)`,
              }}
            >
              <ChangeCard change={change} />
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function StageColumn({ stage, changes }: StageColumnProps) {
  const name = STAGE_NAME[stage];
  return (
    <section
      className={`${styles.lane} ${styles[stage]}`}
      data-testid="stage-column"
      data-stage={stage}
      aria-label={`${name} — ${changes.length} ${
        changes.length === 1 ? "change" : "changes"
      }`}
    >
      <header className={styles.laneHead}>
        <span className={styles.sdot} aria-hidden="true" />
        <span className={styles.laneName}>{name}</span>
        <span className={styles.laneCount}>{changes.length}</span>
      </header>

      {changes.length === 0 ? (
        <div className={styles.laneList} data-testid={`stage-column-${stage}`}>
          <p className={styles.laneEmpty}>
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.6"
              aria-hidden="true"
            >
              <rect x="3" y="4" width="18" height="16" rx="2" />
              <path d="M3 9h18" strokeLinecap="round" />
            </svg>
            Nothing here yet
          </p>
        </div>
      ) : (
        <LaneCardList stage={stage} changes={changes} />
      )}

      {/* Pinned bottom action — RECON ONLY, because changes start at Recon.
       * A quiet outline secondary so it never competes with the top-bar
       * primary; a keyboard-reachable Link to /start with a visible focus
       * ring (WPF-06). The other five lanes have no foot. */}
      {stage === "recon" && (
        <div className={styles.laneFoot}>
          <Link to="/start" className={styles.startHere}>
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              aria-hidden="true"
            >
              <path d="M12 5v14M5 12h14" strokeLinecap="round" />
            </svg>
            Start here
          </Link>
        </div>
      )}
    </section>
  );
}
