// WP-008 — ProductRow — one product card in the Settings tree.
//
// Renders a product (name + its projects) to the signed WP-VIS mockup. An
// EDITABLE product (the normal + carried-over case) shows the Rename / Remove
// product affordances and an "Add project" affordance, and its projects render
// editable. A READ-ONLY product (editable:false — the synthesised implicit
// single product, IMMUTABLE_IMPLICIT/ADR-020) shows neither: it renders its
// tree read-only, and the page surfaces the "Add your first product" first-run
// affordance instead.
//
// Every affordance is a callback into WP-009's forms / dialogs — this card owns
// NO write logic (WP-008 Contract).

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits); the WP Contract pins these rows at pages/settings/ (4 levels deep)
import type {
  SettingsProduct,
  SettingsProject,
} from "../../../../shared/api-types";
import { ProjectRow } from "./ProjectRow";
import { RowActionButton } from "./RowActionButton";
import styles from "./Settings.module.css";

interface Props {
  product: SettingsProduct;
  onRenameProduct?: (product: SettingsProduct) => void;
  onRemoveProduct?: (product: SettingsProduct) => void;
  onAddProject?: (product: SettingsProduct) => void;
  onEditProject?: (project: SettingsProject) => void;
  onChangeRepo?: (project: SettingsProject) => void;
  onAttachRepo?: (project: SettingsProject) => void;
  onRemoveProject?: (project: SettingsProject) => void;
}

export function ProductRow({
  product,
  onRenameProduct,
  onRemoveProduct,
  onAddProject,
  onEditProject,
  onChangeRepo,
  onAttachRepo,
  onRemoveProject,
}: Props) {
  const readOnly = !product.editable;

  return (
    <div className={styles.product} data-testid="settings-product">
      <div className={styles.productHead}>
        <span className={styles.productName}>{product.name}</span>
        <span className={styles.spacer} />
        {!readOnly && (
          <div className={styles.rowActions}>
            {/* Affordances render per the signed mockup; the click handlers are
                wired by WP-010 when WP-009's forms/dialogs exist (the handlers
                are optional until then). */}
            <RowActionButton onClick={() => onRenameProduct?.(product)}>
              Rename
            </RowActionButton>
            <RowActionButton
              variant="danger"
              ariaLabel={`Remove ${product.name}`}
              onClick={() => onRemoveProduct?.(product)}
            >
              Remove
            </RowActionButton>
          </div>
        )}
      </div>

      <div className={styles.projects}>
        {product.projects.map((project) => (
          <ProjectRow
            key={project.projectId}
            project={project}
            readOnly={readOnly}
            onEdit={onEditProject}
            onChangeRepo={onChangeRepo}
            onAttachRepo={onAttachRepo}
            onRemove={onRemoveProject}
          />
        ))}

        {!readOnly && (
          <div className={styles.addProject}>
            <RowActionButton onClick={() => onAddProject?.(product)}>
              + Add project
            </RowActionButton>
          </div>
        )}
      </div>
    </div>
  );
}
