// WP-011 (Blue refactor) — shared plugin-scripts resolution (EP-03).
//
// Two adapters resolve a vendored Sulis CLI by walking the same locations: the
// SpineEmitterMinter (the `sulis-emit-*` emitters, WP-010) and the
// SulisChangeStarter (`sulis-change`, WP-011). Both used the SAME three-step
// search — env override → in-repo marketplace checkout → latest installed
// plugin cache — keyed on a different script name. At the 2-consumer threshold
// (CLAUDE.md non-negotiable #2 / EP-03) the shared primitive is extracted HERE
// so the cache-walk + lexical-version-sort + in-repo-fallback logic lives once.
//
// `resolvePluginScriptsDir(scriptName)` returns the FIRST scripts DIR that holds
// `scriptName` (env override first, then in-repo, then the newest plugin-cache
// version), or "" when none is found. Each adapter joins its own script onto the
// returned dir.

import { existsSync, readdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export interface ResolvePluginScriptsOptions {
  /** The vendored CLI name the scripts dir must contain (e.g. "sulis-change"). */
  scriptName: string;
  /**
   * An optional env var whose value, when set + holding `scriptName`, wins
   * outright (the tests/CI seam). Each adapter names its own var so existing
   * overrides keep working (SULIS_EMITTER_SCRIPTS_DIR / SULIS_CHANGE_SCRIPT).
   * The override may name the scripts DIR (emitter convention) OR the script
   * FILE itself (change convention) — both are honoured.
   */
  envOverride?: string | undefined;
}

/**
 * Resolve the scripts DIR holding `scriptName`. Order:
 *   1. `envOverride` — accepted whether it names the dir or the script file;
 *   2. the in-repo `plugins/sulis/scripts` (a marketplace checkout);
 *   3. the latest installed plugin cache
 *      (`~/.claude/plugins/cache/<mp>/sulis/<version>/scripts`).
 * Returns "" when none holds `scriptName`.
 */
export function resolvePluginScriptsDir(
  opts: ResolvePluginScriptsOptions,
): string {
  const { scriptName, envOverride } = opts;

  if (envOverride) {
    // The override may be the scripts DIR (holds scriptName) or the script FILE.
    if (existsSync(path.join(envOverride, scriptName))) return envOverride;
    if (existsSync(envOverride) && path.basename(envOverride) === scriptName) {
      return path.dirname(envOverride);
    }
  }

  // In-repo (marketplace checkout): apps/cockpit/server/adapters → repo root.
  const here = path.dirname(fileURLToPath(import.meta.url));
  const repoRoot = path.resolve(here, "..", "..", "..", "..");
  const inRepo = path.join(repoRoot, "plugins", "sulis", "scripts");
  if (existsSync(path.join(inRepo, scriptName))) return inRepo;

  // Installed plugin cache — newest version dir that holds scriptName.
  const home = process.env.HOME ?? "";
  if (home) {
    const cacheRoot = path.join(home, ".claude", "plugins", "cache");
    const found = latestPluginScriptsDir(cacheRoot, scriptName);
    if (found) return found;
  }

  return "";
}

/** Find the newest `.../sulis/<version>/scripts` dir holding `scriptName`. */
function latestPluginScriptsDir(
  cacheRoot: string,
  scriptName: string,
): string | null {
  if (!existsSync(cacheRoot)) return null;
  const candidates: string[] = [];
  // Layout: <cacheRoot>/<marketplace>/sulis/<version>/scripts/<scriptName>
  for (const marketplace of safeReaddir(cacheRoot)) {
    const sulisDir = path.join(cacheRoot, marketplace, "sulis");
    for (const version of safeReaddir(sulisDir)) {
      const scripts = path.join(sulisDir, version, "scripts");
      if (existsSync(path.join(scripts, scriptName))) candidates.push(scripts);
    }
  }
  if (candidates.length === 0) return null;
  // Newest version string last (lexical sort is adequate for semver-ish dirs).
  candidates.sort();
  return candidates[candidates.length - 1] ?? null;
}

function safeReaddir(dir: string): string[] {
  try {
    return readdirSync(dir);
  } catch {
    return [];
  }
}
