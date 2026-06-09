// WP-010 — <SettingsActions> unit tests (the wiring funnel, every branch).
//
// The e2e suite (Settings.e2e.test.tsx) walks four affordance branches against
// the REAL router; these unit tests cover the FULL switch — every ActiveForm
// kind the overlay renders — plus the shared invalidate-then-close contract,
// against a mocked `fetch` (fast, no python). Together they keep the wiring
// funnel fully exercised regardless of whether the real-subprocess e2e is
// skipped on a bare checkout.
//
// Each test opens a form via the matching handler, drives it to success, and
// asserts (a) the right fetcher hit the right route with the right body, and
// (b) onSuccess invalidated BOTH cache keys and closed the overlay.

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits); pages/settings/ is 4 levels deep, mirroring ProductRow.tsx / AttachRepoForm.tsx.
import type {
  SettingsProduct,
  SettingsProject,
} from "../../../../shared/api-types";
import { useSettingsActions, SettingsActionOverlay } from "./SettingsActions";

// A tiny harness component: mounts the hook, renders one trigger button per
// affordance, and renders the overlay. Each test clicks the trigger it needs.
function Harness({
  product,
  project,
}: {
  product: SettingsProduct;
  project: SettingsProject;
}) {
  const actions = useSettingsActions();
  return (
    <div>
      <button onClick={actions.handlers.onAddProduct}>t-add-product</button>
      <button onClick={() => actions.handlers.onRenameProduct(product)}>
        t-rename-product
      </button>
      <button onClick={() => actions.handlers.onRemoveProduct(product)}>
        t-remove-product
      </button>
      <button onClick={() => actions.handlers.onAddProject(product)}>
        t-add-project
      </button>
      <button
        onClick={() =>
          actions.handlers.onEditProject(project, product.productId)
        }
      >
        t-edit-project
      </button>
      <button onClick={() => actions.handlers.onAttachRepo(project)}>
        t-attach-repo
      </button>
      <button onClick={() => actions.handlers.onChangeRepo(project)}>
        t-change-repo
      </button>
      <button onClick={() => actions.handlers.onRemoveProject(project)}>
        t-remove-project
      </button>
      <SettingsActionOverlay
        active={actions.active}
        close={actions.close}
        invalidate={actions.invalidate}
      />
    </div>
  );
}

const PRODUCT: SettingsProduct = {
  productId: "dna:product:01HZ000000000000000000PROD",
  name: "Acme",
  editable: true,
  projects: [],
};
const PROJECT: SettingsProject = {
  projectId: "dna:project:01HZ000000000000000000PROJ",
  name: "Web",
  repo: null,
};

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

let invalidateSpy: ReturnType<typeof vi.fn>;

function renderHarness() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  invalidateSpy = vi.fn();
  // Spy on the shared cache invalidation so we can assert BOTH keys refresh.
  client.invalidateQueries = invalidateSpy as never;
  return render(
    <QueryClientProvider client={client}>
      <Harness product={PRODUCT} project={PROJECT} />
    </QueryClientProvider>,
  );
}

/** The fetch calls made during one interaction (url + method + parsed body). */
function fetchCalls(): Array<{ url: string; method: string; body: unknown }> {
  const mock = globalThis.fetch as unknown as ReturnType<typeof vi.fn>;
  return mock.mock.calls.map(([url, init]) => ({
    url: String(url),
    method: (init?.method ?? "GET").toUpperCase(),
    body: init?.body ? JSON.parse(init.body as string) : undefined,
  }));
}

describe("<SettingsActions> — the wiring funnel", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockReset();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders nothing when no affordance is active", () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(200, {}));
    renderHarness();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading")).not.toBeInTheDocument();
  });

  it("add-product → POST /api/settings/products (no id) then invalidate + close", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(200, { ...PRODUCT, name: "New" }),
    );
    renderHarness();
    fireEvent.click(screen.getByText("t-add-product"));

    fireEvent.change(screen.getByLabelText("Product name"), {
      target: { value: "New" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add" }));

    await waitFor(() => expect(invalidateSpy).toHaveBeenCalledTimes(2));
    const post = fetchCalls().find((c) => c.method === "POST");
    expect(post?.url).toBe("/api/settings/products");
    expect(post?.body).toEqual({ name: "New" });
    // Both cache keys refreshed (tree + product switcher).
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["settings"] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["products"] });
    // The overlay closed.
    await waitFor(() =>
      expect(screen.queryByText("Add a product")).not.toBeInTheDocument(),
    );
  });

  it("rename-product → POST with the product id, pre-filled", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(200, PRODUCT));
    renderHarness();
    fireEvent.click(screen.getByText("t-rename-product"));

    expect(screen.getByDisplayValue("Acme")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Product name"), {
      target: { value: "Acme 2" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(invalidateSpy).toHaveBeenCalledTimes(2));
    const post = fetchCalls().find((c) => c.method === "POST");
    expect(post?.body).toEqual({
      productId: PRODUCT.productId,
      name: "Acme 2",
    });
  });

  it("add-project → POST /api/settings/projects with the parent product id", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(200, PROJECT));
    renderHarness();
    fireEvent.click(screen.getByText("t-add-project"));

    fireEvent.change(screen.getByLabelText("Project name"), {
      target: { value: "Docs" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add" }));

    await waitFor(() => expect(invalidateSpy).toHaveBeenCalledTimes(2));
    const post = fetchCalls().find((c) => c.method === "POST");
    expect(post?.url).toBe("/api/settings/projects");
    expect(post?.body).toEqual({ productId: PRODUCT.productId, name: "Docs" });
  });

  it("edit-project → POST with projectId + the threaded parent productId", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(200, PROJECT));
    renderHarness();
    fireEvent.click(screen.getByText("t-edit-project"));

    expect(screen.getByDisplayValue("Web")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Project name"), {
      target: { value: "Web 2" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(invalidateSpy).toHaveBeenCalledTimes(2));
    const post = fetchCalls().find((c) => c.method === "POST");
    // The parent id is non-blank (router boundary requires it even on edit).
    expect(post?.body).toEqual({
      projectId: PROJECT.projectId,
      productId: PRODUCT.productId,
      name: "Web 2",
    });
  });

  it("attach-repo → POST /api/settings/projects/:id/repo", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(200, {
        ...PROJECT,
        repo: { localPath: "/tmp/x", primaryBranch: "main", present: true },
      }),
    );
    renderHarness();
    fireEvent.click(screen.getByText("t-attach-repo"));

    fireEvent.change(screen.getByLabelText(/local folder path/i), {
      target: { value: "/tmp/x" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Attach" }));

    await waitFor(() => expect(invalidateSpy).toHaveBeenCalledTimes(2));
    const post = fetchCalls().find((c) => c.method === "POST");
    expect(post?.url).toBe(
      `/api/settings/projects/${encodeURIComponent(PROJECT.projectId)}/repo`,
    );
    expect(post?.body).toEqual({
      projectId: PROJECT.projectId,
      localPath: "/tmp/x",
    });
  });

  it("change-repo opens the SAME attach form (attach = upsert of source)", () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(200, PROJECT));
    renderHarness();
    fireEvent.click(screen.getByText("t-change-repo"));
    expect(screen.getByText("Attach a folder")).toBeInTheDocument();
  });

  it("remove-product → DELETE /api/settings/products/:id behind the safety dialog", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(200, { ok: true }),
    );
    renderHarness();
    fireEvent.click(screen.getByText("t-remove-product"));

    // The load-bearing files-are-safe note is shown.
    expect(screen.getByText(/your files are safe/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /remove the link/i }));

    await waitFor(() => expect(invalidateSpy).toHaveBeenCalledTimes(2));
    const del = fetchCalls().find((c) => c.method === "DELETE");
    expect(del?.url).toBe(
      `/api/settings/products/${encodeURIComponent(PRODUCT.productId)}`,
    );
  });

  it("remove-project → DELETE /api/settings/projects/:id behind the safety dialog", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(200, { ok: true }),
    );
    renderHarness();
    fireEvent.click(screen.getByText("t-remove-project"));
    fireEvent.click(screen.getByRole("button", { name: /remove the link/i }));

    await waitFor(() => expect(invalidateSpy).toHaveBeenCalledTimes(2));
    const del = fetchCalls().find((c) => c.method === "DELETE");
    expect(del?.url).toBe(
      `/api/settings/projects/${encodeURIComponent(PROJECT.projectId)}`,
    );
  });

  it("Cancel closes the overlay without a fetch", () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse(200, {}));
    renderHarness();
    fireEvent.click(screen.getByText("t-add-product"));
    expect(screen.getByText("Add a product")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByText("Add a product")).not.toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
