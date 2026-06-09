// WP-006 — the Settings router (TDD §5.2; ADR-019). THE THIRD SANCTIONED WRITE
// SURFACE in the cockpit (after the chat relay, ADR-003, and the operator-action
// routes, ADR-015).
//
// This file is allow-listed BY PATH in the read-only gate (the vitest
// read-only-inventory.test.ts AND scripts/check-read-only.sh) because it carries
// the settings CRUD mutation verbs (`router.post` / `router.delete`). The
// load-bearing ADR-019 invariant: the router itself STARTS NO PROCESS and WRITES
// NO FILE. Every mutation delegates to the `SettingsStore` port (WP-002), whose
// sole real adapter — `SpineSettingsAdapter` (WP-005) — is the one allow-listed
// writer. No second write site is introduced here.
//
// The seven routes (TDD §5.2), each mapping 1:1 to one port method:
//   GET    /api/settings                       → readTree
//   POST   /api/settings/products              → upsertProduct   (id ⇒ edit)
//   DELETE /api/settings/products/:id          → removeProduct
//   POST   /api/settings/projects              → upsertProject   (id ⇒ edit)
//   DELETE /api/settings/projects/:id          → removeProject
//   POST   /api/settings/projects/:id/repo     → attachRepo
//   DELETE /api/settings/projects/:id/repo     → unlinkRepo
//
// Two error sources, one envelope (CF-03; the existing cockpit `ApiError`
// `{ error, code }`):
//   1. Boundary validation — input is request-controlled, so the router rejects
//      an obviously-malformed body at the edge with VALIDATION_FAILED (422)
//      BEFORE it reaches the port (the port never sees a junk body). The deeper
//      validation (id shape, path traversal, relative attach paths) stays the
//      adapter's job (WP-005) — the router does NOT duplicate or bypass it.
//   2. Typed port errors — a `SettingsStoreError`'s code maps to the documented
//      HTTP status via the single `STATUS_BY_CODE` table below (no per-route
//      duplication).

import { Router, json as jsonBody } from "express";

import {
  SettingsStoreError,
  type SettingsStore,
  type SettingsErrorCode,
  type ProductWrite,
  type ProjectWrite,
  type RepoAttachWrite,
} from "../ports/SettingsStore";

import { asyncHandler } from "./_async";

export interface SettingsRouterDeps {
  store: SettingsStore;
}

/**
 * The single error-code → HTTP-status table (CF-03). One place, no per-route
 * duplication — the Blue-refactor target the WP names. Three categories:
 *   - Protocol:  NOT_FOUND                         → 404
 *   - Expected:  VALIDATION_FAILED, PATH_NOT_A_REPO → 422 (client must fix input)
 *                PATH_NOT_FOUND                      → 404 (the named thing is absent)
 *                IMMUTABLE_IMPLICIT                  → 409 (state conflict)
 *   - Internal:  WRITE_FAILED                        → 502 (downstream write failed)
 */
const STATUS_BY_CODE: Record<SettingsErrorCode, number> = {
  NOT_FOUND: 404,
  PATH_NOT_FOUND: 404,
  VALIDATION_FAILED: 422,
  PATH_NOT_A_REPO: 422,
  IMMUTABLE_IMPLICIT: 409,
  WRITE_FAILED: 502,
};

/** Throw a router-boundary VALIDATION_FAILED — the request body is malformed
 *  enough that delegating to the port would be meaningless. Reuses the port's
 *  typed-error class so the mapping below is uniform whatever the source. */
function rejectBody(message: string): never {
  throw new SettingsStoreError("VALIDATION_FAILED", message);
}

/** A non-empty, non-blank string — the one shape every write body shares for
 *  its `name` field. (Deeper validation — id format, path safety — is the
 *  adapter's job; the router only screens out obvious junk at the edge.) */
function isNonBlankString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

/** Narrow a request body to a plain object, rejecting a non-object (null, array,
 *  string, number) at the boundary with `message`. Extracted at the 2-consumer
 *  threshold (EP-03): all three write-body validators below open with this same
 *  guard, so the narrowing lives once. */
function asObject(body: unknown, message: string): Record<string, unknown> {
  if (typeof body !== "object" || body === null || Array.isArray(body)) {
    rejectBody(message);
  }
  return body as Record<string, unknown>;
}

/** Validate + normalise a ProductWrite body. `name` required + non-blank;
 *  `productId`, when present, must be a non-blank string (absent ⇒ create). */
function parseProductWrite(body: unknown): ProductWrite {
  const b = asObject(body, "Request body must be a product object.");
  if (!isNonBlankString(b.name)) {
    rejectBody("A product needs a non-empty name.");
  }
  if (b.productId !== undefined && !isNonBlankString(b.productId)) {
    rejectBody("productId, when present, must be a non-empty string.");
  }
  const out: ProductWrite = { name: b.name.trim() };
  if (b.productId !== undefined) out.productId = b.productId;
  return out;
}

/** Validate + normalise a ProjectWrite body. `name` + `productId` required;
 *  `projectId`, when present, must be a non-blank string (absent ⇒ create). */
function parseProjectWrite(body: unknown): ProjectWrite {
  const b = asObject(body, "Request body must be a project object.");
  if (!isNonBlankString(b.name)) {
    rejectBody("A project needs a non-empty name.");
  }
  if (!isNonBlankString(b.productId)) {
    rejectBody("A project needs the productId it belongs to.");
  }
  const out: ProjectWrite = { name: b.name.trim(), productId: b.productId };
  if (b.projectId !== undefined) {
    if (!isNonBlankString(b.projectId)) {
      rejectBody("projectId, when present, must be a non-empty string.");
    }
    out.projectId = b.projectId;
  }
  return out;
}

/** The `:id` path param as a guaranteed non-blank string. Express 5 types
 *  `req.params[k]` as `string | string[] | undefined`; a missing or array-valued
 *  id is a malformed request (VALIDATION_FAILED), never a silent cast. */
function requirePathId(value: unknown): string {
  if (!isNonBlankString(value)) {
    rejectBody("This route needs a non-empty id in the path.");
  }
  return value;
}

/** Validate + normalise a RepoAttachWrite body. The path param is the
 *  authoritative projectId (a body projectId can never override the URL);
 *  `localPath` required + non-blank. Path SAFETY (traversal, relative paths)
 *  is the adapter's job (WP-005) — the router only screens out a missing path. */
function parseRepoAttachWrite(projectId: string, body: unknown): RepoAttachWrite {
  const b = asObject(body, "Request body must include a localPath.");
  if (!isNonBlankString(b.localPath)) {
    rejectBody("Attaching a repo needs a non-empty local folder path.");
  }
  return { projectId, localPath: b.localPath };
}

export function settingsRouter(deps: SettingsRouterDeps): Router {
  const router = Router();
  const { store } = deps;

  // JSON body parsing scoped to this router (read routes elsewhere never parse
  // a body). The write routes carry the validated wire shapes.
  router.use(jsonBody());

  // GET /api/settings — the whole editable tree (active entities only).
  router.get(
    "/",
    asyncHandler(async (_req, res) => {
      res.json(await store.readTree());
    }),
  );

  // POST /api/settings/products — create (no id) or edit (with id) a product.
  router.post(
    "/products",
    asyncHandler(async (req, res) => {
      res.json(await store.upsertProduct(parseProductWrite(req.body)));
    }),
  );

  // DELETE /api/settings/products/:id — soft-delete a product.
  router.delete(
    "/products/:id",
    asyncHandler(async (req, res) => {
      await store.removeProduct(requirePathId(req.params.id));
      res.json({ ok: true });
    }),
  );

  // POST /api/settings/projects — create or edit a project under a product.
  router.post(
    "/projects",
    asyncHandler(async (req, res) => {
      res.json(await store.upsertProject(parseProjectWrite(req.body)));
    }),
  );

  // DELETE /api/settings/projects/:id — soft-delete a project.
  router.delete(
    "/projects/:id",
    asyncHandler(async (req, res) => {
      await store.removeProject(requirePathId(req.params.id));
      res.json({ ok: true });
    }),
  );

  // POST /api/settings/projects/:id/repo — attach a local folder to a project.
  router.post(
    "/projects/:id/repo",
    asyncHandler(async (req, res) => {
      const input = parseRepoAttachWrite(requirePathId(req.params.id), req.body);
      res.json(await store.attachRepo(input));
    }),
  );

  // DELETE /api/settings/projects/:id/repo — clear a project's repo link.
  router.delete(
    "/projects/:id/repo",
    asyncHandler(async (req, res) => {
      res.json(await store.unlinkRepo(requirePathId(req.params.id)));
    }),
  );

  // The settings-local error mapper. A SettingsStoreError (from the boundary
  // validators OR the port) maps to its documented status in the shared
  // `ApiError` envelope via STATUS_BY_CODE. Anything else is re-thrown to the
  // app-level error middleware (which renders an honest 500). This handler is
  // scoped to the settings router so the global middleware needs no settings
  // knowledge — the mapping lives with the surface that owns the codes.
  router.use(
    (
      err: unknown,
      _req: import("express").Request,
      res: import("express").Response,
      next: import("express").NextFunction,
    ) => {
      if (err instanceof SettingsStoreError) {
        res
          .status(STATUS_BY_CODE[err.code])
          .json({ error: err.message, code: err.code });
        return;
      }
      next(err);
    },
  );

  return router;
}
