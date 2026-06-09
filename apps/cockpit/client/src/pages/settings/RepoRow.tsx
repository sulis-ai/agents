// WP-008 — RepoRow — the repo line under a project (read + state pill).
//
// Renders the project's repo link exactly as the signed WP-VIS mockup does:
// the local path (when attached) plus one of three repo-state pills, derived
// from the wire shape (ADR-021 read-only present check):
//
//   repo === null      → "No folder attached"   (neutral)   + Attach-folder CTA
//   repo.present false  → "Not a git repo yet"   (warning, non-blocking ADR-021)
//   repo.present true   → "Git repo"             (positive)
//
// WCAG 1.4.1 — colour is NEVER the sole cue: each pill carries a text label,
// and the decorative dot is aria-hidden. The Attach/Change-folder affordances
// are buttons that call back into WP-009's forms (no write logic here).

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits); the WP Contract pins these rows at pages/settings/ (4 levels deep)
import type { RepoLink } from "../../../../shared/api-types";
import { RowActionButton } from "./RowActionButton";
import styles from "./Settings.module.css";

export type RepoState = "attached" | "no-git" | "unlinked";

/** Derive the repo-state from the wire shape (the one place this maps). */
export function repoState(repo: RepoLink | null): RepoState {
  if (repo === null) return "unlinked";
  return repo.present ? "attached" : "no-git";
}

const PILL_LABEL: Record<RepoState, string> = {
  attached: "Git repo",
  "no-git": "Not a git repo yet",
  unlinked: "No folder attached",
};

const PILL_CLASS: Record<RepoState, string> = {
  // CSS-module classes are known-present at build (non-null assertion is the
  // codebase convention under noUncheckedIndexedAccess — cf. StageBadge.tsx).
  attached: styles.pillOk!,
  "no-git": styles.pillWarn!,
  unlinked: styles.pillNone!,
};

interface Props {
  repo: RepoLink | null;
  /** A read-only product hides the attach affordance (IMMUTABLE_IMPLICIT). */
  readOnly?: boolean;
  /** Open WP-009's attach-folder form for an unlinked project. */
  onAttachRepo?: () => void;
}

export function RepoRow({ repo, readOnly = false, onAttachRepo }: Props) {
  const state = repoState(repo);
  const hasDot = state !== "unlinked";

  return (
    <div className={styles.repoLine}>
      {repo?.localPath != null && (
        <span className={styles.repoPath} title={repo.localPath}>
          {repo.localPath}
        </span>
      )}

      <span
        className={`${styles.pill} ${PILL_CLASS[state]}`}
        data-repo-state={state}
      >
        {hasDot && (
          <span
            className={`${styles.dot} ${state === "attached" ? styles.dotOk : styles.dotWarn}`}
            aria-hidden="true"
          />
        )}
        {PILL_LABEL[state]}
      </span>

      {state === "unlinked" && !readOnly && (
        <RowActionButton onClick={() => onAttachRepo?.()}>
          Attach a folder
        </RowActionButton>
      )}
    </div>
  );
}
