// WP-010 — Express app factory (TDD §5, §13).
//
// `createApp(deps)` returns a fully-wired Express app without binding
// a port. Tests use this directly via supertest; `index.ts` is the
// thin production wrapper that constructs the live dependencies and
// calls `app.listen(port, "127.0.0.1")`.
//
// The middleware stack (in order):
//   1. CORS — allow exactly one origin (the Vite dev client). Dev only;
//      production-bundle mode serves the client same-origin and CORS
//      is moot.
//   2. request-log — one line per request (method/path/status/duration).
//   3. Route routers — six GET endpoints.
//   4. 405 fallback — anything that isn't a registered GET returns 405.
//   5. Error middleware — translates typed errors to the JSON envelope.
//
// Read-only invariant: only `router.get` is ever called. The
// read-only-inventory.test.ts gate enforces this by grep.

import express, { type Application } from "express";
import cors from "cors";

import type { ChangeStoreReader } from "./ports/ChangeStoreReader";

import { createChangesRouter } from "./routes/changes";
import { createChangeDetailRouter } from "./routes/change-detail";
import { createTreeRouter } from "./routes/tree";
import { createFileRouter } from "./routes/file";
import { createDiffRouter } from "./routes/diff";
import { createTranscriptRouter } from "./routes/transcript";

import { errorMiddleware } from "./middleware/errors";
import { requestLogMiddleware } from "./middleware/request-log";

export interface CreateAppDeps {
  changeStore: ChangeStoreReader;
  sulisStateDir: string;
  claudeProjectsDir: string;
  /** Optional override for the 1 MiB file cap (tests + future tuning). */
  fileMaxBytes?: number;
  /** Optional override for the 5s git timeout (tests). */
  gitTimeoutMs?: number;
  /** Optional override for the CORS origin (defaults to Vite dev port). */
  clientOrigin?: string;
}

export function createApp(deps: CreateAppDeps): Application {
  const app = express();

  // 1. CORS — single allowed origin.
  app.use(
    cors({
      origin: deps.clientOrigin ?? "http://127.0.0.1:5173",
      methods: ["GET", "OPTIONS"],
    }),
  );

  // 2. Per-request logging (no bodies, no headers).
  app.use(requestLogMiddleware);

  // 3. Routes. Each router is mounted under the URL prefix and its
  //    handlers are GET-only (the read-only-inventory test enforces).
  app.use(
    "/api/changes",
    createChangesRouter({
      changeStore: deps.changeStore,
      sulisStateDir: deps.sulisStateDir,
    }),
  );

  app.use(
    "/api/changes/:id",
    createChangeDetailRouter({
      changeStore: deps.changeStore,
      sulisStateDir: deps.sulisStateDir,
      claudeProjectsDir: deps.claudeProjectsDir,
    }),
  );

  app.use(
    "/api/changes/:id/tree",
    createTreeRouter({
      changeStore: deps.changeStore,
    }),
  );

  app.use(
    "/api/changes/:id/file",
    createFileRouter({
      changeStore: deps.changeStore,
      fileMaxBytes: deps.fileMaxBytes,
    }),
  );

  app.use(
    "/api/changes/:id/diff",
    createDiffRouter({
      changeStore: deps.changeStore,
      gitTimeoutMs: deps.gitTimeoutMs,
      fileMaxBytes: deps.fileMaxBytes,
    }),
  );

  app.use(
    "/api/changes/:id/transcript",
    createTranscriptRouter({
      changeStore: deps.changeStore,
      claudeProjectsDir: deps.claudeProjectsDir,
    }),
  );

  // 4. Method + path fallback. Anything that reaches here is either:
  //   - A non-GET method on any path → 405 (the cockpit is GET-only).
  //   - A GET on an unregistered path → 404.
  // We use one app-level fallback rather than per-route handling to
  // keep the table flat.
  app.use((req, res) => {
    if (
      req.method !== "GET" &&
      req.method !== "OPTIONS" &&
      req.method !== "HEAD"
    ) {
      res.status(405).json({
        error: `method not allowed: ${req.method}`,
        code: "METHOD_NOT_ALLOWED",
      });
      return;
    }
    res.status(404).json({
      error: `not found: ${req.originalUrl}`,
      code: "NOT_FOUND",
    });
  });

  // 5. Error middleware (the typed-error → JSON envelope mapper).
  app.use(errorMiddleware);

  return app;
}
