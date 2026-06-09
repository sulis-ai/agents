// WP-010 — end-to-end: the real SettingsPage against the real router (CF-07).
//
// Lives under `client/src/tests/` (not colocated at `pages/settings/`) because
// it cold-starts python subprocesses (`execFileSync`) and seeds temp files
// (`writeFileSync`): the read-only gate (scripts/check-read-only.sh, ADR-003)
// excludes `**/tests/**` as test fixtures, exactly where the cockpit's other
// real-subprocess client tests live. The pure-mock wiring unit test stays
// colocated at `pages/settings/SettingsActions.test.tsx`.
//
// This is the consumer half of the graph-closing integration. It mounts the
// REAL <SettingsPage> (WP-008) with the REAL WP-009 forms/dialog WIRED IN
// (the wiring this WP adds), backed by the REAL typed client fetcher (WP-007),
// and drives `fetch` through to the REAL `settingsRouter` over a REAL
// `SpineSettingsAdapter` over a REAL `mkdtemp` brain — NO mock at the seam.
//
// `global.fetch` is replaced by a thin proxy that forwards the funnel's
// requests (api/client.ts) to the live router via supertest. That is the only
// substitution, and it is transport-only: every byte the client sends is what
// the real server parses, and every byte it reads back is what the real adapter
// produced. The journey walked is the SPEC's headline acceptance:
//
//   add product → it appears in the tree (no reload — the invalidated query
//   refetches) → add a project → attach a local folder → rename → remove →
//   a sentinel file in the founder's folder survives (disk-safety, ADR-020).
//
// The wiring assertions this file pins (the open seam WP-010 closes):
//   - clicking "Add product" opens WP-009's <EntityForm>, and a successful
//     submit makes the new product appear in the tree WITHOUT a manual reload
//     (onSuccess invalidates SETTINGS_QUERY_KEY → the tree refetches);
//   - clicking "Rename" opens the edit form pre-filled and persists the rename;
//   - clicking "Attach a folder" opens <AttachRepoForm> and attaches a real
//     local folder (present:true for a git repo);
//   - clicking product "Remove" opens <ConfirmRemoveDialog> (the files-are-safe
//     note), and confirming removes the product from the tree while the
//     founder's sentinel file stays on disk.
//
// Clicks use `fireEvent` (the cockpit client-test convention; cf.
// EntityForm.test.tsx) — not `user-event`, which the workspace doesn't vendor.
// Skips cleanly (not vacuously) when python3 or the vendored adapter scripts
// are unavailable (a bare checkout), matching the server conformance test.

import { describe, it, expect, beforeAll, afterEach, vi } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  within,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { existsSync, writeFileSync, readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import request from "supertest";
import type { Express } from "express";

import { SettingsPage } from "../pages/SettingsPage";
import {
  resolveScriptsDir,
  adapterAvailable,
  realSettingsApp,
  realAdapter,
  TempDirs,
} from "../../../server/tests/helpers/settingsHarness";

// Repo-root-relative anchor (this file is five levels under the repo root:
// apps/cockpit/client/src/tests/ → repo root). The shared harness owns the rest.
const HERE = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = join(HERE, "..", "..", "..", "..", "..");
const SCRIPTS_DIR = resolveScriptsDir(REPO_ROOT);

let available = false;
beforeAll(() => {
  available = adapterAvailable(SCRIPTS_DIR);
});

function unavailable(): boolean {
  if (!available) {
    // eslint-disable-next-line no-console
    console.warn(
      "skipping: python3 or the vendored adapter scripts unavailable",
    );
    return true;
  }
  return false;
}

const temps = new TempDirs();
afterEach(() => {
  temps.cleanup();
  vi.restoreAllMocks();
});

/** A real app over a fresh throwaway brain (the per-test starting point). */
function realApp(base: string): Express {
  return realSettingsApp(SCRIPTS_DIR, base);
}

/**
 * Install a `global.fetch` that forwards the client funnel's request to the
 * real Express app via supertest. Transport-only substitution: the URL, verb,
 * and JSON body the client builds are replayed verbatim against the live
 * router, and its real response (status + JSON) is handed back as a `Response`.
 */
function proxyFetchTo(app: Express): void {
  vi.spyOn(globalThis, "fetch").mockImplementation((async (
    input: RequestInfo | URL,
    init?: RequestInit,
  ) => {
    const url = typeof input === "string" ? input : input.toString();
    const method = (init?.method ?? "GET").toUpperCase();
    const path = url.replace(/^https?:\/\/[^/]+/, ""); // strip any origin

    const agent = request(app);
    let req = agent[method.toLowerCase() as "get" | "post" | "delete"](path);
    if (init?.body != null) {
      req = req
        .set("content-type", "application/json")
        .send(JSON.parse(init.body as string));
    }
    const res = await req;
    return new Response(JSON.stringify(res.body), {
      status: res.status,
      headers: { "content-type": "application/json" },
    });
  }) as typeof fetch);
}

// Each write drives a REAL python emitter subprocess (mint/edit/set-status/
// list), then the invalidated query refetches through another real `list`
// subprocess before the tree re-renders. Under the forked test pool that
// round-trip routinely exceeds Testing-Library's 1000ms `findBy`/`waitFor`
// default, so every assertion that waits on a write→refetch is given a
// generous budget (the work itself is still bounded by the adapter's execFile
// timeouts; a true hang fails fast at the describe-level 60s cap). This mirrors
// the WP-005 adapter test's per-suite budget for the same real-subprocess work.
const ROUND_TRIP = { timeout: 30_000 } as const;

function freshClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, refetchOnWindowFocus: false, staleTime: 0 },
    },
  });
}

function renderPage() {
  return render(
    <QueryClientProvider client={freshClient()}>
      <MemoryRouter initialEntries={["/settings"]}>
        <SettingsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe(
  "<SettingsPage> end-to-end against the real router (no mocks at the seam)",
  { timeout: 60_000 },
  () => {
    it("add_product_appears_in_tree_no_reload — Add product opens the form; a saved product shows without a reload", async () => {
      if (unavailable()) return;
      proxyFetchTo(realApp(temps.brain()));
      renderPage();

      // Empty store → first-run affordance (waits on the initial GET, a real
      // `list` subprocess on an empty brain — budgeted like every round-trip).
      const addFirst = await screen.findByRole(
        "button",
        { name: /add your first product/i },
        ROUND_TRIP,
      );
      fireEvent.click(addFirst);

      // WP-009's <EntityForm> opens (a real labelled field, not a placeholder).
      const nameField = await screen.findByLabelText("Product name");
      fireEvent.change(nameField, { target: { value: "Acme" } });
      fireEvent.click(screen.getByRole("button", { name: "Add" }));

      // The new product appears in the tree WITHOUT a manual reload — the
      // onSuccess invalidation refetched SETTINGS_QUERY_KEY.
      expect(
        await screen.findByText("Acme", {}, ROUND_TRIP),
      ).toBeInTheDocument();
      // And the edit affordances are present (it is an editable real product).
      expect(
        await screen.findByRole("button", { name: /rename/i }, ROUND_TRIP),
      ).toBeInTheDocument();
    });

    it("rename_product_persists — Rename opens a pre-filled form and the new name shows", async () => {
      if (unavailable()) return;
      const base = temps.brain();
      // Seed a product through the real adapter so the page starts non-empty.
      const seedAdapter = realAdapter(SCRIPTS_DIR, base);
      await seedAdapter.upsertProduct({ name: "Old Name" });

      proxyFetchTo(realApp(base));
      renderPage();

      expect(
        await screen.findByText("Old Name", {}, ROUND_TRIP),
      ).toBeInTheDocument();
      fireEvent.click(screen.getByRole("button", { name: /rename/i }));

      const field = await screen.findByDisplayValue("Old Name");
      fireEvent.change(field, { target: { value: "New Name" } });
      fireEvent.click(screen.getByRole("button", { name: "Save" }));

      expect(
        await screen.findByText("New Name", {}, ROUND_TRIP),
      ).toBeInTheDocument();
      await waitFor(
        () => expect(screen.queryByText("Old Name")).not.toBeInTheDocument(),
        ROUND_TRIP,
      );
    });

    it("attach_folder_shows_repo_state — Attach a folder opens the form and the repo state updates", async () => {
      if (unavailable()) return;
      const base = temps.brain();
      const seed = realAdapter(SCRIPTS_DIR, base);
      const product = await seed.upsertProduct({ name: "Acme" });
      await seed.upsertProject({ productId: product.productId, name: "Web" });

      proxyFetchTo(realApp(base));
      renderPage();

      // The project starts unlinked → "No folder attached" + an Attach CTA.
      expect(
        await screen.findByText("No folder attached", {}, ROUND_TRIP),
      ).toBeInTheDocument();
      fireEvent.click(screen.getByRole("button", { name: /attach a folder/i }));

      const folder = temps.folder(true); // a real git repo → present:true
      const pathField = await screen.findByLabelText(/local folder path/i);
      fireEvent.change(pathField, { target: { value: folder } });
      fireEvent.click(screen.getByRole("button", { name: "Attach" }));

      // The repo line refreshes to the attached state (present:true → "Git repo").
      expect(
        await screen.findByText("Git repo", {}, ROUND_TRIP),
      ).toBeInTheDocument();
    });

    it("remove_product_then_sentinel_survives_end_to_end — confirm-remove deletes the link; the founder's file stays", async () => {
      if (unavailable()) return;
      const base = temps.brain();
      const seed = realAdapter(SCRIPTS_DIR, base);
      const product = await seed.upsertProduct({ name: "Acme" });
      const project = await seed.upsertProject({
        productId: product.productId,
        name: "Web",
      });

      // A founder folder with an irreplaceable sentinel + a real .git.
      const founder = temps.folder(true);
      const sentinel = join(founder, "PRECIOUS.txt");
      writeFileSync(sentinel, "the founder's irreplaceable work");
      await seed.attachRepo({
        projectId: project.projectId,
        localPath: founder,
      });

      proxyFetchTo(realApp(base));
      renderPage();

      expect(
        await screen.findByText("Acme", {}, ROUND_TRIP),
      ).toBeInTheDocument();
      fireEvent.click(screen.getByRole("button", { name: /remove .?Acme.?/i }));

      // WP-009's <ConfirmRemoveDialog> opens with the load-bearing safety note.
      const dialog = await screen.findByRole("dialog");
      expect(
        within(dialog).getByText(/your files are safe/i),
      ).toBeInTheDocument();
      fireEvent.click(
        within(dialog).getByRole("button", { name: /remove the link/i }),
      );

      // The product vanishes from the tree (soft-delete → invalidated refetch).
      await waitFor(
        () => expect(screen.queryByText("Acme")).not.toBeInTheDocument(),
        ROUND_TRIP,
      );

      // INVARIANT (ADR-020): the founder's sentinel + .git survive on disk.
      expect(existsSync(sentinel)).toBe(true);
      expect(readFileSync(sentinel, "utf8")).toBe(
        "the founder's irreplaceable work",
      );
      expect(existsSync(join(founder, ".git"))).toBe(true);
    });
  },
);
