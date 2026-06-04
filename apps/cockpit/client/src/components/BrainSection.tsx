// WP-006 — <BrainSection /> — the data-bound Brain container (FR-06/07).
//
// Fetches the change's brain view (useBrain) and renders the presentational
// <BrainView>. Keeps <ThreadView> thin and <BrainView> pure (data-prop
// only), the same container/presentational split the rest of the thread
// uses. Loading / error reuse the app's one state-pattern set (ADR-005):
// a plain status line, never a broken shell.

import { useBrain } from "../api/useBrain";
import { BrainView } from "./BrainView";

interface Props {
  changeId: string;
}

export function BrainSection({ changeId }: Props) {
  const query = useBrain(changeId);

  if (query.isLoading) {
    return (
      <p data-testid="brain-loading" style={{ padding: 14 }}>
        Loading the brain…
      </p>
    );
  }

  if (query.isError) {
    return (
      <p role="alert" data-testid="brain-error" style={{ padding: 14 }}>
        Couldn&rsquo;t load what the agent has created for this change.
      </p>
    );
  }

  return <BrainView view={query.data!} />;
}
