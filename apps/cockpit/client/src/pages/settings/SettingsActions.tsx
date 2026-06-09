// WP-010 — the Settings write-affordance overlay (the open seam, closed).
//
// WP-008 built the read tree with affordance buttons whose handlers were unset;
// WP-009 built the standalone forms/dialog (EntityForm / AttachRepoForm /
// ConfirmRemoveDialog). This component is the wiring WP-010 adds: it owns the
// "which form is open, against which entity" state and renders the right WP-009
// component for it, driving the WP-007 typed fetchers (writeProduct /
// writeProject / attachRepo / removeProduct / removeProject) and invalidating
// the WP-008 cache keys on success so the tree + product switcher refresh
// WITHOUT a page reload.
//
// The page passes the affordance callbacks (onRenameProduct, onAddProject, …)
// straight from `useSettingsActions().handlers` into ProductRow, and renders
// `<SettingsActionOverlay/>` once at the page root. Keeping the form-routing
// here (rather than inline in SettingsPage) keeps the page a thin read surface
// and puts every write affordance behind ONE invalidation funnel (EP-03).

import { useCallback, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits); pages/settings/ is 4 levels deep.
import type {
  SettingsProduct,
  SettingsProject,
} from "../../../../shared/api-types";
import {
  writeProduct,
  writeProject,
  attachRepo,
  removeProduct,
  removeProject,
} from "../../api/settings";
import { SETTINGS_QUERY_KEY, PRODUCTS_QUERY_KEY } from "../../api/useSettings";
import { EntityForm } from "./EntityForm";
import { AttachRepoForm } from "./AttachRepoForm";
import { ConfirmRemoveDialog } from "./ConfirmRemoveDialog";

/** The currently-open write affordance (a discriminated union — exactly one
 *  form/dialog is open at a time, or none). */
export type ActiveForm =
  | { kind: "add-product" }
  | { kind: "rename-product"; product: SettingsProduct }
  | { kind: "remove-product"; product: SettingsProduct }
  | { kind: "add-project"; product: SettingsProduct }
  | { kind: "edit-project"; project: SettingsProject; productId: string }
  | { kind: "attach-repo"; project: SettingsProject }
  | { kind: "remove-project"; project: SettingsProject };

/** The affordance callbacks the tree rows call. Each opens the matching form. */
export interface SettingsActionHandlers {
  onAddProduct: () => void;
  onRenameProduct: (product: SettingsProduct) => void;
  onRemoveProduct: (product: SettingsProduct) => void;
  onAddProject: (product: SettingsProduct) => void;
  onEditProject: (project: SettingsProject, productId: string) => void;
  onAttachRepo: (project: SettingsProject) => void;
  onChangeRepo: (project: SettingsProject) => void;
  onRemoveProject: (project: SettingsProject) => void;
}

export interface UseSettingsActions {
  active: ActiveForm | null;
  handlers: SettingsActionHandlers;
  close: () => void;
  /** Invalidate the settings tree + the product switcher (no reload). */
  invalidate: () => void;
}

/**
 * The one place the settings-write affordances are wired. Returns the active
 * form + the handlers the tree rows call + the shared cache-invalidation +
 * close. `invalidate` refreshes BOTH the settings tree (so the page re-renders
 * the change) and the product switcher key (so a product rename/remove shows in
 * the cockpit's switcher) — the WP-008-documented invalidation contract.
 */
export function useSettingsActions(): UseSettingsActions {
  const queryClient = useQueryClient();
  const [active, setActive] = useState<ActiveForm | null>(null);

  const close = useCallback(() => setActive(null), []);

  const invalidate = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: SETTINGS_QUERY_KEY });
    void queryClient.invalidateQueries({ queryKey: PRODUCTS_QUERY_KEY });
  }, [queryClient]);

  const handlers: SettingsActionHandlers = {
    onAddProduct: useCallback(() => setActive({ kind: "add-product" }), []),
    onRenameProduct: useCallback(
      (product) => setActive({ kind: "rename-product", product }),
      [],
    ),
    onRemoveProduct: useCallback(
      (product) => setActive({ kind: "remove-product", product }),
      [],
    ),
    onAddProject: useCallback(
      (product) => setActive({ kind: "add-project", product }),
      [],
    ),
    onEditProject: useCallback(
      (project, productId) =>
        setActive({ kind: "edit-project", project, productId }),
      [],
    ),
    // "Attach a folder" (unlinked) and "Change folder" (already linked) both
    // open the attach form — attach is an upsert of Project.source (ADR-021).
    onAttachRepo: useCallback(
      (project) => setActive({ kind: "attach-repo", project }),
      [],
    ),
    onChangeRepo: useCallback(
      (project) => setActive({ kind: "attach-repo", project }),
      [],
    ),
    onRemoveProject: useCallback(
      (project) => setActive({ kind: "remove-project", project }),
      [],
    ),
  };

  return { active, handlers, close, invalidate };
}

interface OverlayProps {
  active: ActiveForm | null;
  close: () => void;
  invalidate: () => void;
}

/**
 * Render the WP-009 form/dialog for the active affordance. Every form's
 * `onSuccess` runs the shared `invalidate` (refresh tree + switcher, no reload)
 * then `close` (dismiss the overlay). The forms own their own inline error
 * rendering (errors-are-values, WPF-02) — the overlay never throws.
 */
export function SettingsActionOverlay({
  active,
  close,
  invalidate,
}: OverlayProps) {
  if (active === null) return null;

  const onSuccess = () => {
    invalidate();
    close();
  };

  switch (active.kind) {
    case "add-product":
      return (
        <EntityForm
          title="Add a product"
          label="Product name"
          hint="Shown in the product switcher and across the cockpit."
          initialValue=""
          submitLabel="Add"
          onSubmit={(name) => writeProduct({ name })}
          onCancel={close}
          onSuccess={onSuccess}
        />
      );

    case "rename-product":
      return (
        <EntityForm
          title="Rename product"
          label="Product name"
          hint="Shown in the product switcher and across the cockpit."
          initialValue={active.product.name}
          submitLabel="Save"
          onSubmit={(name) =>
            writeProduct({ productId: active.product.productId, name })
          }
          onCancel={close}
          onSuccess={onSuccess}
        />
      );

    case "add-project":
      return (
        <EntityForm
          title="Add a project"
          label="Project name"
          hint="A project groups the work and the folder behind it."
          initialValue=""
          submitLabel="Add"
          onSubmit={(name) =>
            writeProject({ productId: active.product.productId, name })
          }
          onCancel={close}
          onSuccess={onSuccess}
        />
      );

    case "edit-project":
      return (
        <EntityForm
          title="Rename project"
          label="Project name"
          hint="A project groups the work and the folder behind it."
          initialValue={active.project.name}
          submitLabel="Save"
          onSubmit={(name) =>
            // productId is immutable on edit (ADR-020) but the wire shape +
            // router boundary require a non-blank parent id; the adapter
            // ignores it when a projectId is present (goes straight to edit).
            writeProject({
              projectId: active.project.projectId,
              productId: active.productId,
              name,
            })
          }
          onCancel={close}
          onSuccess={onSuccess}
        />
      );

    case "attach-repo":
      return (
        <AttachRepoForm
          projectId={active.project.projectId}
          onAttach={(localPath) =>
            attachRepo({ projectId: active.project.projectId, localPath })
          }
          onCancel={close}
          onSuccess={onSuccess}
        />
      );

    case "remove-product":
      return (
        <ConfirmRemoveDialog
          entityName={active.product.name}
          title={`Remove “${active.product.name}”?`}
          onConfirm={() => removeProduct(active.product.productId)}
          onCancel={close}
          onSuccess={onSuccess}
        />
      );

    case "remove-project":
      return (
        <ConfirmRemoveDialog
          entityName={active.project.name}
          title={`Remove “${active.project.name}”?`}
          onConfirm={() => removeProject(active.project.projectId)}
          onCancel={close}
          onSuccess={onSuccess}
        />
      );
  }
}
