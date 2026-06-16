// ProductPicker — assign (or change) a change's Product, in the detail view.
//
// A small native <select> of the founder's Products, showing the change's
// current assignment. Picking one calls the assignment endpoint and invalidates
// the board so its product filter reflects the change. Native <select> keeps it
// accessible (keyboard + screen-reader) and tokens-only (no raw colour).
//
// Hidden when there are no Products yet (nothing to assign to) — the founder
// creates one first via "Set up a new product".

import { useProducts } from "../api/useProducts";
import { useAssignChangeProduct } from "../api/assignChangeProduct";
import styles from "../styles/Thread.module.css";

interface Props {
  changeId: string;
  /** The change's current Product id, or null/undefined when unassigned. */
  currentProductId: string | null | undefined;
}

export function ProductPicker({ changeId, currentProductId }: Props) {
  const products = useProducts();
  const assign = useAssignChangeProduct(changeId);

  const list = products.data?.products ?? [];
  if (list.length === 0) return null;

  return (
    <select
      className={styles.productPicker}
      data-testid="change-product-picker"
      aria-label="Assign this change to a product"
      value={currentProductId ?? ""}
      disabled={assign.isPending}
      onChange={(e) => {
        const productId = e.target.value;
        if (productId) assign.mutate(productId);
      }}
    >
      <option value="" disabled>
        Assign a product…
      </option>
      {list.map((p) => (
        <option key={p.productId} value={p.productId}>
          {p.name}
        </option>
      ))}
    </select>
  );
}
