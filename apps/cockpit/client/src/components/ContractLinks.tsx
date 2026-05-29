// WP-003 — <ContractLinks> — per-change "open data contract / open UI"
// affordances (TDD §2.1 client; WPF-01 composed component, WPF-05 the three
// states, WPF-06 a11y, WPF-07 tokens, WPF-02 typed client).
//
// Renders, for ONE change, links to its OWN rendered contracts:
//   - "Open data contract" → /api/changes/:id/contract/data (CONTRACT.html)
//   - "Open UI"            → /api/changes/:id/contract/ui   (UI.html)
//
// Both hrefs derive from the change's own id (ADR-003 — generic, never
// hard-wired). The links open the server-rendered HTML in a new tab; the
// founder never navigates a worktree (TDD §5).
//
// States (WPF-05):
//   - loading      → a status line while the summary is fetched;
//   - error        → a plain note + Retry;
//   - ready+UI     → both links;
//   - ready+no-UI  → the data link + a plain "no UI contract" note (NEVER a
//                    broken link — honest-confidence, WPF-12);
//   - unavailable  → a plain degrade note (a shipped change we couldn't reach).
//
// Honest-confidence (WPF-12): the "no UI contract" / "couldn't reach" notes
// are surfaced plainly, not hidden behind a dead link.

import type { Change } from "../../../shared/api-types";
import { useContractPreview } from "../api/useContractPreview";
import styles from "./ContractLinks.module.css";

export interface ContractLinksProps {
  change: Change;
}

export function ContractLinks({ change }: ContractLinksProps) {
  const { changeId, handle } = change;
  const query = useContractPreview(changeId);

  return (
    <section
      className={styles.links}
      data-testid="contract-links"
      aria-label={`Contracts for ${handle}`}
    >
      <h3 className={styles.heading}>Contracts</h3>

      {query.isLoading && (
        <p className={styles.status} data-testid="contract-links-loading">
          Loading the contract preview…
        </p>
      )}

      {query.isError && (
        <div className={styles.note} role="alert">
          <p>Couldn&rsquo;t load the contract preview for this change.</p>
          <button
            type="button"
            className={styles.retry}
            onClick={() => query.refetch()}
          >
            Retry
          </button>
        </div>
      )}

      {query.isSuccess && query.data.status === "unavailable" && (
        <p className={styles.note} data-testid="contract-links-unavailable">
          {query.data.note}
        </p>
      )}

      {query.isSuccess && query.data.status === "ready" && (
        <ReadyLinks
          changeId={changeId}
          handle={handle}
          present={query.data.present}
          dataName={query.data.dataContract?.name ?? null}
          ui={query.data.uiContract}
        />
      )}
    </section>
  );
}

interface ReadyLinksProps {
  changeId: string;
  handle: string;
  present: boolean;
  dataName: string | null;
  ui: { status: "present" } | { status: "none"; note: string };
}

function ReadyLinks({
  changeId,
  handle,
  present,
  dataName,
  ui,
}: ReadyLinksProps) {
  if (!present) {
    // Worktree resolved but nothing rendered yet (e.g. before the
    // pre-dispatch review gate has run).
    return (
      <p className={styles.note} data-testid="contract-links-not-rendered">
        No contract preview has been rendered for this change yet.
      </p>
    );
  }
  return (
    <ul className={styles.list}>
      <li>
        <a
          className={styles.link}
          href={`/api/changes/${changeId}/contract/data`}
          target="_blank"
          rel="noreferrer"
          aria-label={`Open data contract for ${handle}`}
        >
          Open data contract
          {dataName ? <span className={styles.meta}> ({dataName})</span> : null}
        </a>
      </li>
      <li>
        {ui.status === "present" ? (
          <a
            className={styles.link}
            href={`/api/changes/${changeId}/contract/ui`}
            target="_blank"
            rel="noreferrer"
            aria-label={`Open UI preview for ${handle}`}
          >
            Open UI
          </a>
        ) : (
          <span className={styles.note} data-testid="contract-links-no-ui">
            {ui.note}
          </span>
        )}
      </li>
    </ul>
  );
}
