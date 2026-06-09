// WP-006 — Settings router (TDD §5.2; ADR-019). The cockpit's THIRD sanctioned
// write surface.
//
// Drives the real `settingsRouter` through supertest (no real port bind). The
// router is the PRODUCER side of the settings seam: every route maps 1:1 to a
// `SettingsStore` port call, and every typed `SettingsStoreError` code maps to
// the right HTTP status in the existing `ApiError` envelope. The router itself
// starts no process and writes no entity — it validates the request body at the
// boundary and delegates to the port (whose sole real adapter,
// `SpineSettingsAdapter`, is the one allow-listed writer; ADR-019).
//
// Two stores back the tests:
//   - `FakeSettingsStore` (WP-002) — REAL in-memory behaviour, used for the
//     happy-path round trips (create/edit/remove/attach/unlink + readTree).
//   - `RecordingStore` / `ThrowingStore` — thin doubles that prove (a) each
//     route reaches EXACTLY the expected port method with the expected argv,
//     and (b) each typed error code maps to the documented HTTP status.

import { describe, it, expect } from "vitest";
import request from "supertest";
import express, { type Express } from "express";

import { settingsRouter } from "../routes/settings";
import { FakeSettingsStore } from "../adapters/FakeSettingsStore";
import {
  SettingsStoreError,
  type SettingsStore,
  type SettingsErrorCode,
  type SettingsTree,
  type SettingsProduct,
  type SettingsProject,
  type ProductWrite,
  type ProjectWrite,
  type RepoAttachWrite,
} from "../ports/SettingsStore";
import { errorMiddleware } from "../middleware/errors";

// ── Test app factory ─────────────────────────────────────────────────────────
// Mounts the real router under /api/settings behind the real error middleware,
// exactly as app.ts wires it — but with an injectable store so each test pins a
// precise behaviour.
function appWith(store: SettingsStore): Express {
  const app = express();
  app.use("/api/settings", settingsRouter({ store }));
  app.use(errorMiddleware);
  return app;
}

// A store that records the last call it received and returns a canned value.
// Lets a test assert "this HTTP route called EXACTLY this port method with
// EXACTLY these args" without the fake's full behaviour getting in the way.
class RecordingStore implements SettingsStore {
  calls: Array<{ method: string; arg: unknown }> = [];
  private readonly tree: SettingsTree = { products: [] };
  private readonly product: SettingsProduct = {
    productId: "p1",
    name: "Recorded",
    editable: true,
    projects: [],
  };
  private readonly project: SettingsProject = {
    projectId: "pr1",
    name: "Recorded project",
    repo: null,
  };

  async readTree(): Promise<SettingsTree> {
    this.calls.push({ method: "readTree", arg: undefined });
    return this.tree;
  }
  async upsertProduct(input: ProductWrite): Promise<SettingsProduct> {
    this.calls.push({ method: "upsertProduct", arg: input });
    return this.product;
  }
  async upsertProject(input: ProjectWrite): Promise<SettingsProject> {
    this.calls.push({ method: "upsertProject", arg: input });
    return this.project;
  }
  async removeProduct(productId: string): Promise<void> {
    this.calls.push({ method: "removeProduct", arg: productId });
  }
  async removeProject(projectId: string): Promise<void> {
    this.calls.push({ method: "removeProject", arg: projectId });
  }
  async attachRepo(input: RepoAttachWrite): Promise<SettingsProject> {
    this.calls.push({ method: "attachRepo", arg: input });
    return this.project;
  }
  async unlinkRepo(projectId: string): Promise<SettingsProject> {
    this.calls.push({ method: "unlinkRepo", arg: projectId });
    return this.project;
  }
}

// A store whose every method throws one configured typed error — used to prove
// the code → status mapping for every route uniformly.
class ThrowingStore implements SettingsStore {
  constructor(private readonly err: SettingsStoreError) {}
  private fail(): never {
    throw this.err;
  }
  async readTree(): Promise<SettingsTree> {
    return this.fail();
  }
  async upsertProduct(): Promise<SettingsProduct> {
    return this.fail();
  }
  async upsertProject(): Promise<SettingsProject> {
    return this.fail();
  }
  async removeProduct(): Promise<void> {
    return this.fail();
  }
  async removeProject(): Promise<void> {
    return this.fail();
  }
  async attachRepo(): Promise<SettingsProject> {
    return this.fail();
  }
  async unlinkRepo(): Promise<SettingsProject> {
    return this.fail();
  }
}

describe("settings router — each route maps to a port call (WP-006, TDD §5.2)", () => {
  it("each_route_maps_to_port_call_and_typed_error — GET /api/settings → readTree", async () => {
    const store = new RecordingStore();
    const res = await request(appWith(store)).get("/api/settings");
    expect(res.status).toBe(200);
    expect(store.calls).toEqual([{ method: "readTree", arg: undefined }]);
    expect(res.body).toEqual({ products: [] });
  });

  it("POST /api/settings/products → upsertProduct(body)", async () => {
    const store = new RecordingStore();
    const res = await request(appWith(store))
      .post("/api/settings/products")
      .send({ name: "Alpha" });
    expect(res.status).toBe(200);
    expect(store.calls).toEqual([
      { method: "upsertProduct", arg: { name: "Alpha" } },
    ]);
    expect(res.body).toMatchObject({ productId: "p1", name: "Recorded" });
  });

  it("POST /api/settings/products with productId → upsertProduct (edit)", async () => {
    const store = new RecordingStore();
    const res = await request(appWith(store))
      .post("/api/settings/products")
      .send({ productId: "p1", name: "Alpha v2" });
    expect(res.status).toBe(200);
    expect(store.calls).toEqual([
      { method: "upsertProduct", arg: { productId: "p1", name: "Alpha v2" } },
    ]);
  });

  it("DELETE /api/settings/products/:id → removeProduct(id) returns { ok: true }", async () => {
    const store = new RecordingStore();
    const res = await request(appWith(store)).delete(
      "/api/settings/products/abc",
    );
    expect(res.status).toBe(200);
    expect(store.calls).toEqual([{ method: "removeProduct", arg: "abc" }]);
    expect(res.body).toEqual({ ok: true });
  });

  it("POST /api/settings/projects → upsertProject(body)", async () => {
    const store = new RecordingStore();
    const res = await request(appWith(store))
      .post("/api/settings/projects")
      .send({ productId: "p1", name: "Web" });
    expect(res.status).toBe(200);
    expect(store.calls).toEqual([
      { method: "upsertProject", arg: { productId: "p1", name: "Web" } },
    ]);
  });

  it("DELETE /api/settings/projects/:id → removeProject(id) returns { ok: true }", async () => {
    const store = new RecordingStore();
    const res = await request(appWith(store)).delete(
      "/api/settings/projects/pr1",
    );
    expect(res.status).toBe(200);
    expect(store.calls).toEqual([{ method: "removeProject", arg: "pr1" }]);
    expect(res.body).toEqual({ ok: true });
  });

  it("POST /api/settings/projects/:id/repo → attachRepo({ projectId, localPath })", async () => {
    const store = new RecordingStore();
    const res = await request(appWith(store))
      .post("/api/settings/projects/pr1/repo")
      .send({ localPath: "/Users/founder/code/alpha" });
    expect(res.status).toBe(200);
    // The path param is the authoritative projectId — the router injects it so a
    // body projectId can never disagree with the URL.
    expect(store.calls).toEqual([
      {
        method: "attachRepo",
        arg: { projectId: "pr1", localPath: "/Users/founder/code/alpha" },
      },
    ]);
  });

  it("DELETE /api/settings/projects/:id/repo → unlinkRepo(id) returns the project", async () => {
    const store = new RecordingStore();
    const res = await request(appWith(store)).delete(
      "/api/settings/projects/pr1/repo",
    );
    expect(res.status).toBe(200);
    expect(store.calls).toEqual([{ method: "unlinkRepo", arg: "pr1" }]);
    expect(res.body).toMatchObject({ projectId: "pr1" });
  });
});

describe("settings router — typed error → HTTP status mapping (CF-03; ADR-019)", () => {
  // The WP Contract mapping table:
  //   VALIDATION_FAILED → 422, NOT_FOUND/PATH_NOT_FOUND → 404,
  //   PATH_NOT_A_REPO → 422 (Expected/client-error), IMMUTABLE_IMPLICIT → 409,
  //   WRITE_FAILED → 502.
  const cases: Array<{ code: SettingsErrorCode; status: number }> = [
    { code: "VALIDATION_FAILED", status: 422 },
    { code: "NOT_FOUND", status: 404 },
    { code: "PATH_NOT_FOUND", status: 404 },
    { code: "PATH_NOT_A_REPO", status: 422 },
    { code: "IMMUTABLE_IMPLICIT", status: 409 },
    { code: "WRITE_FAILED", status: 502 },
  ];

  for (const { code, status } of cases) {
    it(`${code} from the port → HTTP ${status} in the ApiError envelope`, async () => {
      const store = new ThrowingStore(
        new SettingsStoreError(code, `boom: ${code}`),
      );
      const res = await request(appWith(store))
        .post("/api/settings/products")
        .send({ name: "Alpha" });
      expect(res.status).toBe(status);
      expect(res.body).toEqual({ error: `boom: ${code}`, code });
    });
  }

  it("immutable_implicit_product_rejects_409 — editing the implicit product is a 409", async () => {
    const store = new ThrowingStore(
      new SettingsStoreError(
        "IMMUTABLE_IMPLICIT",
        "The default product can't be edited yet.",
      ),
    );
    const res = await request(appWith(store))
      .post("/api/settings/products")
      .send({ productId: "dna:product:01IMPLICITSINGLE", name: "Renamed" });
    expect(res.status).toBe(409);
    expect(res.body).toEqual({
      error: "The default product can't be edited yet.",
      code: "IMMUTABLE_IMPLICIT",
    });
  });
});

describe("settings router — boundary validation rejects malformed bodies (VALIDATION_FAILED)", () => {
  // The router rejects obviously-malformed bodies at the boundary with
  // VALIDATION_FAILED (422) and NEVER reaches the port — input is
  // request-controlled, so the router fails fast before delegating.
  it("malformed_body_rejected_with_422 — POST product with no name never calls the port", async () => {
    const store = new RecordingStore();
    const res = await request(appWith(store))
      .post("/api/settings/products")
      .send({ productId: "p1" }); // missing `name`
    expect(res.status).toBe(422);
    expect(res.body.code).toBe("VALIDATION_FAILED");
    expect(store.calls).toEqual([]); // port never reached
  });

  it("POST product with blank name → 422, port not reached", async () => {
    const store = new RecordingStore();
    const res = await request(appWith(store))
      .post("/api/settings/products")
      .send({ name: "   " });
    expect(res.status).toBe(422);
    expect(res.body.code).toBe("VALIDATION_FAILED");
    expect(store.calls).toEqual([]);
  });

  it("POST product with non-string name → 422, port not reached", async () => {
    const store = new RecordingStore();
    const res = await request(appWith(store))
      .post("/api/settings/products")
      .send({ name: 42 });
    expect(res.status).toBe(422);
    expect(res.body.code).toBe("VALIDATION_FAILED");
    expect(store.calls).toEqual([]);
  });

  it("POST product with a non-object (array) body → 422, port not reached", async () => {
    const store = new RecordingStore();
    const res = await request(appWith(store))
      .post("/api/settings/products")
      .send([{ name: "Alpha" }]); // an array is not a product object
    expect(res.status).toBe(422);
    expect(res.body.code).toBe("VALIDATION_FAILED");
    expect(store.calls).toEqual([]);
  });

  it("POST project with no productId → 422, port not reached", async () => {
    const store = new RecordingStore();
    const res = await request(appWith(store))
      .post("/api/settings/projects")
      .send({ name: "Web" }); // missing productId
    expect(res.status).toBe(422);
    expect(res.body.code).toBe("VALIDATION_FAILED");
    expect(store.calls).toEqual([]);
  });

  it("POST repo attach with no localPath → 422, port not reached", async () => {
    const store = new RecordingStore();
    const res = await request(appWith(store))
      .post("/api/settings/projects/pr1/repo")
      .send({}); // missing localPath
    expect(res.status).toBe(422);
    expect(res.body.code).toBe("VALIDATION_FAILED");
    expect(store.calls).toEqual([]);
  });
});

describe("settings router — real round trips over the FakeSettingsStore (WP-002)", () => {
  it("create product → create project → attach → readTree reflects the writes", async () => {
    const store = new FakeSettingsStore();
    const app = appWith(store);

    const created = await request(app)
      .post("/api/settings/products")
      .send({ name: "Alpha" });
    expect(created.status).toBe(200);
    const productId = created.body.productId as string;

    const proj = await request(app)
      .post("/api/settings/projects")
      .send({ productId, name: "Web" });
    expect(proj.status).toBe(200);
    const projectId = proj.body.projectId as string;

    // Attach the worktree itself (an existing folder) so the attach succeeds.
    const attach = await request(app)
      .post(`/api/settings/projects/${encodeURIComponent(projectId)}/repo`)
      .send({ localPath: process.cwd() });
    expect(attach.status).toBe(200);
    expect(attach.body.repo.localPath).toBe(process.cwd());

    const tree = await request(app).get("/api/settings");
    expect(tree.status).toBe(200);
    expect(tree.body.products).toHaveLength(1);
    expect(tree.body.products[0].name).toBe("Alpha");
    expect(tree.body.products[0].projects).toHaveLength(1);
    expect(tree.body.products[0].projects[0].repo.localPath).toBe(
      process.cwd(),
    );
  });

  it("removeProduct soft-deletes — the next readTree omits it", async () => {
    const store = new FakeSettingsStore();
    const app = appWith(store);
    const created = await request(app)
      .post("/api/settings/products")
      .send({ name: "Temp" });
    const productId = created.body.productId as string;

    const del = await request(app).delete(
      `/api/settings/products/${encodeURIComponent(productId)}`,
    );
    expect(del.status).toBe(200);
    expect(del.body).toEqual({ ok: true });

    const tree = await request(app).get("/api/settings");
    expect(tree.body.products).toEqual([]);
  });

  it("attach to a missing path → 404 PATH_NOT_FOUND (the port's typed error)", async () => {
    const store = new FakeSettingsStore();
    const app = appWith(store);
    const created = await request(app)
      .post("/api/settings/products")
      .send({ name: "Alpha" });
    const productId = created.body.productId as string;
    const proj = await request(app)
      .post("/api/settings/projects")
      .send({ productId, name: "Web" });
    const projectId = proj.body.projectId as string;

    const attach = await request(app)
      .post(`/api/settings/projects/${encodeURIComponent(projectId)}/repo`)
      .send({ localPath: "/no/such/folder/anywhere/xyzzy" });
    expect(attach.status).toBe(404);
    expect(attach.body.code).toBe("PATH_NOT_FOUND");
  });
});
