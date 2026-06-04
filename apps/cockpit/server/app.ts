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
import type { RecreateRunner } from "./ports/RecreateRunner";
import type { SessionBridge } from "./ports/SessionBridge";
import { InFlightLock } from "./lib/inFlightLock";
import { createChatRouter, type ChatLogLine } from "./routes/chat";

import { createChangesRouter } from "./routes/changes";
import { createChangeDetailRouter } from "./routes/change-detail";
import { createTreeRouter } from "./routes/tree";
import { createFileRouter } from "./routes/file";
import { createDiffRouter } from "./routes/diff";
import { createTranscriptRouter } from "./routes/transcript";
import { createContractRouter } from "./routes/contract";
import { createStatusRouter } from "./routes/status";
import { createBrainRouter } from "./routes/brain";
import { createSearchRouter } from "./routes/search";
import { createProductsRouter } from "./routes/products";

import { errorMiddleware } from "./middleware/errors";
import { requestLogMiddleware } from "./middleware/request-log";

export interface CreateAppDeps {
  changeStore: ChangeStoreReader;
  /**
   * The recreate-on-demand runner (WP-004), used by the contract-preview
   * endpoints to re-materialise a tidied shipped change's worktree before
   * serving its contracts. Optional: when absent, a present worktree still
   * serves, but a tidied one degrades to a plain "unavailable" note.
   */
  recreateRunner?: RecreateRunner;
  /**
   * WP-005 — the SessionBridge for the chat relay (ADR-002). The one new
   * write/act path. Optional: when absent, the relay route is NOT mounted and
   * chat degrades to unavailable (read surfaces unaffected — the rollback
   * shape). Production wires `StreamJsonSessionBridge`; tests inject a
   * recorded/programmable bridge.
   */
  sessionBridge?: SessionBridge;
  /**
   * WP-005 — where the relay's one-structured-line-per-send log goes
   * (NFR-SEC-03: never the body or reply). Defaults to a no-op; tests capture
   * it. Production points it at the request-log discipline.
   */
  chatLogSink?: (line: ChatLogLine) => void;
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

  // 1. CORS — single allowed origin. POST is allowed for the ONE sanctioned
  //    write path (the chat relay, ADR-001/003); every other route is GET-only
  //    and the read-only gate proves no other mutation verb exists.
  app.use(
    cors({
      origin: deps.clientOrigin ?? "http://127.0.0.1:5173",
      methods: ["GET", "POST", "OPTIONS"],
    }),
  );

  // 2. Per-request logging (no bodies, no headers).
  app.use(requestLogMiddleware);

  // WP-005 — JSON body parsing for the relay's prompt payload. Scoped to the
  // chat route only (mounted with the parser) so read routes never parse a
  // body. The chat relay is the single sanctioned write path (ADR-003); it is
  // mounted only when a SessionBridge is provided (else chat degrades to
  // unavailable — the rollback shape; read surfaces unaffected).
  if (deps.sessionBridge) {
    const inFlightLock = new InFlightLock();
    // Mounted at the LITERAL `/api/changes` prefix (not a parametric mount):
    // the router matches `/:id/chat` internally. A parametric `app.use` mount
    // (`/api/changes/:id/chat`) mis-matches a POST over a real HTTP socket
    // under Express 5 / path-to-regexp v8 (supertest's in-process inject
    // tolerated it; a live server returned 405). The literal-prefix mount is
    // the same shape the GET `changes` router uses and is unambiguous.
    app.use(
      "/api/changes",
      createChatRouter({
        changeStore: deps.changeStore,
        sessionBridge: deps.sessionBridge,
        inFlightLock,
        chatLogSink: deps.chatLogSink,
      }),
    );
  }

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

  // WP-003 — contract-preview endpoints. GET-only; serves the rendered
  // CONTRACT.html + UI.html from the change's worktree, recreating a tidied
  // worktree on demand via the injected RecreateRunner (ADR-001/003/004).
  app.use(
    "/api/changes/:id/contract",
    createContractRouter({
      changeStore: deps.changeStore,
      recreateRunner: deps.recreateRunner,
    }),
  );

  // WP-004 — read-time status endpoint (FR-04/05/12). GET-only; computes
  // the plain-English status + needs-attention flag on each read from the
  // record + transcript + liveness + open-BLOCKER signal (never a stored
  // periodic post). Composes existing reads — no new port.
  app.use(
    "/api/changes/:id/status",
    createStatusRouter({
      changeStore: deps.changeStore,
      sulisStateDir: deps.sulisStateDir,
      claudeProjectsDir: deps.claudeProjectsDir,
    }),
  );

  // WP-006 — read-time brain view (FR-06/07). GET-only; reads the change
  // worktree's `.brain/instances` tree, groups entities by kind (empty
  // groups omitted), and returns a BrainView. Composes existing reads —
  // no new port; reading it starts no `claude` process (FR-N4).
  app.use(
    "/api/changes/:id/brain",
    createBrainRouter({
      changeStore: deps.changeStore,
    }),
  );

  // WP-007 — search + filter (FR-10/11/12). GET-only; searches the active
  // Product's change CONTENT (conversation + created entities — not just
  // labels), filters by stage and needs-attention, and returns the same
  // row shape as the board list (`{ results: Change[] }`). All filters
  // narrow the SAME board (ADR-005). Composes existing reads — no new
  // port; reading it starts no `claude` process (FR-N4).
  app.use(
    "/api/search",
    createSearchRouter({
      changeStore: deps.changeStore,
      sulisStateDir: deps.sulisStateDir,
      claudeProjectsDir: deps.claudeProjectsDir,
    }),
  );

  // WP-008 — multi-product list + switch (FR-38, ADR-009). GET-only; lists
  // the Tenant's Products with the active one marked (single-Product Tenant
  // = the trivial case, one Product shown active). The active Product is the
  // optional `?product=<id>` value — the stateless all-GET scope variant
  // (ADR-009), so there is NO POST /api/products/active and the read-only
  // gate needs no scope-selection classification.
  app.use(
    "/api/products",
    createProductsRouter({
      changeStore: deps.changeStore,
      sulisStateDir: deps.sulisStateDir,
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
