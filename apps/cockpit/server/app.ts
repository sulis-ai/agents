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

import { homedir } from "node:os";
import { join } from "node:path";

import express, { type Application } from "express";
import cors from "cors";

import type { ChangeStoreReader } from "./ports/ChangeStoreReader";
import type { RecreateRunner } from "./ports/RecreateRunner";
import type { SessionBridge } from "./ports/SessionBridge";
import { InFlightLock } from "./lib/inFlightLock";
import {
  createChatRouter,
  createConciergeRouter,
  createOnboardingRouter,
  createStartChangeRouter,
  type ChatLogLine,
  type ConciergeLogLine,
  type OnboardingLogLine,
  type StartChangeLogLine,
} from "./routes/chat";
import { LocalTranscriptConversationIdentity } from "./adapters/LocalTranscriptConversationIdentity";
import type { SpineMinter } from "./ports/SpineMinter";
import {
  SpineEmitterMinter,
  resolveEmitterScriptsDir,
} from "./adapters/SpineEmitterMinter";
import type { StartChangeRunner } from "./ports/StartChangeRunner";
import {
  SulisChangeStarter,
  resolveSulisChangeScript,
} from "./adapters/SulisChangeStarter";
import type { ResolvedProject } from "./lib/discovery/startFromIntent";
import { resolveProjectRepo } from "./lib/products/resolveProjectRepo";

import { createChangesRouter } from "./routes/changes";
import { createChangeDetailRouter } from "./routes/change-detail";
import { createTreeRouter } from "./routes/tree";
import { createFileRouter } from "./routes/file";
import { createDiffRouter } from "./routes/diff";
import { createChangedRouter } from "./routes/changed";
import { createProvenanceRouter } from "./routes/provenance";
import { createOriginRouter } from "./routes/origin";
import { createTranscriptRouter } from "./routes/transcript";
import { createTurnSummariesRouter } from "./routes/turnSummaries";
import { createAdvancedRouter } from "./routes/advanced";
import { createContractRouter } from "./routes/contract";
import { createStatusRouter } from "./routes/status";
import { createBrainRouter } from "./routes/brain";
import { createSearchRouter } from "./routes/search";
import { createProductsRouter } from "./routes/products";
import { settingsRouter } from "./routes/settings";
import type { SettingsStore } from "./ports/SettingsStore";
import { SpineSettingsAdapter } from "./adapters/SpineSettingsAdapter";
import { resolvePluginScriptsDir } from "./adapters/resolvePluginScripts";

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
  /**
   * WP-009 — where the concierge query's one-structured-line-per-query log goes
   * (NFR-SEC-03: never the question or reply). Defaults to a no-op; tests
   * capture it. The concierge rides the SAME bridge as the chat (ADR-006).
   */
  conciergeLogSink?: (line: ConciergeLogLine) => void;
  /**
   * WP-010 — the permitted search root for cold-start onboarding (FR-N7): the
   * chosen area MUST be inside it; discovery never roams to a parent / sibling /
   * the whole disk (NFR-DISC-01). Defaults to the founder's home directory.
   */
  onboardingPermittedRoot?: string;
  /**
   * WP-010 (fix-forward) — the deterministic server-side mint + repo
   * find-or-create (ADR-007 amended). Production defaults to the real
   * `SpineEmitterMinter` (invokes the validated spine emitters + `git init`
   * directly); tests inject a fake to exercise success / all-or-nothing
   * (FR-N11) / idempotency (FR-31) without a live agent.
   */
  onboardingSpineMinter?: SpineMinter;
  /**
   * WP-010 — where the onboarding one-structured-line-per-act log goes
   * (NFR-SEC-03: never the chosen area, prompt, or reply). Defaults to no-op.
   */
  onboardingLogSink?: (line: OnboardingLogLine) => void;
  /**
   * WP-011 (fix-forward applied) — the deterministic server-side change-start
   * (ADR-007). Production defaults to the real `SulisChangeStarter` (execFiles
   * `sulis-change start` + `git clone` directly — the WP-010 lesson: never
   * delegate the act to the bridge agent). Tests inject a fake to exercise
   * propose/confirm/clone/all-or-nothing without a real `sulis-change`.
   */
  startChangeRunner?: StartChangeRunner;
  /**
   * WP-011 — resolve a productId → its Project repo (FR-29). Production reads
   * the brain's Project entities (`resolveProjectRepo`); tests inject a seam so
   * the integration test needs no on-disk brain.
   */
  startResolveProject?: (productId: string) => Promise<ResolvedProject | null>;
  /**
   * WP-011 — where the start-from-intent one-line-per-act log goes (NFR-SEC-03:
   * never the intent text). Defaults to no-op.
   */
  startChangeLogSink?: (line: StartChangeLogLine) => void;
  /**
   * WP-006 (ADR-019) — the SettingsStore the Settings router (the THIRD
   * sanctioned write surface) delegates to. Production defaults to the real
   * `SpineSettingsAdapter` (the one allow-listed writer — it execFiles the
   * validated python helpers; the router itself starts no process and writes no
   * file). Tests inject a `FakeSettingsStore` to exercise the routes without
   * shelling out. The router is ALWAYS mounted (settings is a first-class
   * surface, not bridge-gated like chat) — when no store is injected the real
   * adapter is constructed from `sulisStateDir`.
   */
  settingsStore?: SettingsStore;
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

  // 1. CORS — single allowed origin. POST is allowed for the sanctioned write
  //    paths (the chat relay, ADR-001/003; the operator-action routes, ADR-015;
  //    the settings router, WP-006/ADR-019). DELETE is allowed for the settings
  //    CRUD removes (ADR-019). Every OTHER route is GET-only and the read-only
  //    gate proves no other mutation verb exists.
  app.use(
    cors({
      origin: deps.clientOrigin ?? "http://127.0.0.1:5173",
      methods: ["GET", "POST", "DELETE", "OPTIONS"],
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
        // WP-004 — the conversation-identity seam (ADR-018). The single
        // sanctioned composition site wires the ONLY adapter this change ships,
        // `LocalTranscriptConversationIdentity` (derives the assisted Thread id +
        // Message ordinal locally, read-only — no cross-service call). A live
        // service adapter swaps in behind the same port later with no route
        // change. `claudeProjectsDir` lets the relay read the resolved session's
        // transcript (read-only) to count the Message ordinal.
        conversationIdentity: new LocalTranscriptConversationIdentity(),
        claudeProjectsDir: deps.claudeProjectsDir,
        chatLogSink: deps.chatLogSink,
      }),
    );

    // WP-009 — the concierge query route (FR-33/34/N8/N9; ADR-006). Read-only:
    // it rides the SAME bridge, registered in the SAME sanctioned relay file
    // (routes/chat.ts) so no NEW file gains a write verb. Mounted only when a
    // bridge is wired (else the concierge degrades to unavailable — the
    // rollback shape; read surfaces unaffected).
    app.use(
      "/api/concierge",
      createConciergeRouter({
        changeStore: deps.changeStore,
        sessionBridge: deps.sessionBridge,
        conciergeLogSink: deps.conciergeLogSink,
      }),
    );

    // WP-010 — the cold-start onboarding route (ADR-007 amended/008). The SECOND
    // confirm-gated ACT path, registered in the SAME sanctioned relay file
    // (routes/chat.ts) so no NEW file gains a write verb (ADR-006). It rides the
    // SAME bridge (FR-27) for the CONVERSATION; the MINT + `git init` are
    // deterministic server actions behind the SpineMinter port (production
    // defaults to the real SpineEmitterMinter — the one sanctioned emitter-
    // invocation site). Mounted only when a bridge is wired (else onboarding
    // degrades to unavailable — read surfaces unaffected).
    app.use(
      "/api/onboarding",
      createOnboardingRouter({
        sessionBridge: deps.sessionBridge,
        spineMinter:
          deps.onboardingSpineMinter ??
          new SpineEmitterMinter({
            scriptsDir: resolveEmitterScriptsDir(),
            sulisStateDir: deps.sulisStateDir,
          }),
        sulisStateDir: deps.sulisStateDir,
        permittedRoot: deps.onboardingPermittedRoot ?? homedir(),
        ...(deps.onboardingLogSink
          ? { onboardingLogSink: deps.onboardingLogSink }
          : {}),
      }),
    );

    // WP-011 — the start-from-intent route (ADR-006/007). The THIRD confirm-
    // gated ACT path, registered in the SAME sanctioned relay file
    // (routes/chat.ts) so no NEW file gains a write verb. The classify is a
    // deterministic server step; the change-start is a deterministic SERVER
    // action behind the StartChangeRunner port (production defaults to the real
    // SulisChangeStarter — execFiles `sulis-change start` + `git clone`, the
    // WP-010 lesson applied). Mounted at the LITERAL `/api/changes` prefix (the
    // router matches `/start-from-intent` internally — a parametric mount
    // mis-matches a POST over a real socket, the chat-relay lesson). Mounted
    // only when a bridge is wired (else start-from-intent degrades to
    // unavailable — read surfaces unaffected).
    app.use(
      "/api/changes",
      createStartChangeRouter({
        sessionBridge: deps.sessionBridge,
        startChangeRunner:
          deps.startChangeRunner ??
          new SulisChangeStarter({
            scriptPath: resolveSulisChangeScript(),
            sulisStateDir: deps.sulisStateDir,
          }),
        resolveProject:
          deps.startResolveProject ??
          ((productId: string) =>
            resolveProjectRepo({ sulisStateDir: deps.sulisStateDir, productId })),
        ...(deps.startChangeLogSink
          ? { startChangeLogSink: deps.startChangeLogSink }
          : {}),
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
      claudeProjectsDir: deps.claudeProjectsDir,
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

  // Files redesign — the change's changed-files set (base → worktree) for
  // the repo-browser's All-files ↔ Changed scope + worded status badges.
  // GET-only; read-only (composes the sanctioned `git diff` boundary).
  app.use(
    "/api/changes/:id/changed",
    createChangedRouter({
      changeStore: deps.changeStore,
      gitTimeoutMs: deps.gitTimeoutMs,
    }),
  );

  // Provenance — read projection over the change's brain (digest + run-log +
  // coverage map; `?focus=<reqId>` for one requirement's trace). GET-only.
  app.use(
    "/api/changes/:id/provenance",
    createProvenanceRouter({
      changeStore: deps.changeStore,
    }),
  );

  // WP-P08/P09 — change-origin (inferred). Per-file likely origin (autonomous /
  // assisted / unknown) with the honest `attribution:"inferred"` flag; `?path=`
  // for one file. GET-only; the only git is the sanctioned `git log` boundary,
  // reached THROUGH the InferredOriginAttribution adapter (ADR-012).
  app.use(
    "/api/changes/:id/origin",
    createOriginRouter({
      changeStore: deps.changeStore,
      claudeProjectsDir: deps.claudeProjectsDir,
      ...(deps.gitTimeoutMs !== undefined
        ? { gitTimeoutMs: deps.gitTimeoutMs }
        : {}),
    }),
  );

  app.use(
    "/api/changes/:id/transcript",
    createTranscriptRouter({
      changeStore: deps.changeStore,
      claudeProjectsDir: deps.claudeProjectsDir,
    }),
  );

  // chat-B2 — per-turn 2–3 sentence summaries (Haiku, cached, non-blocking).
  app.use(
    "/api/changes/:id/turn-summaries",
    createTurnSummariesRouter({
      changeStore: deps.changeStore,
      claudeProjectsDir: deps.claudeProjectsDir,
    }),
  );

  // Advanced (operator) view — branch link, linked processes, reveal + stop.
  app.use(
    "/api/changes/:id",
    createAdvancedRouter({ changeStore: deps.changeStore }),
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

  // WP-006 — the Settings management surface (FR settings; ADR-019/020/021). THE
  // THIRD SANCTIONED WRITE SURFACE: the only place outside the chat relay +
  // operator-action routes that carries mutation verbs. Every mutation delegates
  // to the SettingsStore port, whose sole real adapter (SpineSettingsAdapter) is
  // the one allow-listed writer; the router itself starts no process and writes
  // no file (the read-only gate proves it). Always mounted (a first-class
  // surface, not bridge-gated): when no store is injected, the real adapter is
  // built from `sulisStateDir` (its `_entity_adapter_local.py` resolved from the
  // installed plugin / in-repo checkout, the same walk the emitter/starter use).
  app.use(
    "/api/settings",
    settingsRouter({
      store:
        deps.settingsStore ??
        new SpineSettingsAdapter({
          scriptsDir: resolvePluginScriptsDir({
            scriptName: "_entity_adapter_local.py",
            envOverride: process.env.SULIS_ADAPTER_SCRIPTS_DIR,
          }),
          baseDir: join(deps.sulisStateDir, ".brain", "instances"),
        }),
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
