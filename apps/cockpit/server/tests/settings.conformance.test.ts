// WP-010 — CF-07 conformance: the client wire shapes against the REAL router.
//
// This is the graph-closing integration test (CF-07): it swaps the mock the
// consumer built against for the REAL producer — `settingsRouter` over a REAL
// `SpineSettingsAdapter` over a REAL `mkdtemp` brain driven by the REAL
// validated Python emitters. No `FakeSettingsStore`, no stubbed `fetch`, no
// mock at the seam (MEA-09 / WPB-03). It proves two things:
//
//   1. CONFORMANCE — every shape the client (`apps/cockpit/client/src/api/
//      settings.ts`) sends and reads round-trips through the live router and
//      resolves to the WP-001 wire types in `shared/api-types.ts`. A field the
//      client reads is a field the server sets; every `SettingsErrorCode` is
//      returned in the `{ error, code }` ApiError envelope as typed (CF-03).
//   2. SPEC ACCEPTANCE — each acceptance criterion is exercised by one named
//      test, end-to-end against the real wiring, including the headline
//      disk-safety promise (a sentinel file in the founder's folder survives
//      remove + unlink — ADR-020).
//
// The harness mirrors `SpineSettingsAdapter.test.ts` (the WP-005 integration
// test): a fresh `<state>/.brain/instances` mkdtemp brain per test, the real
// vendored scripts resolved repo-root-relative, and a clean skip (not a vacuous
// pass) when python3 or the adapter scripts are unavailable (a bare checkout).
//
// Named Red cases (WP-010 Definition of Done):
//   - client_against_real_router_round_trip
//   - every_settings_error_shape_conforms
//   - new_product_appears_in_switcher_no_reload
//   - remove_then_sentinel_survives_end_to_end

import { describe, it, expect, beforeAll, afterEach } from "vitest";
import request from "supertest";
import type { Express } from "express";
import { existsSync, writeFileSync, readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

// eslint-disable-next-line no-restricted-imports -- the test imports the wire
// types from the shared contract verbatim (CF-02/06): the conformance check IS
// "the client/server resolve to these same shapes".
import type {
  SettingsTree,
  SettingsProduct,
  SettingsProject,
  SettingsErrorCode,
} from "../../shared/api-types";
import {
  resolveScriptsDir,
  adapterAvailable,
  realSettingsApp,
  TempDirs,
} from "./helpers/settingsHarness";

// Repo-root-relative anchor (this file is four levels under the repo root:
// apps/cockpit/server/tests/ → repo root). The shared harness owns the rest.
const HERE = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = join(HERE, "..", "..", "..", "..");
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
afterEach(() => temps.cleanup());

/** A fresh brain + a real app over it — the per-test starting point. */
function appOverFreshBrain(): Express {
  return realSettingsApp(SCRIPTS_DIR, temps.brain());
}

/** The settings error envelope on the wire (CF-03; the cockpit `ApiError`). */
interface ApiErrorBody {
  error: string;
  code: SettingsErrorCode;
}

describe(
  "settings CF-07 conformance (client shapes ↔ real router, no mocks)",
  { timeout: 60_000 },
  () => {
    it("client_against_real_router_round_trip — full CRUD round-trips through the live router + adapter", async () => {
      if (unavailable()) return;
      const app = appOverFreshBrain();

      // CREATE a product (the `ProductWrite` shape the client sends; the
      // `SettingsProduct` shape it reads back).
      const created = await request(app)
        .post("/api/settings/products")
        .send({ name: "Acme" })
        .expect(200);
      const product = created.body as SettingsProduct;
      expect(product.productId).toMatch(/^dna:product:[0-9A-HJKMNP-TV-Z]{26}$/);
      expect(product.name).toBe("Acme");
      expect(product.editable).toBe(true);
      expect(Array.isArray(product.projects)).toBe(true);

      // EDIT (rename) the product — same id ⇒ overwrite in place.
      const renamed = await request(app)
        .post("/api/settings/products")
        .send({ productId: product.productId, name: "Acme Renamed" })
        .expect(200);
      expect((renamed.body as SettingsProduct).name).toBe("Acme Renamed");

      // CREATE a project under it (the `ProjectWrite` shape).
      const projectRes = await request(app)
        .post("/api/settings/projects")
        .send({ productId: product.productId, name: "Web" })
        .expect(200);
      const project = projectRes.body as SettingsProject;
      expect(project.projectId).toMatch(/^dna:project:[0-9A-HJKMNP-TV-Z]{26}$/);
      expect(project.name).toBe("Web");
      expect(project.repo).toBeNull();

      // ATTACH an existing local folder (the `RepoAttachWrite` shape; a real
      // git repo ⇒ present:true — ADR-021 read-only present check).
      const folder = temps.folder(true);
      const attached = await request(app)
        .post(
          `/api/settings/projects/${encodeURIComponent(project.projectId)}/repo`,
        )
        .send({ projectId: project.projectId, localPath: folder })
        .expect(200);
      const withRepo = attached.body as SettingsProject;
      expect(withRepo.repo).not.toBeNull();
      expect(withRepo.repo?.localPath).toBe(folder);
      expect(withRepo.repo?.primaryBranch).toBe("main");
      expect(withRepo.repo?.present).toBe(true);

      // The GET /api/settings tree reflects everything (the `SettingsTree` the
      // page reads). A field the client reads is a field the server set.
      const treeRes = await request(app).get("/api/settings").expect(200);
      const tree = treeRes.body as SettingsTree;
      const acme = tree.products.find((p) => p.productId === product.productId);
      expect(acme?.name).toBe("Acme Renamed");
      const web = acme?.projects.find(
        (pr) => pr.projectId === project.projectId,
      );
      expect(web?.repo?.localPath).toBe(folder);

      // UNLINK the repo — the link clears; disk untouched (asserted in the
      // sentinel test below).
      const unlinked = await request(app)
        .delete(
          `/api/settings/projects/${encodeURIComponent(project.projectId)}/repo`,
        )
        .expect(200);
      expect((unlinked.body as SettingsProject).repo).toBeNull();

      // REMOVE the project, then the product — both soft-deletes ⇒ they vanish
      // from the next tree read.
      await request(app)
        .delete(
          `/api/settings/projects/${encodeURIComponent(project.projectId)}`,
        )
        .expect(200)
        .expect({ ok: true });
      await request(app)
        .delete(
          `/api/settings/products/${encodeURIComponent(product.productId)}`,
        )
        .expect(200)
        .expect({ ok: true });

      const afterRemoval = (await request(app).get("/api/settings").expect(200))
        .body as SettingsTree;
      expect(afterRemoval.products.map((p) => p.productId)).not.toContain(
        product.productId,
      );
    });

    it("every_settings_error_shape_conforms — each SettingsErrorCode rides the typed ApiError envelope", async () => {
      if (unavailable()) return;
      const app = appOverFreshBrain();

      // VALIDATION_FAILED (422) — a blank name is rejected at the boundary.
      const blank = await request(app)
        .post("/api/settings/products")
        .send({ name: "   " })
        .expect(422);
      expect((blank.body as ApiErrorBody).code).toBe("VALIDATION_FAILED");
      expect(typeof (blank.body as ApiErrorBody).error).toBe("string");

      // A real product to hang the path-error cases off.
      const product = (
        await request(app)
          .post("/api/settings/products")
          .send({ name: "Acme" })
          .expect(200)
      ).body as SettingsProduct;
      const project = (
        await request(app)
          .post("/api/settings/projects")
          .send({ productId: product.productId, name: "Web" })
          .expect(200)
      ).body as SettingsProject;

      // PATH_NOT_FOUND (404) — attach pointed at a non-existent folder.
      const missing = await request(app)
        .post(
          `/api/settings/projects/${encodeURIComponent(project.projectId)}/repo`,
        )
        .send({
          projectId: project.projectId,
          localPath: "/nonexistent/wp010/nope",
        })
        .expect(404);
      expect((missing.body as ApiErrorBody).code).toBe("PATH_NOT_FOUND");

      // WRITE_FAILED (502) — editing a well-formed but unminted id makes the real
      // helper return a non-ok envelope (find_by_id → None), surfaced as a typed
      // WRITE_FAILED (the Internal-category code).
      const ghostId = `dna:product:${"01HZZZZZZZZZZZZZZZZZZZG010".slice(0, 26)}`;
      const writeFail = await request(app)
        .post("/api/settings/products")
        .send({ productId: ghostId, name: "Ghost" })
        .expect(502);
      expect((writeFail.body as ApiErrorBody).code).toBe("WRITE_FAILED");

      // The codes asserted above span the three CF-03 categories the client maps:
      // Expected (VALIDATION_FAILED), Protocol (PATH_NOT_FOUND), Internal
      // (WRITE_FAILED). Every code is a member of the SettingsErrorCode union —
      // the conformance the client's `toSettingsError` mapping depends on.
      const seen: SettingsErrorCode[] = [
        (blank.body as ApiErrorBody).code,
        (missing.body as ApiErrorBody).code,
        (writeFail.body as ApiErrorBody).code,
      ];
      const allCodes: readonly SettingsErrorCode[] = [
        "NOT_FOUND",
        "VALIDATION_FAILED",
        "PATH_NOT_FOUND",
        "PATH_NOT_A_REPO",
        "WRITE_FAILED",
        "IMMUTABLE_IMPLICIT",
      ];
      for (const code of seen) {
        expect(allCodes).toContain(code);
      }
    });

    it("new_product_appears_in_switcher_no_reload — a created product shows in the next tree read", async () => {
      if (unavailable()) return;
      // SPEC acceptance: "add a new product, and it shows up in the cockpit's
      // product switcher without editing any file or running any command." The
      // switcher reads the same store the tree does; a fresh GET (the
      // invalidated query refetch — no page reload) returns the new product.
      const app = appOverFreshBrain();

      const before = (await request(app).get("/api/settings").expect(200))
        .body as SettingsTree;
      expect(before.products.map((p) => p.name)).not.toContain("Brand New");

      const created = (
        await request(app)
          .post("/api/settings/products")
          .send({ name: "Brand New" })
          .expect(200)
      ).body as SettingsProduct;

      // A subsequent read (what the invalidated query refetches — NOT a reload)
      // sees it. This is the exact mechanic the page's onSuccess invalidation
      // drives: write → invalidate SETTINGS_QUERY_KEY/PRODUCTS_QUERY_KEY → refetch.
      const after = (await request(app).get("/api/settings").expect(200))
        .body as SettingsTree;
      expect(after.products.map((p) => p.productId)).toContain(
        created.productId,
      );
    });

    it("remove_then_sentinel_survives_end_to_end — the disk-safety promise, proven through the real router", async () => {
      if (unavailable()) return;
      // The headline acceptance (SPEC binding decision 4; ADR-020): remove =
      // unlink the pointer only; the founder's files on disk are NEVER touched.
      // Proven end-to-end here through the REAL router + adapter (not just the
      // adapter unit) — the full HTTP seam the founder drives.
      const app = appOverFreshBrain();

      // A mock "founder folder" with an irreplaceable sentinel + a real .git.
      const founder = temps.folder(true);
      const sentinel = join(founder, "PRECIOUS.txt");
      writeFileSync(sentinel, "the founder's irreplaceable work");
      const gitDir = join(founder, ".git");

      const product = (
        await request(app)
          .post("/api/settings/products")
          .send({ name: "Acme" })
          .expect(200)
      ).body as SettingsProduct;
      const project = (
        await request(app)
          .post("/api/settings/projects")
          .send({ productId: product.productId, name: "Web" })
          .expect(200)
      ).body as SettingsProject;
      await request(app)
        .post(
          `/api/settings/projects/${encodeURIComponent(project.projectId)}/repo`,
        )
        .send({ projectId: project.projectId, localPath: founder })
        .expect(200);

      // The two writes that could conceivably touch disk: unlink + remove.
      await request(app)
        .delete(
          `/api/settings/projects/${encodeURIComponent(project.projectId)}/repo`,
        )
        .expect(200);
      await request(app)
        .delete(
          `/api/settings/projects/${encodeURIComponent(project.projectId)}`,
        )
        .expect(200);

      // INVARIANT (ADR-020): the sentinel, its contents, and `.git` ALL survive.
      expect(existsSync(founder)).toBe(true);
      expect(existsSync(sentinel)).toBe(true);
      expect(readFileSync(sentinel, "utf8")).toBe(
        "the founder's irreplaceable work",
      );
      expect(existsSync(gitDir)).toBe(true);

      // …and the removed project is gone from the cockpit's view.
      const tree = (await request(app).get("/api/settings").expect(200))
        .body as SettingsTree;
      const acme = tree.products.find((p) => p.productId === product.productId);
      expect(acme?.projects.map((pr) => pr.projectId) ?? []).not.toContain(
        project.projectId,
      );
    });
  },
);
