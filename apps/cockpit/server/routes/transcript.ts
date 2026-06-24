// WP-010 — GET /api/changes/:id/transcript.
//
// Returns the chronologically-merged TranscriptMessage[] for a change.
//
// CH-GJ9KQR WP-006 — SUBSTITUTE-Strangle (data-source re-point). The raw
// transcript view now reads OUR durable ThreadStore (WP-002) FIRST — the
// authoritative, vendor-neutral message log the cockpit owns (one thread per
// change, ADR-004; keyed by the change id) — instead of Claude's provider
// transcript files. The provider-transcript path (locateTranscripts →
// parseTranscripts, WP-009) stays available as the fallback when the store has
// no log for the change yet: the old read path remains behind the strangle
// until the durable store is proven across a full thread lifecycle. Removing
// the fallback from this raw-read path is the recorded `removal_plan` milestone
// (a Strangle without a recorded removal is wrapper rot — the WP records one).
//
// Behaviour-preserving for the UI: the wire shape is the SAME TranscriptMessage[]
// (the store's ThreadMessage maps to it), so the rich/raw renderers are
// unchanged (no visual change). This re-point does NOT touch the live-tail
// terminal (the in-memory EventLog path) — only the durable raw view.

import { Router } from "express";

import type { ChangeStoreReader } from "../ports/ChangeStoreReader";
import { locateTranscripts } from "../lib/locateTranscripts";
import { parseTranscripts } from "../lib/parseTranscripts";
import { readThreadStore } from "../lib/readThreadStore";

import { asyncHandler } from "./_async";
import { requireChange } from "./_change-lookup";

export interface TranscriptRouterDeps {
  changeStore: ChangeStoreReader;
  /** Root of the Sulis state dir (`~/.sulis`) — where the durable ThreadStore
   *  log lives under `changes/{changeId}/threads/` (ADR-002 local binding). */
  sulisStateDir: string;
  claudeProjectsDir: string;
}

export function createTranscriptRouter(deps: TranscriptRouterDeps): Router {
  const router = Router({ mergeParams: true });
  router.get(
    "/",
    asyncHandler(async (req, res) => {
      const { id } = req.params as { id: string };
      const record = await requireChange(deps.changeStore, id);

      // Strangle: prefer OUR durable store (ADR-002 / ADR-004). The thread is
      // keyed by the change id (one thread per change).
      const stored = await readThreadStore(deps.sulisStateDir, id);
      if (stored.length > 0) {
        res.json(stored);
        return;
      }

      // Fallback (behind the strangle, per removal_plan): the provider
      // transcript path, for a change with no durable log yet.
      const paths = await locateTranscripts(
        record.worktreePath,
        deps.claudeProjectsDir,
      );
      const messages = await parseTranscripts(paths);
      res.json(messages);
    }),
  );
  return router;
}
