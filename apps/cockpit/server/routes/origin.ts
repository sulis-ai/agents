// WP-P09 — GET /api/changes/:id/origin (ADR-012).
//
// Two reads, one route (mirrors routes/provenance.ts):
//   - `GET /api/changes/:id/origin`              → ChangeOriginView (every
//     changed file's inferred origin).
//   - `GET /api/changes/:id/origin?path=<rel>`   → OriginView (ONE file's
//     inferred origin; `path: null` change-level if path is empty).
//
// GET-only; starts NO process (the read-only gate proves no mutation verb or
// process start lives here — the only git is the sanctioned `git log` boundary,
// reached THROUGH the InferredOriginAttribution adapter). `requireChange` gives
// the 404 for an unknown id; `unknown` origin is a valid result, never an error
// (CF-03). Recorded overrides inferred at the adapter swap (WP-P13) with no
// change to this route (ADR-012).

import { Router } from "express";

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern blocks escapes out of apps/cockpit/, which import/no-restricted-paths enforces)
import type { ChangeOriginView, OriginView } from "../../shared/api-types";
import type { ChangeStoreReader } from "../ports/ChangeStoreReader";
import { InferredOriginAttribution } from "../adapters/InferredOriginAttribution";
import { RecordedOriginAttribution } from "../adapters/RecordedOriginAttribution";
import { CompositeOriginAttribution } from "../adapters/CompositeOriginAttribution";
import { readOrigin } from "../lib/readOrigin";

import { asyncHandler } from "./_async";
import { requireChange } from "./_change-lookup";
import { resolveWorktreeRoot } from "./_worktree";

export interface OriginRouterDeps {
  changeStore: ChangeStoreReader;
  /** Where Claude Code stores session transcripts (`~/.claude/projects`). */
  claudeProjectsDir: string;
  /** Override the git subprocess timeout (tests). */
  gitTimeoutMs?: number;
}

export function createOriginRouter(deps: OriginRouterDeps): Router {
  const router = Router({ mergeParams: true });
  router.get(
    "/",
    asyncHandler(async (req, res) => {
      const { id } = req.params as { id: string };
      const path =
        typeof req.query.path === "string" ? req.query.path : null;

      const record = await requireChange(deps.changeStore, id);
      const worktreeRoot = await resolveWorktreeRoot(record.worktreePath);

      // Recorded-supersedes-inferred (ADR-012): a stamped commit (WP-P12) reads
      // back its EXACT origin (attribution "recorded", the badge drops "· likely"
      // with NO UI change); every other file falls back to the inferred adapter.
      const inferred = new InferredOriginAttribution({
        worktreeRoot,
        recordedWorktreePath: record.worktreePath,
        claudeProjectsDir: deps.claudeProjectsDir,
        ...(deps.gitTimeoutMs !== undefined
          ? { gitTimeoutMs: deps.gitTimeoutMs }
          : {}),
      });
      const recorded = new RecordedOriginAttribution({
        worktreeRoot,
        ...(deps.gitTimeoutMs !== undefined
          ? { gitTimeoutMs: deps.gitTimeoutMs }
          : {}),
      });
      const attribution = new CompositeOriginAttribution(recorded, inferred);

      // `?path=` → one file's origin (OriginView). `path: null` is allowed and
      // yields the honest change-level answer (per-file is the meaningful view).
      if (path !== null) {
        const origin = await attribution.originFor(id, path);
        const body: OriginView = { changeId: id, path, origin };
        res.json(body);
        return;
      }

      // No `?path=` → the whole-change list (one inferred origin per file).
      const body: ChangeOriginView = await readOrigin(
        id,
        worktreeRoot,
        record.baseSha,
        attribution,
        deps.gitTimeoutMs !== undefined
          ? { gitTimeoutMs: deps.gitTimeoutMs }
          : {},
      );
      res.json(body);
    }),
  );
  return router;
}
