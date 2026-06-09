// WP-008 — <SettingsPage> tests (the read surface; RED first).
//
// The Settings screen renders the master tree Products → Projects → Repo to the
// signed WP-VIS mockup: the three repo-state pills (Git repo / Not a git repo
// yet / No folder attached), the empty/implicit first-run read-only state, and
// carried-over products rendering editable. Plus the one async state-pattern
// set (loading / error+retry / empty — ADR-005, WPF-05).
//
// Data is fetched through the typed client (getSettings → apiGet funnel) —
// never `fetch` in the component (WPF-02). The test drives the real fetcher +
// useSettings hook against mocked global fetch, the substrate every client
// test uses (mirrors Board.test.tsx). A11y is gated by jest-axe (WPF-06): the
// three pills carry a text label, never colour alone (WCAG 1.4.1).

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { axe } from "jest-axe";
import type {
  SettingsTree,
  SettingsProduct,
  SettingsProject,
} from "../../../shared/api-types";
import { SettingsPage } from "./SettingsPage";

function project(overrides: Partial<SettingsProject> = {}): SettingsProject {
  return {
    projectId: "pr-1",
    name: "cockpit-app",
    repo: {
      localPath: "~/code/sulis/apps/cockpit",
      primaryBranch: "main",
      present: true,
    },
    ...overrides,
  };
}

function product(overrides: Partial<SettingsProduct> = {}): SettingsProduct {
  return {
    productId: "pd-1",
    name: "Sulis Cockpit",
    editable: true,
    projects: [project()],
    ...overrides,
  };
}

function freshClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, refetchOnWindowFocus: false, staleTime: 0 },
    },
  });
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function renderPage(tree?: SettingsTree) {
  if (tree !== undefined) {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(200, tree));
  }
  return render(
    <QueryClientProvider client={freshClient()}>
      <MemoryRouter initialEntries={["/settings"]}>
        <SettingsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("<SettingsPage>", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockReset();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders_three_repo_state_pills_axe_clean", async () => {
    // A product whose three projects exercise the three repo states:
    //   present:true  → "Git repo"
    //   present:false → "Not a git repo yet" (warning, non-blocking — ADR-021)
    //   repo:null     → "No folder attached" (neutral)
    const tree: SettingsTree = {
      products: [
        product({
          projects: [
            project({ projectId: "pr-ok", name: "cockpit-app" }),
            project({
              projectId: "pr-warn",
              name: "design-tokens",
              repo: {
                localPath: "~/code/sulis/studios/product/design",
                primaryBranch: "main",
                present: false,
              },
            }),
            project({ projectId: "pr-none", name: "cockpit-docs", repo: null }),
          ],
        }),
      ],
    };
    const { findByText, getByText, container } = renderPage(tree);

    // Each pill appears with its TEXT label (never colour alone, WCAG 1.4.1).
    expect(await findByText("Git repo")).toBeInTheDocument();
    expect(getByText("Not a git repo yet")).toBeInTheDocument();
    expect(getByText("No folder attached")).toBeInTheDocument();

    // jest-axe clean (WPF-06).
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("implicit_product_is_read_only_with_add_first", async () => {
    // The synthesised single product is read-only (editable:false): no Rename/
    // Remove affordances, and the prominent "Add your first product" first-run
    // affordance is shown (IMMUTABLE_IMPLICIT).
    const tree: SettingsTree = {
      products: [
        product({
          productId: "pd-implicit",
          name: "My products",
          editable: false,
          projects: [],
        }),
      ],
    };
    const { findByRole, queryByRole } = renderPage(tree);

    expect(
      await findByRole("button", { name: /add your first product/i }),
    ).toBeInTheDocument();
    // No edit affordances on the read-only implicit product.
    expect(
      queryByRole("button", { name: /^rename$/i }),
    ).not.toBeInTheDocument();
    expect(
      queryByRole("button", { name: /^remove$/i }),
    ).not.toBeInTheDocument();
  });

  it("carryover_product_renders_editable", async () => {
    // An existing ("carry-over") product renders in the same tree, editable:
    // its Rename + Remove affordances are present (SPEC acceptance).
    const tree: SettingsTree = {
      products: [
        product({
          productId: "pd-carry",
          name: "Investor Coach",
          editable: true,
          projects: [
            project({
              projectId: "pr-carry",
              name: "investor-coach-plugin",
            }),
          ],
        }),
      ],
    };
    const { findByText, getByRole } = renderPage(tree);

    expect(await findByText("Investor Coach")).toBeInTheDocument();
    expect(getByRole("button", { name: /rename/i })).toBeInTheDocument();
    // The product-level Remove affordance is present on an editable product.
    expect(
      getByRole("button", { name: /remove “?Investor Coach”?/i }),
    ).toBeInTheDocument();
  });

  it("renders a loading state while the tree is in flight (ADR-005, WPF-05)", () => {
    vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise(() => {}));
    const { getByTestId } = renderPage();
    expect(getByTestId("settings-loading")).toBeInTheDocument();
  });

  it("renders an error message + retry on a transport failure (ADR-005 error+retry)", async () => {
    // A genuine TRANSPORT failure (the fetcher rethrows a non-ApiError) drives
    // the query's isError branch — the page's generic retry state (WP-007).
    vi.spyOn(globalThis, "fetch").mockRejectedValue(
      new TypeError("network down"),
    );
    const { findByText, getByRole } = renderPage();
    await findByText(/something went wrong/i);
    expect(getByRole("button", { name: /retry/i })).toBeInTheDocument();
  });

  it("renders the empty first-run state when the store has zero products (WPF-05)", async () => {
    const { findByRole } = renderPage({ products: [] });
    expect(
      await findByRole("button", { name: /add your first product/i }),
    ).toBeInTheDocument();
  });
});
