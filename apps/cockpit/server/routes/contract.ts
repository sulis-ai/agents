// WP-003 — GET /api/changes/:id/contract{,/data,/ui}
// (TDD §2.1 cockpit endpoints, §5 timing; ADR-001 read-only, ADR-003
// generic resolution, ADR-004 recreate-on-demand).
//
// Three GET-only endpoints that serve the rendered artifacts the renderers
// (WP-001/002) write into a change's worktree:
//
//   GET /                → ContractAvailability summary. The per-change
//                          links read this to decide present / no-UI note /
//                          unavailable.
//   GET /data            → serves CONTRACT.html as text/html.
//   GET /ui              → serves UI.html as text/html when present; a typed
//                          JSON note (NOT a broken link) when the change has
//                          no UI contract.
//
// Read-only invariant (ADR-001): only `router.get`. The cockpit CONSUMES the
// shared CONTRACT.manifest.json + serves the named files; it never parses
// the contracts itself and never writes. Recreating a tidied worktree is an
// explicitly-invoked step behind the RecreateRunner port — not in-process
// server generation.
//
// Generic resolution (ADR-003): the change is resolved by `:id` via the same
// `requireChange` + recreate-on-demand path tree/file/diff use; every fact
// (worktreePath, handle, shippedSha, branch) comes off the record — nothing
// is hard-wired to a specific change.
//
// Security (TDD §3 Armor): the change_id — the key that crosses the recreate
// seam (ADR-001) — is shape-guarded (`isSafeChangeHandle`) before it can reach
// the spawn. A malformed id degrades to the typed "unavailable" note WITHOUT
// spawning.

import { Router } from "express";

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits)
import type { ContractAvailability } from "../../shared/api-types";
import type {
  ChangeStoreReader,
  ChangeStoreRecord,
} from "../ports/ChangeStoreReader";
import type { RecreateRunner } from "../ports/RecreateRunner";

import { readFileContents } from "../lib/readFileContents";
import { isSafeChangeHandle } from "../lib/changeHandleGuard";

import { asyncHandler } from "./_async";
import { requireChange } from "./_change-lookup";
import {
  resolveContractWorktree,
  type ContractWorktreeResolution,
} from "./_recreate-on-demand";
import {
  readContractManifest,
  type ContractManifest,
} from "./_contract-manifest";

// The conventional artifact filenames the renderers write at the worktree
// root. Served by name (via the read-path's safeJoin) rather than by the
// manifest's absolute path, so the serving path stays inside the resolved
// worktree root — the same path-safety discipline tree/file/diff use.
const CONTRACT_HTML = "CONTRACT.html";
const UI_HTML = "UI.html";

export interface ContractRouterDeps {
  changeStore: ChangeStoreReader;
  /**
   * The recreate-on-demand runner (WP-004). Optional so existing app
   * construction sites that don't serve contracts are unaffected; when a
   * tidied worktree needs re-materialising and no runner is wired, the path
   * degrades to "unavailable" rather than throwing.
   */
  recreateRunner?: RecreateRunner;
}

/**
 * Resolve a change's worktree for contract serving: shape-guard the
 * change_id, then recreate-on-demand if the worktree was tidied. Returns the
 * WP-004 resolution, with the malformed-id case mapped to the same
 * "unavailable" degrade (never a spawn, never a throw into the request).
 */
async function resolveForServing(
  record: ChangeStoreRecord,
  runner: RecreateRunner | undefined,
): Promise<ContractWorktreeResolution> {
  // Defence-in-depth: refuse a malformed change_id before it can reach the
  // recreate spawn (the argparse flag-confusion vector + traversal shapes).
  // The change_id is the key carried across the seam (ADR-001), so it — not
  // the display handle — is what the serving boundary guards.
  if (!isSafeChangeHandle(record.changeId)) {
    return {
      status: "unavailable",
      note: "couldn't reach this shipped change's contracts",
      reason: "not-recreatable",
    };
  }
  if (runner === undefined) {
    // No recreate runner wired: a present worktree still resolves; an absent
    // one degrades (we can't re-materialise it).
    return resolveContractWorktree({ record, runner: noopRunner });
  }
  return resolveContractWorktree({ record, runner });
}

// A runner that never succeeds at recreating. Used when no real runner is
// injected: a present worktree resolves directly (resolveContractWorktree
// checks presence before ever calling recreate), an absent one degrades.
const noopRunner: RecreateRunner = {
  recreate: async () => ({
    ok: false,
    reason: "SPAWN_FAIL",
    detail: "no recreate runner configured",
  }),
};

/** Project the internal manifest into the wire-shape summary. */
function toAvailability(manifest: ContractManifest): ContractAvailability {
  const uiContract =
    manifest.uiContract.status === "present"
      ? ({ status: "present" } as const)
      : ({ status: "none", note: manifest.uiContract.note } as const);
  return {
    status: "ready",
    present: manifest.present,
    dataContract: manifest.dataContract,
    uiContract,
  };
}

export function createContractRouter(deps: ContractRouterDeps): Router {
  const router = Router({ mergeParams: true });

  /**
   * Shared prologue for the two file-serving endpoints: resolve the change +
   * its worktree, and on "unavailable" send the typed 404 note and return
   * null. A non-null return is a ready worktree root the handler serves from.
   * (3-consumer duplication across the handlers → extracted, EP-03.)
   */
  async function resolveServingRoot(
    req: import("express").Request,
    res: import("express").Response,
  ): Promise<string | null> {
    const { id } = req.params as { id: string };
    const record = await requireChange(deps.changeStore, id);
    const resolution = await resolveForServing(record, deps.recreateRunner);
    if (resolution.status === "unavailable") {
      res
        .status(404)
        .json({ error: resolution.note, code: "CONTRACT_UNAVAILABLE" });
      return null;
    }
    return resolution.worktreeRoot;
  }

  // GET / — the availability summary. (Uses its own response shape — the
  // links read this JSON — so it doesn't share the 404-note prologue.)
  router.get(
    "/",
    asyncHandler(async (req, res) => {
      const { id } = req.params as { id: string };
      const record = await requireChange(deps.changeStore, id);
      const resolution = await resolveForServing(record, deps.recreateRunner);
      if (resolution.status === "unavailable") {
        const body: ContractAvailability = {
          status: "unavailable",
          note: resolution.note,
        };
        res.json(body);
        return;
      }
      const manifest = await readContractManifest(resolution.worktreeRoot);
      res.json(toAvailability(manifest));
    }),
  );

  // GET /data — serve the rendered CONTRACT.html.
  router.get(
    "/data",
    asyncHandler(async (req, res) => {
      const worktreeRoot = await resolveServingRoot(req, res);
      if (worktreeRoot === null) return;
      const manifest = await readContractManifest(worktreeRoot);
      if (!manifest.present || manifest.contractHtml === null) {
        res.status(404).json({
          error: "no data contract has been rendered for this change yet",
          code: "CONTRACT_NOT_RENDERED",
        });
        return;
      }
      const file = await readFileContents(worktreeRoot, CONTRACT_HTML);
      sendHtml(res, file.content);
    }),
  );

  // GET /ui — serve the rendered UI.html, or a typed note when there is none.
  router.get(
    "/ui",
    asyncHandler(async (req, res) => {
      const worktreeRoot = await resolveServingRoot(req, res);
      if (worktreeRoot === null) return;
      const manifest = await readContractManifest(worktreeRoot);
      if (manifest.uiContract.status === "none") {
        // A note, served as JSON — NOT a broken link. The founder sees
        // "no UI contract for this change", not an error page.
        res.json({ uiContract: "none", note: manifest.uiContract.note });
        return;
      }
      const file = await readFileContents(worktreeRoot, UI_HTML);
      sendHtml(res, file.content);
    }),
  );

  return router;
}

/**
 * Send the rendered HTML. `readFileContents` returns `content: null` only for
 * a binary or over-cap file; a rendered contract page is neither, but we
 * guard defensively rather than send a literal "null".
 */
function sendHtml(
  res: import("express").Response,
  content: string | null,
): void {
  res.type("html").send(content ?? "");
}
