// WP-008 — ProjectRow — one project node in the Settings tree.
//
// Renders a project (name + its repo line via RepoRow) with the affordance
// buttons from the signed WP-VIS mockup: Edit, Change folder (only when a repo
// is attached), Remove. The affordances are callbacks that open WP-009's forms
// / confirm-remove dialog — this row owns NO write logic (WP-008 Contract:
// "the affordance buttons that open WP-009's forms via callbacks/props").
//
// A read-only product (editable:false — the synthesised implicit product)
// passes `readOnly`, which hides every affordance (IMMUTABLE_IMPLICIT).

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits); the WP Contract pins these rows at pages/settings/ (4 levels deep)
import type { SettingsProject } from "../../../../shared/api-types";
import { RepoRow } from "./RepoRow";
import { RowActionButton } from "./RowActionButton";
import styles from "./Settings.module.css";

interface Props {
  project: SettingsProject;
  readOnly?: boolean;
  onEdit?: (project: SettingsProject) => void;
  onChangeRepo?: (project: SettingsProject) => void;
  onAttachRepo?: (project: SettingsProject) => void;
  onRemove?: (project: SettingsProject) => void;
}

export function ProjectRow({
  project,
  readOnly = false,
  onEdit,
  onChangeRepo,
  onAttachRepo,
  onRemove,
}: Props) {
  const hasRepo = project.repo !== null;

  return (
    <div className={styles.project} data-testid="settings-project">
      <span className={styles.projIcon} aria-hidden="true">
        ❮❯
      </span>
      <div className={styles.projBody}>
        <div className={styles.projName}>{project.name}</div>
        <RepoRow
          repo={project.repo}
          readOnly={readOnly}
          onAttachRepo={onAttachRepo ? () => onAttachRepo(project) : undefined}
        />
      </div>

      {!readOnly && (
        <div className={styles.rowActions}>
          {/* Affordances render per the signed mockup; handlers are wired by
              WP-010 when WP-009's forms/dialogs exist (optional until then). */}
          <RowActionButton onClick={() => onEdit?.(project)}>
            Edit
          </RowActionButton>
          {/* "Change folder" only when a folder is attached (mockup): an
              unlinked project gets the "Attach a folder" CTA on its repo line. */}
          {hasRepo && (
            <RowActionButton onClick={() => onChangeRepo?.(project)}>
              Change folder
            </RowActionButton>
          )}
          <RowActionButton
            variant="danger"
            ariaLabel={`Remove ${project.name}`}
            onClick={() => onRemove?.(project)}
          >
            Remove
          </RowActionButton>
        </div>
      )}
    </div>
  );
}
