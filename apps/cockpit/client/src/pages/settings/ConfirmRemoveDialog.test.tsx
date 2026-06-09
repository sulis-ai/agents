// WP-009 — <ConfirmRemoveDialog> tests (the disk-safety promise, WP-VIS item 8).
//
// The remove-confirmation dialog. Its load-bearing content is the positive-
// tinted "Your files are safe" note — SPEC binding decision 4 (ADR-020:
// remove = soft-delete, never a file delete) surfaced to the founder in plain
// English. The ConfirmRemoveDialog test asserts that note's presence; it is
// not decoration.
//
// Built standalone (props-driven) against a fake confirm fetcher. jest-axe per
// WPF-06.

import { describe, it, expect, vi } from "vitest";
import { render, fireEvent, waitFor } from "@testing-library/react";
import { axe } from "jest-axe";
import type { Result } from "../../api/settings";
import { ConfirmRemoveDialog } from "./ConfirmRemoveDialog";

describe("<ConfirmRemoveDialog>", () => {
  it("shows_files_are_safe_note", async () => {
    const { getByText, container } = render(
      <ConfirmRemoveDialog
        entityName="design-tokens"
        title='Remove "design-tokens"?'
        onConfirm={vi.fn(
          async (): Promise<Result<void>> => ({
            ok: true,
            value: undefined,
          }),
        )}
        onCancel={vi.fn()}
        onSuccess={vi.fn()}
      />,
    );

    // The disk-safety promise, verbatim from the signed mockup (WP-VIS item 8).
    expect(getByText(/Your files are safe\./i)).toBeInTheDocument();
    expect(
      getByText(
        /Nothing on your computer is deleted — this only removes the link\./i,
      ),
    ).toBeInTheDocument();

    expect(await axe(container)).toHaveNoViolations();
  });

  it("confirm fires onConfirm then onSuccess (the invalidation callback)", async () => {
    const onConfirm = vi.fn(
      async (): Promise<Result<void>> => ({ ok: true, value: undefined }),
    );
    const onSuccess = vi.fn();
    const { getByRole } = render(
      <ConfirmRemoveDialog
        entityName="design-tokens"
        title='Remove "design-tokens"?'
        onConfirm={onConfirm}
        onCancel={vi.fn()}
        onSuccess={onSuccess}
      />,
    );

    fireEvent.click(getByRole("button", { name: "Remove the link" }));
    await waitFor(() => expect(onSuccess).toHaveBeenCalledTimes(1));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("renders a typed error inline when the remove fails (errors-are-values)", async () => {
    const onConfirm = vi.fn(
      async (): Promise<Result<void>> => ({
        ok: false,
        error: {
          code: "WRITE_FAILED",
          message: "Couldn't save that change. Try again.",
        },
      }),
    );
    const onSuccess = vi.fn();
    const { getByRole, findByText } = render(
      <ConfirmRemoveDialog
        entityName="design-tokens"
        title='Remove "design-tokens"?'
        onConfirm={onConfirm}
        onCancel={vi.fn()}
        onSuccess={onSuccess}
      />,
    );

    fireEvent.click(getByRole("button", { name: "Remove the link" }));

    const err = await findByText("Couldn't save that change. Try again.");
    expect(err).toBeInTheDocument();
    expect(onSuccess).not.toHaveBeenCalled();
  });

  it("Cancel fires onCancel and performs no remove", () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    const { getByRole } = render(
      <ConfirmRemoveDialog
        entityName="design-tokens"
        title='Remove "design-tokens"?'
        onConfirm={onConfirm}
        onCancel={onCancel}
        onSuccess={vi.fn()}
      />,
    );
    fireEvent.click(getByRole("button", { name: "Cancel" }));
    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(onConfirm).not.toHaveBeenCalled();
  });
});
