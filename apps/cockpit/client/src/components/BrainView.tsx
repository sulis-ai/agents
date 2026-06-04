// WP-006 — <BrainView /> (FR-06/07).
//
// The right-panel "Brain" section: the entities the agent created for a
// change, GROUPED by kind, each group with its kind label + a count, each
// item with a readable title and an openable detail (FR-06/07). An empty
// brain shows a plain note — never a broken/empty shell (honest-confidence,
// matching the app's one state-pattern set, ADR-005).
//
// Presentational: takes a `BrainView` prop (the data-fetch lives in
// useBrain), exactly like <StageTrack> / <StatusHeader>. Colour is
// decorative only — kind labels + counts + titles carry all meaning, so
// the panel is legible without colour (WCAG 1.4.1; the SIGNED visual
// contract's `.bgroup`/`.bitem`). Consumes tokens.css only — no raw hex.

import { useState } from "react";
import type {
  BrainView as BrainViewModel,
  BrainEntity,
} from "../../../shared/api-types";
import styles from "../styles/BrainView.module.css";

interface Props {
  view: BrainViewModel;
}

export function BrainView({ view }: Props) {
  if (view.groups.length === 0) {
    return (
      <div
        className={styles.empty}
        data-testid="brain-empty"
        aria-label="Brain — nothing created yet"
      >
        <p>Nothing here yet.</p>
        <p className={styles.emptyDetail}>
          When the agent creates requirements, designs, decisions or workflows
          for this change, they&rsquo;ll show up here grouped by kind.
        </p>
      </div>
    );
  }

  return (
    <div
      className={styles.brain}
      aria-label="Brain — what the agent has created"
    >
      {view.groups.map((group) => (
        <section
          key={group.kind}
          className={styles.group}
          data-testid="brain-group"
          data-kind={group.kind}
        >
          <h5 className={styles.groupHead}>
            <span className={styles.kind}>{group.kind}</span>
            <span
              className={styles.count}
              aria-label={`${group.items.length} items`}
            >
              {group.items.length}
            </span>
          </h5>
          <ul className={styles.items}>
            {group.items.map((item) => (
              <BrainItem key={item.id} item={item} />
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}

function BrainItem({ item }: { item: BrainEntity }) {
  const [open, setOpen] = useState(false);
  return (
    <li className={styles.item} data-testid="brain-item">
      <button
        type="button"
        className={styles.itemHead}
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        <span className={styles.title}>{item.title}</span>
        <span className={styles.itemKind}>{item.kind}</span>
      </button>
      {open && (
        <dl className={styles.detail} data-testid="brain-detail">
          {detailRows(item).map(([label, value]) => (
            <div key={label} className={styles.detailRow}>
              <dt className={styles.detailLabel}>{label}</dt>
              <dd className={styles.detailValue}>{value}</dd>
            </div>
          ))}
        </dl>
      )}
    </li>
  );
}

/**
 * Flatten the entity's detail into readable label/value rows (FR-07).
 * Scalars render directly; arrays as a comma list; objects as compact JSON.
 * The id always leads so the founder can correlate the entity.
 */
function detailRows(item: BrainEntity): Array<[string, string]> {
  const rows: Array<[string, string]> = [["id", item.id]];
  const detail = item.detail ?? {};
  for (const [key, raw] of Object.entries(detail)) {
    if (key === "id") continue;
    rows.push([key, stringifyValue(raw)]);
  }
  return rows;
}

function stringifyValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (Array.isArray(value)) {
    return value.map((v) => stringifyValue(v)).join(", ");
  }
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}
