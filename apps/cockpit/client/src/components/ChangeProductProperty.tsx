// WP-006 — the change-nav product property (ADR-002, SUBSTITUTE-Replace).
//
// Replaces the raw native <select> (ProductPicker, deleted) with a labelled
// "Product" property that renders the shared <ProductControl mode="assign">
// primitive (WP-002). It is a THIN placement: it supplies the product rows + the
// current selection + the commit handlers, and the primitive owns all the menu /
// keyboard / a11y logic (ADR-002 "build once, place three times").
//
// Commit-on-select, no Save button (Concern B1):
//   - picking a product commits via useAssignChangeProduct (the existing assign
//     write, reused verbatim);
//   - "Remove from product" commits via useClearChangeProduct (WP-004);
//   - the in-flight write shows "Saving…", success shows a "Saved" tick — the
//     primitive's aria-live region announces both (never colour alone).
//
// The primitive NEVER calls the network; this placement injects the hooks at the
// edge, keeping ProductControl a pure, testable component. Hidden when the
// Tenant has no products yet (nothing to assign to) — the founder creates one
// first via "Set up a new product".

import { useEffect, useRef, useState } from "react";

import { useProducts } from "../api/useProducts";
import { useAssignChangeProduct } from "../api/assignChangeProduct";
import { useClearChangeProduct } from "../api/clearChangeProduct";
import { ProductControl, type ProductRow } from "./ProductControl";

interface Props {
  changeId: string;
  /** The change's current Product id, or null/undefined when unassigned. */
  currentProductId: string | null | undefined;
  /** "Set up a new product" foot action (routes to settings; optional). */
  onSetUpNew?: () => void;
}

/** How long the "Saved" tick lingers after a successful commit (ms). */
const SAVED_LINGER_MS = 1800;

export function ChangeProductProperty({
  changeId,
  currentProductId,
  onSetUpNew,
}: Props) {
  const products = useProducts();
  const assign = useAssignChangeProduct(changeId);
  const clear = useClearChangeProduct(changeId);

  // The aria-live commit feedback: "saving" while either write is in flight,
  // then "saved" briefly once it settles, then back to idle. Mirrors the
  // primitive's saveState contract (idle | saving | saved).
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved">(
    "idle",
  );
  const savedTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const inFlight = assign.isPending || clear.isPending;
  const settledSuccess = assign.isSuccess || clear.isSuccess;

  useEffect(() => {
    if (inFlight) {
      setSaveState("saving");
      return;
    }
    if (settledSuccess) {
      setSaveState("saved");
      if (savedTimer.current) clearTimeout(savedTimer.current);
      savedTimer.current = setTimeout(() => setSaveState("idle"), SAVED_LINGER_MS);
    }
  }, [inFlight, settledSuccess]);

  useEffect(
    () => () => {
      if (savedTimer.current) clearTimeout(savedTimer.current);
    },
    [],
  );

  const list = products.data?.products ?? [];
  // Nothing to assign to until the founder has a product — keep the nav clean.
  if (list.length === 0) return null;

  const rows: ProductRow[] = list.map((p) => ({
    productId: p.productId,
    name: p.name,
    glyph: "monogram",
  }));

  const selectedId = currentProductId ?? null;
  const assignedName =
    list.find((p) => p.productId === selectedId)?.name ?? null;

  // The trigger's accessible name carries the change's product even when the
  // visible name folds at narrow nav widths (the change-nav e2e a11y gate):
  // assigned → "Product: <name>, change product"; unassigned → "Add this change
  // to a product".
  const triggerLabel = assignedName
    ? `Product: ${assignedName}, change product`
    : "Add this change to a product";

  return (
    <ProductControl
      mode="assign"
      rows={rows}
      selectedId={selectedId}
      triggerLabel={triggerLabel}
      saveState={saveState}
      onSelect={(id) => {
        if (id) assign.mutate(id);
      }}
      onRemove={() => clear.mutate()}
      onSetUpNew={onSetUpNew}
    />
  );
}
