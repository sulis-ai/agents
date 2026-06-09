// WP-009 — <AttachRepoForm> tests (local-path-only attach, ADR-021).
//
// The attach-folder form: a labelled local-path input + Cancel/Attach,
// submitting through the WP-007 fetcher (injected `onAttach`, returns a
// Result). Two ADR-021 behaviours under test:
//
//   1. PATH_NOT_FOUND is a HARD, blocking inline error rendered in plain
//      English ("We couldn't find that folder…") — never a thrown opaque.
//   2. A non-git folder still ATTACHES (onAttach resolves ok with a project
//      whose repo.present === false); the form shows a NON-blocking "not a
//      git repo yet" note and still fires onSuccess — it never blocks.

import { describe, it, expect, vi } from "vitest";
import { render, fireEvent, waitFor } from "@testing-library/react";
import { axe } from "jest-axe";
// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits); pages/settings/ is one level deeper than api/, so the wire-type import is 4 levels up. Mirrors api/settings.ts.
import type { SettingsProject } from "../../../../shared/api-types";
import type { Result, SettingsError } from "../../api/settings";
import { AttachRepoForm } from "./AttachRepoForm";

const PROJECT_ID = "dna:project:01PROJ0000000000000000000";

function pathNotFound(): SettingsError {
  return {
    code: "PATH_NOT_FOUND",
    message: "PATH_NOT_FOUND", // raw code — the form must render plain English, not echo this.
  };
}

function attachedNonRepo(): SettingsProject {
  return {
    projectId: PROJECT_ID,
    name: "design-tokens",
    repo: {
      localPath: "/Users/founder/code/new-folder",
      primaryBranch: "main",
      present: false, // attached, but no .git yet (ADR-021 warning, non-blocking)
    },
  };
}

describe("<AttachRepoForm>", () => {
  it("path_not_found_shows_plain_english_inline", async () => {
    const onAttach = vi.fn(
      async (): Promise<Result<SettingsProject>> => ({
        ok: false,
        error: pathNotFound(),
      }),
    );
    const onSuccess = vi.fn();
    const { getByLabelText, getByRole, findByText, container } = render(
      <AttachRepoForm
        projectId={PROJECT_ID}
        onAttach={onAttach}
        onCancel={vi.fn()}
        onSuccess={onSuccess}
      />,
    );

    fireEvent.change(getByLabelText("Local folder path"), {
      target: { value: "~/code/sulis/apps/does-not-exist" },
    });
    fireEvent.click(getByRole("button", { name: "Attach" }));

    // Plain English, not the raw PATH_NOT_FOUND code.
    const err = await findByText(/We couldn't find that folder/i);
    expect(err).toBeInTheDocument();
    expect(err.textContent).not.toContain("PATH_NOT_FOUND");

    // A hard error does NOT fire the success/invalidation callback.
    await waitFor(() => expect(onAttach).toHaveBeenCalledTimes(1));
    expect(onSuccess).not.toHaveBeenCalled();

    expect(await axe(container)).toHaveNoViolations();
  });

  it("renders a non-PATH typed error inline using the server message", async () => {
    const onAttach = vi.fn(
      async (): Promise<Result<SettingsProject>> => ({
        ok: false,
        error: {
          code: "WRITE_FAILED",
          message: "Couldn't save that change. Try again.",
        },
      }),
    );
    const onSuccess = vi.fn();
    const { getByLabelText, getByRole, findByText } = render(
      <AttachRepoForm
        projectId={PROJECT_ID}
        onAttach={onAttach}
        onCancel={vi.fn()}
        onSuccess={onSuccess}
      />,
    );

    fireEvent.change(getByLabelText("Local folder path"), {
      target: { value: "/Users/founder/code/x" },
    });
    fireEvent.click(getByRole("button", { name: "Attach" }));

    const err = await findByText("Couldn't save that change. Try again.");
    expect(err).toBeInTheDocument();
    expect(onSuccess).not.toHaveBeenCalled();
  });

  it("non_repo_folder_attaches_with_warning_not_block", async () => {
    const onAttach = vi.fn(
      async (): Promise<Result<SettingsProject>> => ({
        ok: true,
        value: attachedNonRepo(),
      }),
    );
    const onSuccess = vi.fn();
    const { getByLabelText, getByRole, findByText } = render(
      <AttachRepoForm
        projectId={PROJECT_ID}
        onAttach={onAttach}
        onCancel={vi.fn()}
        onSuccess={onSuccess}
      />,
    );

    fireEvent.change(getByLabelText("Local folder path"), {
      target: { value: "/Users/founder/code/new-folder" },
    });
    fireEvent.click(getByRole("button", { name: "Attach" }));

    // The attach SUCCEEDED (onSuccess fired) even though it isn't a git repo…
    await waitFor(() => expect(onSuccess).toHaveBeenCalledTimes(1));

    // …and the non-blocking "not a git repo yet" note is shown (warning, not
    // an error/blocker).
    const note = await findByText(/not a git repo yet/i);
    expect(note).toBeInTheDocument();
  });
});
