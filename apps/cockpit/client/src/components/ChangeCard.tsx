// WP-005 — <ChangeCard> — the redesigned change card (production-approved
// MOCKUP). One card per change on the board; click navigates to /c/:changeId.
//
// EVERY card has the SAME reading order, top to bottom (identical every card):
//   topLine : handle (left) · LivenessProbe = probe dot + bare time (right)
//   steps   : slim ·N/6 step dots (role="img" aria-label="Step N of 6")
//   intent  : clamped to 2 lines (the calm fixed shape)
//   slug    : the meta line (the time lives on the top line, not duplicated)
//   foot    : EXACTLY ONE verdict — WaitingOnYou (flagged) XOR ChangeHealthBadge
//             (not flagged). Never both (the founder's load-bearing rule, TDD §5
//             / BR-1), enforced by a single branch.
//
// Dropped from the old card: the StageBadge pill (the lane already says the
// stage), the top banner, the left colour stripe.
//
// A11y: rendered as a <Link> whose accessible name carries the FULL handle +
// intent ("Change CH-… : <intent>"). The intent is clamped visually only — the
// full text stays reachable via the aria-label + title.
//
// WP-009 — the SELECTED + INTERACTION states (CS-1 / CS-2, SRD §7c; FR-50/51,
// BR-20..23; S-32 / S-33). Both are ALTERNATE states that compose ADDITIVELY
// onto any content/degraded/shipped card — they never hide a verdict.
//   - SELECTED (route-derived): the card whose change is the open route
//     (`/c/:changeId`) marks itself selected via the `selected` prop. The
//     parent (Board) reads the active change the SAME way the shell does
//     (`useMatch("/c/:changeId")` → `activeChangeId`) and threads it
//     Board → StageColumn → card; the card passes nothing about selection to
//     the feed (route-derived, never stored — survives a re-poll). The marker
//     is NOT colour-alone: `aria-current="true"` + a persistent non-colour
//     inset left-edge bar + ring (greyscale-distinguishable). At most one card
//     is selected; on a non-change route none is.
//   - INTERACTION/FOCUS: the card-as-<Link> is natively focusable and
//     Enter-activates (ARIA link pattern); this WP pins the visible
//     `:focus-visible` ring (coexists with the selected marker) and a small
//     pressed (`:active`) feedback. No signal depends on hover. The inner
//     "Open terminal" control is a SEPARATE tab stop (stopPropagation) — its
//     own focusable button, distinct from the card link.
//
// WP-011 — the DEGRADED / PARTIAL composition (FR-54 / FR-55 / BR-26 / S-35).
// A malformed or partial record renders PER-FIELD: every readable field renders
// normally; every unreadable field falls to its EXISTING unknown read (health →
// "Not assessed yet" FR-31; liveness → the distinct unknown "?" probe FR-41;
// recency → "—" FR-42; missing slug/intent → an honest FIXED placeholder). The
// card STILL renders and STILL links (so the founder can go investigate), and a
// quiet, FIXED-STRING, aria-announced "Some details couldn't be read" notice
// names the partial state in words — reinforcement of the per-field reads
// (BR-3), never echoing the malformed content (NFR-SEC-03 / FR-32). One bad
// record degrades INDEPENDENTLY: it never drops a sibling or breaks the lane
// (BR-26). The unknown reads REUSE the WP-005 components — no second unknown
// implementation (EP-03).
//
// WP-012 — the SHIPPED / TERMINAL composition (FR-56 / BR-27 / BR-28 / S-36).
// A change in the terminal stage (`stage === "shipped"`, the SAME predicate the
// Sidebar split + StageBadge use — BR-27, reused not reinvented) reads as
// ARCHIVED, not active. The card is MUTED; the LivenessProbe is REPLACED by a
// static "Shipped" marker (no working/live/idle, no pulse); BOTH live feet are
// suppressed (BR-28 MUST — neither "Waiting on you" nor the change-health badge
// renders); and recency reads "shipped Nd ago" (the Q-7 one-constant archival
// wording from formatShippedRecency), NOT a live-activity age. Shipped wins the
// foot/probe treatment over the degraded reads (SRD §7c precedence), but any
// unreadable IDENTITY field (slug/intent) still falls to its WP-011 unknown
// read + the degraded notice — the per-field honesty is orthogonal to the
// terminal treatment.

// WP-008 — assign-from-card. The board card carries the product vocabulary in
// context (Concern C2, ADR-002):
//   - UNASSIGNED: an always-in-DOM, keyboard-reachable "＋ Product" affordance
//     (accessible name "Add this change to a product", ≥44px target). Hover
//     only EMPHASISES it — it never controls presence (keyboard/touch parity).
//     Activating opens the shared <ProductControl mode="assign" compact>
//     popover so assignment happens WITHOUT opening the change.
//   - ASSIGNED: a quiet product monogram chip in the foot-meta, and the product
//     name rides the card's accessible name.
//   Assign reuses useAssignChangeProduct VERBATIM; the placement wires the hook
//   at the edge — ProductControl never touches the network (ADR-002). The
//   affordance is a <button> and the card is a <Link> (<a>); interactive
//   content cannot nest in an anchor, so the affordance renders OUTSIDE the
//   <Link> (a card-shell wrapper holds the Link + the affordance as siblings).
//   The assigned chip is a non-interactive <span>, so it sits inside the Link's
//   foot-meta legitimately.

import { Link } from "react-router-dom";
import type { Change, Product } from "../../../shared/api-types";
import { stageStepNumber, STAGE_COUNT } from "./StageBadge";
import { LivenessProbe } from "./LivenessProbe";
import { ChangeHealthBadge } from "./ChangeHealthBadge";
import { WaitingOnYou } from "./WaitingOnYou";
import { ProductControl, type ProductRow } from "./ProductControl";
import { monogram } from "./ProductSwitcher";
import { useAssignChangeProduct } from "../api/assignChangeProduct";
import { formatShippedRecency } from "../utils/relativeTime";
import styles from "./ChangeCard.module.css";

export interface ChangeCardProps {
  change: Change;
  /** WP-009 — the card is SELECTED when its change is the one open in the
   *  active route (`/c/:changeId`). The parent derives this the SAME way the
   *  shell does — `useMatch("/c/:changeId")` → `activeChangeId` — and passes
   *  `change.changeId === activeChangeId` (CS-1 / FR-50 / BR-20 / BR-21).
   *  Selection is ROUTE-DERIVED, never stored on the feed or the card, so it
   *  survives a feed re-poll. The marker is additive — it never hides health,
   *  waiting, the probe, recency, or a degraded notice (SRD §7c precedence).
   *  Defaults to false → existing usages render unchanged. */
  selected?: boolean;
  /** WP-009 — "open this change's terminal" action. When provided, the card
   *  renders an "Open terminal" button that opens the change's in-cockpit
   *  Terminal tab via this callback. Omitted → no terminal action rendered
   *  (existing dashboard usages unchanged). */
  onOpenTerminal?: (changeId: string) => void;
  /** "now" override for deterministic tests; defaults to the real clock.
   *  Forwarded to the live probe (the working/live recency split) and the
   *  shipped-recency ("shipped Nd ago") read so both bucket against one clock. */
  now?: Date;
  /** WP-008 — the founder's products, INJECTED at the edge (ADR-002 — the
   *  placement supplies data; the card never fetches). Drives the assigned
   *  monogram chip (resolves `forProduct` → a human name) and the unassigned
   *  "＋ Product" affordance. Omitted/undefined → no product placement renders
   *  (existing dashboard usages + the provider-less unit tests are unchanged);
   *  the board threads the one already-fetched products list to every card, so
   *  there is ONE products query, not one per card. */
  products?: Product[];
}

/** The slim "·N/6" step dots — the one non-redundant part of the old stage
 *  pill, kept as a tiny progress indicator with an SR text label. A terminal
 *  stage (no step number) renders the rail with no current dot. */
function StepDots({ step }: { step: number | null }) {
  const label =
    step !== null ? `Step ${step} of ${STAGE_COUNT}` : "Past the workflow";
  return (
    <div className={styles.steps} role="img" aria-label={label}>
      {Array.from({ length: STAGE_COUNT }, (_, i) => {
        const n = i + 1;
        const cls =
          step !== null && n === step
            ? `${styles.step} ${styles.stepCur}`
            : step !== null && n < step
              ? `${styles.step} ${styles.stepOn}`
              : styles.step;
        return <span key={n} className={cls} />;
      })}
    </div>
  );
}

/**
 * WP-011 — the FIXED degraded vocabulary (FR-55 / FR-32 / MUC-3). Every string
 * here is a constant from the enumerable set — none is interpolated from the
 * record's content (NFR-SEC-03). The notice is the single source the card
 * surfaces; the per-field unknown reads carry the primary signal (BR-3).
 */
export const DEGRADED_NOTICE = "Some details couldn't be read";
/** Honest placeholders for content fields that came back unreadable. Fixed
 *  strings — never the (possibly malformed) row content itself. */
const INTENT_UNREADABLE = "Details couldn't be read";
const SLUG_UNREADABLE = "slug unavailable";

/**
 * WP-011 — is this a malformed / partial record (FR-54)? Two honest signals:
 *
 *  1. A readable CONTENT field is missing — an empty/blank slug or intent. A
 *     well-formed record always carries both; their absence means the row could
 *     not be fully read.
 *  2. The COMBINED unknown signal — liveness AND health both came back
 *     `unknown`. A SINGLE unknown read is the honest fresh-change case ("too
 *     early to tell") and is NOT degraded; both unknown together is the
 *     malformed-record shape (the producer's never-throw output, WP-002).
 *
 * Pure, no I/O — a render-time predicate over the wire `Change`. Exported so the
 * card test and any future consumer share ONE definition (CF-02 / DRY).
 */
export function isDegraded(change: Change): boolean {
  const missingContent =
    change.slug.trim() === "" || change.intent.trim() === "";
  const bothUnknown =
    change.liveness.status === "unknown" && change.health.state === "unknown";
  return missingContent || bothUnknown;
}

/**
 * WP-012 — the TERMINAL predicate (BR-27). A change in the terminal stage reads
 * as ARCHIVED, not active. This is the SAME `stage === "shipped"` test the
 * Sidebar split + StageBadge already use — reused, never a second detector.
 * Exported so the card test and any future consumer share ONE definition.
 */
export function isShipped(change: Change): boolean {
  return change.stage === "shipped";
}

/**
 * WP-012 — the static "Shipped" marker that REPLACES the LivenessProbe on a
 * terminal card (FR-56 / BR-28). It carries NO probe dot, NO motion, NO
 * working/live/idle state — a shipped change has no live session to read. The
 * word "Shipped" carries the meaning in text (never colour/placement alone), so
 * a screen reader hears "archived", not silence.
 */
function ShippedMarker() {
  return (
    <span
      className={styles.shippedMarker}
      data-testid="shipped-marker"
      data-shipped-marker
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={1.9}
        aria-hidden="true"
      >
        {/* an archive box — the calm "filed away" glyph */}
        <path
          d="M3 7h18M5 7v12a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V7M3 7l2-3h14l2 3M10 12h4"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      Shipped
    </span>
  );
}

/** Plain-English why-text for the waiting chip, from the fixed reason set.
 *  Never echoes any reply body (NFR-SEC-03) — these are enumerable shapes. */
function attentionWhy(reason: Change["needsAttention"]["reason"]): string {
  switch (reason) {
    case "blocked":
      return "blocked — needs a decision";
    case "waiting-on-decision":
      return "picking an approach";
    case "stopped-mid-reply":
      return "stopped mid-reply";
    case null:
    default:
      return "needs you";
  }
}

/**
 * WP-008 — the assign-from-card affordance. Rendered OUTSIDE the card's <Link>
 * (interactive content can't nest in an <a>) when the change is unassigned. A
 * thin placement of the shared <ProductControl> (ADR-002): it supplies the
 * product rows + wires `useAssignChangeProduct` at the edge; the menu/keyboard/
 * a11y model lives in the primitive. The affordance is ALWAYS in the DOM and
 * keyboard-reachable (a native <button> trigger) — hover only emphasises it.
 *
 * The products list is INJECTED (the card never fetches — ADR-002); the assign
 * mutation hook is the one piece of network the placement owns, so this is the
 * only part that needs a QueryClient (mounted only on the board, behind the
 * provider). Hidden when there are no products yet — the founder creates one
 * first via the switcher's "Set up a new product".
 */
function CardProductAffordance({
  changeId,
  products,
}: {
  changeId: string;
  products: Product[];
}) {
  const assign = useAssignChangeProduct(changeId);

  if (products.length === 0) return null;

  const rows: ProductRow[] = products.map((p) => ({
    productId: p.productId,
    name: p.name,
    glyph: "monogram",
  }));

  const saveState: "idle" | "saving" | "saved" = assign.isPending
    ? "saving"
    : assign.isSuccess
      ? "saved"
      : "idle";

  return (
    <div className={styles.cardProduct} data-testid="card-product-affordance">
      <ProductControl
        mode="assign"
        compact
        rows={rows}
        selectedId={null}
        triggerLabel="Add this change to a product"
        saveState={saveState}
        onSelect={(id) => {
          // Commit-on-select: assign in place via the shared hook. Clearing
          // (id === null) is not reachable from an unassigned card's menu.
          if (id) assign.mutate(id);
        }}
      />
    </div>
  );
}

/** Per-field degraded fallbacks (FR-54): readable fields render verbatim;
 *  unreadable content fields fall to a FIXED placeholder — never blank, never
 *  the (possibly malformed) row text. The aria name stays honest even when the
 *  intent is unreadable. Pure; extracted so the card body holds no field-branch. */
function degradedFields(change: Change): {
  intentText: string;
  slugText: string;
  ariaIntent: string;
} {
  const intentBlank = change.intent.trim() === "";
  return {
    intentText: intentBlank ? INTENT_UNREADABLE : change.intent,
    slugText: change.slug.trim() === "" ? SLUG_UNREADABLE : change.slug,
    ariaIntent: intentBlank ? "some details couldn't be read" : change.intent,
  };
}

/** WP-008 — resolve the assigned product (if any). The board feed carries only
 *  `forProduct` (an id); the human name comes from the INJECTED products list
 *  (ADR-002 — the card never fetches). Pure; null when unassigned or no list. */
function resolveAssignedProduct(
  change: Change,
  products?: Product[],
): Product | null {
  if (typeof change.forProduct !== "string" || !products) return null;
  return products.find((p) => p.productId === change.forProduct) ?? null;
}

/** The card's CSS class string — `card` plus the additive selected/degraded/
 *  shipped state classes. Extracted so the parent holds no className branch. */
function cardClassName(
  selected: boolean,
  degraded: boolean,
  shipped: boolean,
): string {
  return [
    styles.card,
    selected ? styles.selected : "",
    degraded ? styles.degraded : "",
    shipped ? styles.shipped : "",
  ]
    .filter(Boolean)
    .join(" ");
}

/** A boolean → the `"true"`-or-omitted attribute value pattern the card uses
 *  for its data-/aria- state flags (present only when on, never colour-alone). */
const attrFlag = (on: boolean): "true" | undefined => (on ? "true" : undefined);

/** WP-012 — top-line right element: the static "Shipped" marker on a terminal
 *  card (BR-28 — no live signal), else the live probe. */
function CardProbe({
  shipped,
  change,
  now,
}: {
  shipped: boolean;
  change: Change;
  now?: Date;
}) {
  if (shipped) return <ShippedMarker />;
  return (
    <LivenessProbe
      liveness={change.liveness}
      lastActivityAt={change.lastActivityAt}
      now={now}
    />
  );
}

/** WP-008 — the quiet ASSIGNED chip: a neutral monogram tile + the product
 *  name. A non-interactive <span>, so it sits inside the card <Link>
 *  legitimately. Never colour-alone — the glyph + the name carry the meaning. */
function AssignedProductChip({ product }: { product: Product }) {
  return (
    <span className={styles.cardProductChip} data-testid="card-product-chip">
      <span className={styles.cardProductMono} aria-hidden="true">
        {monogram(product.name)}
      </span>
      <span className={styles.cardProductName}>{product.name}</span>
    </span>
  );
}

/** The meta line: slug + (shipped recency, WP-012) + (assigned chip, WP-008).
 *  Shipped recency is the archival "shipped Nd ago" read (Q-7), NOT a live age,
 *  derived from `updatedAt` (always present, unlike the nullable lastActivityAt). */
function CardMeta({
  slugText,
  shipped,
  updatedAt,
  now,
  assignedProduct,
}: {
  slugText: string;
  shipped: boolean;
  updatedAt: string;
  now?: Date;
  assignedProduct: Product | null;
}) {
  return (
    <div className={styles.cardMeta}>
      <span className={styles.slug}>{slugText}</span>
      {shipped ? (
        <span className={styles.shippedRecency} data-testid="shipped-recency">
          {formatShippedRecency(updatedAt, now)}
        </span>
      ) : null}
      {assignedProduct ? (
        <AssignedProductChip product={assignedProduct} />
      ) : null}
    </div>
  );
}

/** THE ONE FOOT VERDICT — waiting XOR health, never both (the founder's
 *  load-bearing rule, BR-1). WP-012 — SUPPRESSED entirely on a shipped card:
 *  a terminal change shows NEITHER live foot (BR-28 mutual suppression). */
function CardFootVerdict({
  shipped,
  flagged,
  change,
}: {
  shipped: boolean;
  flagged: boolean;
  change: Change;
}) {
  if (shipped) return null;
  return (
    <div className={`${styles.footRow} ${flagged ? styles.waitingFoot : ""}`}>
      {flagged ? (
        <WaitingOnYou why={attentionWhy(change.needsAttention.reason)} />
      ) : (
        <ChangeHealthBadge health={change.health} />
      )}
    </div>
  );
}

/** WP-011 — the quiet, FIXED-STRING degraded notice (FR-55). Reinforcement of
 *  the per-field unknown reads (BR-3); role="status" announces it so it is never
 *  colour-/placement-alone (NFR-A11Y-4). Never interpolates row content. */
function DegradedNotice({ show }: { show: boolean }) {
  if (!show) return null;
  return (
    <div className={styles.degradedNote} role="status">
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={1.8}
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="9" />
        <path d="M12 8v4M12 16h.01" strokeLinecap="round" />
      </svg>
      {DEGRADED_NOTICE}
    </div>
  );
}

/** WP-009 — the "Open terminal" action: a SEPARATE tab stop inside the card
 *  (stopPropagation, so it doesn't also navigate). Omitted → not rendered. */
function OpenTerminalAction({
  changeId,
  onOpenTerminal,
}: {
  changeId: string;
  onOpenTerminal?: (changeId: string) => void;
}) {
  if (!onOpenTerminal) return null;
  return (
    <div className={styles.actions}>
      <button
        type="button"
        className={styles.openTerminal}
        onClick={(event) => {
          // "open terminal" is a distinct action from "open change" — stop the
          // click from also navigating via the enclosing card <Link>.
          event.preventDefault();
          event.stopPropagation();
          onOpenTerminal(changeId);
        }}
      >
        Open terminal
      </button>
    </div>
  );
}

export function ChangeCard({
  change,
  selected = false,
  onOpenTerminal,
  now,
  products,
}: ChangeCardProps) {
  const step = stageStepNumber(change.stage);
  const flagged = change.needsAttention.flagged;
  const degraded = isDegraded(change);
  // WP-012 — terminal/archived treatment. Shipped wins the foot/probe over the
  // live + degraded reads (SRD §7c precedence); the per-field identity reads
  // still apply (an unreadable slug/intent still falls to its placeholder).
  const shipped = isShipped(change);

  const { intentText, slugText, ariaIntent } = degradedFields(change);

  // WP-008 — the assigned product drives the quiet foot-meta chip, the card's
  // accessible name, and whether the unassigned affordance shows. A shipped card
  // keeps its product read like any other; it just shows no affordance.
  const assignedProduct = resolveAssignedProduct(change, products);
  const assigned = assignedProduct !== null;
  // The product name rides the card's accessible name when assigned, so a screen
  // reader hears which product the change belongs to.
  const productAria = assignedProduct ? ` · ${assignedProduct.name}` : "";

  return (
    <div className={styles.cardShell} data-testid="change-card-shell">
      <Link
        to={`/c/${change.changeId}`}
        className={cardClassName(selected, degraded, shipped)}
        data-testid="change-card"
        // WP-009 — route-derived selection marker. data-selected drives the CSS
        // and test selection (mirrors SidebarItem's data-active); aria-current
        // announces it to assistive tech so it's never colour-/placement-alone
        // (NFR-A11Y-1). Additive — it sits alongside the degraded/shipped reads.
        data-selected={attrFlag(selected)}
        aria-current={attrFlag(selected)}
        data-degraded={attrFlag(degraded)}
        data-shipped={attrFlag(shipped)}
        aria-label={`Change ${change.handle}: ${ariaIntent}${productAria}`}
      >
        <div className={styles.topLine}>
          <span className={styles.handle}>{change.handle}</span>
          <CardProbe shipped={shipped} change={change} now={now} />
        </div>

        <StepDots step={step} />

        {/* Intent is clamped to 2 lines in CSS so the card stays a calm fixed
         * shape; the full text stays reachable via the title + the card aria-label. */}
        <p className={styles.intent} title={intentText}>
          {intentText}
        </p>

        <CardMeta
          slugText={slugText}
          shipped={shipped}
          updatedAt={change.updatedAt}
          now={now}
          assignedProduct={assignedProduct}
        />

        <CardFootVerdict shipped={shipped} flagged={flagged} change={change} />

        <DegradedNotice show={degraded} />

        <OpenTerminalAction
          changeId={change.changeId}
          onOpenTerminal={onOpenTerminal}
        />
      </Link>

      {/* WP-008 — the assign-from-card affordance. Rendered OUTSIDE the <Link>
       * (interactive content can't nest in an anchor) and only when a products
       * list is injected (the board), the change is UNASSIGNED, and it's not
       * shipped (a terminal change has nothing to assign in context). Honours the
       * recorded WP fallback: if it ever destabilises the card it can be dropped
       * (the change-nav property, WP-006, is the alternate surface) — but it
       * ships here per the signed design. */}
      {products && !assigned && !shipped ? (
        <CardProductAffordance changeId={change.changeId} products={products} />
      ) : null}
    </div>
  );
}
