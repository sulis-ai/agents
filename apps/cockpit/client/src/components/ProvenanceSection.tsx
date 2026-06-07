// WP-P06 — <ProvenanceSection /> — the data-bound Provenance container.
//
// Fetches the change's Provenance read projection (useProvenance) + the flat
// brain (useBrain, for the "Browse everything" fallback) and renders the
// presentational <ProvenanceView>. Owns the coverage lens's selected
// requirement so it can run the `?focus=<reqId>` query (useFocusedTrace) and
// hand the resolved trace down — keeping <ProvenanceView> pure. Loading /
// error reuse the app's one state-pattern set (ADR-005): a plain status line,
// never a broken shell. Mirrors the thread's container/presentational split.

import { useState } from "react";
import { useProvenance, useFocusedTrace } from "../api/useProvenance";
import { useBrain } from "../api/useBrain";
import { useOrigin } from "../api/useOrigin";
import { ProvenanceView } from "./ProvenanceView";
import type { ChangeView } from "./ChangeNav";

interface Props {
  changeId: string;
  /** Switch the change view (for the "How it came to be" lens's jumps). */
  onSelectView?: (view: ChangeView) => void;
}

export function ProvenanceSection({ changeId, onSelectView }: Props) {
  const query = useProvenance(changeId);
  const brain = useBrain(changeId);
  const origin = useOrigin(changeId);

  // The selected requirement for the coverage drill-in; the focus query stays
  // disabled (returns nothing) until one is chosen.
  const [focusId, setFocusId] = useState<string | null>(null);
  const focusQuery = useFocusedTrace(changeId, focusId ?? "");

  if (query.isLoading) {
    return (
      <p
        data-testid="provenance-loading"
        style={{ padding: 24, color: "var(--muted-foreground)" }}
      >
        Loading what Sulis did…
      </p>
    );
  }

  if (query.isError) {
    return (
      <p role="alert" data-testid="provenance-error" style={{ padding: 24 }}>
        Couldn&rsquo;t load what Sulis did on this change.
      </p>
    );
  }

  return (
    <ProvenanceView
      view={query.data!}
      focusId={focusId}
      onFocus={setFocusId}
      focus={{
        trace: focusId ? focusQuery.data : undefined,
        isLoading: focusId ? focusQuery.isLoading : false,
        isError: focusId ? focusQuery.isError : false,
      }}
      brain={brain.isSuccess ? brain.data : undefined}
      origin={origin.isSuccess ? origin.data : undefined}
      onSelectView={onSelectView}
    />
  );
}
