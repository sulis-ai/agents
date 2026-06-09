// WP-009 — <EntityForm> tests (the shared create/edit form).
//
// EntityForm is the create/edit twin (ProductWrite / ProjectWrite driven): a
// single labelled field + hint + Cancel/Save, submitting through the WP-007
// typed fetcher (injected as the `onSubmit` prop, returning a Result). On a
// typed error it renders the message inline — never a thrown opaque (WPF-02,
// errors-are-values). On success it invokes the WP-008 query-invalidation
// callback (`onSuccess`) so the tree + switcher refresh.
//
// Built standalone (props-driven) against a fake fetcher; not wired into a
// page (that is WP-008/WP-010). jest-axe per WPF-06.

import { describe, it, expect, vi } from "vitest";
import { render, fireEvent, waitFor } from "@testing-library/react";
import { axe } from "jest-axe";
// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits); pages/settings/ is one level deeper than api/, so the wire-type import is 4 levels up. Mirrors api/settings.ts.
import type { SettingsProduct } from "../../../../shared/api-types";
import type { Result, SettingsError } from "../../api/settings";
import { EntityForm } from "./EntityForm";

const PRODUCT: SettingsProduct = {
  productId: "dna:product:01ACME00000000000000000000",
  name: "Sulis Cockpit",
  editable: true,
  projects: [],
};

function validationError(): SettingsError {
  return {
    code: "VALIDATION_FAILED",
    message: "A product name is required.",
  };
}

describe("<EntityForm>", () => {
  it("renders_inline_validation_error_axe_clean", async () => {
    const onSubmit = vi.fn(
      async (): Promise<Result<SettingsProduct>> => ({
        ok: false,
        error: validationError(),
      }),
    );
    const { getByLabelText, getByRole, findByText, container } = render(
      <EntityForm
        title="Rename product"
        label="Product name"
        hint="Shown in the product switcher and across the cockpit."
        initialValue="Sulis Cockpit"
        submitLabel="Save"
        onSubmit={onSubmit}
        onCancel={vi.fn()}
        onSuccess={vi.fn()}
      />,
    );

    // The field is a real <label>-associated input (not a placeholder).
    const input = getByLabelText("Product name");
    fireEvent.change(input, { target: { value: "" } });
    fireEvent.click(getByRole("button", { name: "Save" }));

    // The typed error renders inline, in plain English — never thrown.
    const err = await findByText("A product name is required.");
    expect(err).toBeInTheDocument();
    expect(onSubmit).toHaveBeenCalledTimes(1);

    // WCAG AA — the error-bearing form is axe-clean.
    expect(await axe(container)).toHaveNoViolations();
  });

  it("invokes the invalidation callback on a successful save", async () => {
    const onSubmit = vi.fn(
      async (): Promise<Result<SettingsProduct>> => ({
        ok: true,
        value: { ...PRODUCT, name: "Renamed" },
      }),
    );
    const onSuccess = vi.fn();
    const { getByLabelText, getByRole } = render(
      <EntityForm
        title="Rename product"
        label="Product name"
        hint="Shown in the product switcher and across the cockpit."
        initialValue="Sulis Cockpit"
        submitLabel="Save"
        onSubmit={onSubmit}
        onCancel={vi.fn()}
        onSuccess={onSuccess}
      />,
    );

    fireEvent.change(getByLabelText("Product name"), {
      target: { value: "Renamed" },
    });
    fireEvent.click(getByRole("button", { name: "Save" }));

    await waitFor(() => expect(onSuccess).toHaveBeenCalledTimes(1));
    expect(onSubmit).toHaveBeenCalledWith("Renamed");
  });

  it("Cancel fires onCancel and performs no submit", () => {
    const onSubmit = vi.fn();
    const onCancel = vi.fn();
    const { getByRole } = render(
      <EntityForm
        title="Rename product"
        label="Product name"
        hint="Shown in the product switcher and across the cockpit."
        initialValue="Sulis Cockpit"
        submitLabel="Save"
        onSubmit={onSubmit}
        onCancel={onCancel}
        onSuccess={vi.fn()}
      />,
    );
    fireEvent.click(getByRole("button", { name: "Cancel" }));
    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
