// WP-P13 — RecordedOriginAttribution adapter (ADR-012/013).
//
// The recorded side of the `OriginAttribution` port. For one file it:
//   1. reads the `Sulis-Origin:` trailer on the file's last-changing commit via
//      the ONE git site (`gitOriginTrailer` in gitShow.ts — which reuses the
//      sanctioned `git log` read; NO new spawn, so the read-only gate stays
//      green),
//   2. if no trailer, falls back to the `.sulis/origin/<sha>.json` sidecar (a
//      plain fs read, keyed by that commit's sha — the WP-P12 fallback),
//   3. maps either source to an `Origin` with `attribution: "recorded"` via the
//      SHARED pure parsers in `lib/originAttribution/recorded.ts` (the same
//      parser the inferred path's recorded short-circuit uses — EP-03).
//
// A recorded origin OVERRIDES inference (ADR-012) — the route composes this
// adapter ahead of the inferred one. Where neither a trailer nor a sidecar
// exists, this adapter returns an honest `unknown` (still `attribution:
// "recorded"`, since the recorded SOURCE was consulted) and the route falls
// back to the inferred adapter.
//
// Fail-soft throughout: a file with no resolvable commit, an absent sidecar, a
// git failure — all resolve to `unknown`, NEVER an error (the port contract).

import { readFile } from "node:fs/promises";
import { join } from "node:path";

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern blocks escapes out of apps/cockpit/, which import/no-restricted-paths enforces)
import type { Origin } from "../../shared/api-types";
import type { OriginAttribution } from "../ports/OriginAttribution";
import { gitOriginTrailer } from "../lib/gitShow";
import {
  originFromSidecar,
  originFromTrailerValue,
} from "../lib/originAttribution/recorded";

export interface RecordedOriginDeps {
  /** Realpath-resolved worktree root for the change. */
  worktreeRoot: string;
  /** Override the git subprocess timeout (tests). */
  gitTimeoutMs?: number;
}

/** The honest "no recorded stamp here" answer — the route falls back to inferred. */
function unrecorded(reason: string): Origin {
  return { kind: "unknown", reason, attribution: "recorded" };
}

export class RecordedOriginAttribution implements OriginAttribution {
  constructor(private readonly deps: RecordedOriginDeps) {}

  async originFor(_changeId: string, path?: string): Promise<Origin> {
    // Change-level origin: with no path there is no single commit to read a
    // stamp from. Honest unknown — the per-file list is the meaningful view.
    if (path === undefined || path === "") {
      return unrecorded(
        "origin is attributed per file; ask for a specific file's origin",
      );
    }

    let trailer: Awaited<ReturnType<typeof gitOriginTrailer>>;
    try {
      trailer = await gitOriginTrailer({
        cwd: this.deps.worktreeRoot,
        relativePath: path,
        ...(this.deps.gitTimeoutMs !== undefined
          ? { timeoutMs: this.deps.gitTimeoutMs }
          : {}),
      });
    } catch {
      // A git failure (e.g. timeout) is fail-soft for origin: unknown, never 500.
      trailer = null;
    }
    if (trailer === null) {
      return unrecorded("no commit has touched this file yet");
    }

    // 1. The trailer wins — the stamp travels with the commit.
    const fromTrailer = originFromTrailerValue(trailer.originTrailer);
    if (fromTrailer !== null) return fromTrailer;

    // 2. Fall back to the sidecar keyed by the commit sha.
    const fromSidecar = await this.readSidecar(trailer.sha);
    if (fromSidecar !== null) return fromSidecar;

    // 3. Neither — no recorded origin for this file (route falls back to inferred).
    return unrecorded("no recorded origin stamp for this file");
  }

  /** Read `.sulis/origin/<sha>.json`, fail-soft to null (absent / unparseable). */
  private async readSidecar(sha: string): Promise<Origin | null> {
    if (sha === "") return null;
    const sidecarPath = join(
      this.deps.worktreeRoot,
      ".sulis",
      "origin",
      `${sha}.json`,
    );
    try {
      const raw = await readFile(sidecarPath, "utf8");
      return originFromSidecar(JSON.parse(raw) as unknown);
    } catch {
      return null;
    }
  }
}
