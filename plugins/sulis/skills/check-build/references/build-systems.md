# Build Systems — Detection + Commands + Hygiene Rules

How `scripts/builder.py` detects build systems, runs them, and parses
results. Plus manifest-hygiene rules per file type.

## Detection signals

| System | Signal | Confidence |
|---|---|---|
| **pip** (Python) | `pyproject.toml` with `[project]` or `[tool.poetry]`, OR `setup.py`, OR `requirements.txt` | High |
| **npm/yarn/pnpm** (Node) | `package.json` with `scripts.build` | High |
| **go** | `go.mod` | High |
| **cargo** (Rust) | `Cargo.toml` | High |
| **docker** | `Dockerfile` (at root or `Dockerfile.{name}`) | Medium (build target needed for multi-image) |
| **make** | `Makefile` with a `build` or `all` target | Low (Make is too flexible to assume `make` = build) |

Multi-detection: a single repo can have multiple systems. v1 reports
each and runs each independently when `--run` is passed. Use
`--system <name>` to restrict to one.

## Run commands + safe defaults

| System | Default build command | Side effects? |
|---|---|---|
| pip | `python -m build` (modern) or `pip install -e .` (editable) | No |
| npm | `npm run build` | **Maybe** — depends on script contents |
| yarn | `yarn build` | Maybe — depends on script |
| pnpm | `pnpm build` | Maybe — depends on script |
| go | `go build ./...` | No |
| cargo | `cargo build` | No |
| docker | `docker build -t {project}:check .` | No (local image only) |
| make | `make build` (if target exists), else `make all` | **Often** — Make targets can do anything |

### Side-effect blocklist

Make targets + npm scripts matching these patterns are SKIPPED by
default unless `--allow-side-effects` is passed:

- `publish`, `publish:*`, `*:publish`
- `deploy`, `deploy:*`, `*:deploy`
- `release`, `release:*`, `*:release`
- `push`, `*:push`
- `upload`, `*:upload`
- `notify:*` (notification side effects)

Per-project blocklist additions: `.checkup/{project}/dangerous-targets.txt`
(one pattern per line; lines starting with `#` are comments).

## Manifest hygiene rules

The manifest-hygiene check runs on every detected manifest file. Rules
per file type:

### Common (all JSON manifests)

| Rule | Severity | What |
|---|---|---|
| MH-001 | high | File parses as JSON |
| MH-002 | concern | No trailing commas (some parsers reject) |
| MH-003 | advisory | UTF-8 encoded; LF line endings |

### plugin.json (Claude Code plugin)

| Rule | Severity | What |
|---|---|---|
| PH-101 | high | `name` field present, kebab-case, ≤50 chars |
| PH-102 | high | `version` field present, valid semver (X.Y.Z) |
| PH-103 | high | `description` field present, ≤500 chars (per HD-004) |
| PH-104 | concern | `repository` field present if shipping to a marketplace |
| PH-105 | advisory | `keywords` array present, ≥3 entries |

### marketplace.json

| Rule | Severity | What |
|---|---|---|
| MM-101 | high | `metadata.version` field present, valid semver |
| MM-102 | high | `plugins` array present, non-empty |
| MM-103 | high | Each plugin entry has `name`, `source`, `version`, `description` |
| MM-104 | concern | Plugin entry `description` ≤500 chars (per HD-004) |
| MM-105 | advisory | Plugin entry `source` points at a path that exists |

### package.json (Node)

| Rule | Severity | What |
|---|---|---|
| PJ-101 | high | `name` field present |
| PJ-102 | high | `version` field present, valid semver |
| PJ-103 | advisory | `description` field present |
| PJ-104 | advisory | `license` field present |
| PJ-105 | concern | `scripts.build` present if claiming to be buildable |

### pyproject.toml (Python)

| Rule | Severity | What |
|---|---|---|
| PT-101 | high | `[project]` or `[tool.poetry]` table present |
| PT-102 | high | `name` field present |
| PT-103 | high | `version` field present, valid semver-ish (PEP 440) |
| PT-104 | advisory | `description` field present |

## Parser notes

### pip / Python build

Common build errors and their founder-mode translations:

| Pattern | Founder phrasing |
|---|---|
| `ResolutionImpossible:` | "Couldn't figure out which package versions to install — there's a conflict between dependencies. Check the project's requirements." |
| `ModuleNotFoundError:` | "Build tried to import {module} but couldn't find it. Likely a missing dependency." |
| `error: subprocess-exited-with-error` | "A package's installer crashed while trying to build itself. Check the package's own README." |
| `Permission denied` | "Build doesn't have permission to write somewhere it needs to. Often fixed with a virtualenv." |

### npm

| Pattern | Founder phrasing |
|---|---|
| `ENOENT` | "Build can't find a file or directory it expected — typically a missing config or path." |
| `ETIMEDOUT` / `ECONNREFUSED` | "Build couldn't reach the registry — check network or registry config." |
| `npm ERR! missing script:` | "package.json doesn't have the script the build is trying to run." |
| `EACCES` / `EPERM` | "Permission issue — typically a permissions problem on node_modules/." |

### go

Go build errors are usually clear; minimal translation needed. Map:
- `cannot find module` → "Couldn't find module {x} — check `go.mod`."
- `imports `…`: undefined` → "Code uses something that isn't defined — likely a missing import or typo."

### docker

| Pattern | Founder phrasing |
|---|---|
| `Cannot connect to the Docker daemon` | "Docker isn't running. Start Docker Desktop or the daemon and try again." |
| `failed to compute cache key` | "Docker build cache is confused — try `docker builder prune` if this persists." |
| `pull access denied` | "Docker can't pull a base image — check registry auth or image name." |

## Cached-vs-fresh decision tree

Same logic as check-tests:

```
1. If --no-run: report detection-only.
2. Else if cached results found AND not stale (< 5 min old): use cache.
3. Else if --run: run fresh.
4. Else: report "build systems detected; pass --run to verify they actually build."
```

Cache lives at `.checkup/{project}/build-cache.json` (separate from
baseline; cache is short-lived, baseline is the regression-detection
snapshot).

## Adding a new build system

To extend support:

1. Add a `BuildSystem` dataclass entry in `scripts/builder.py`
   (`KNOWN_SYSTEMS` list) with detection signals + run command +
   parser function.
2. Add a parser function returning `BuildResult(system, exit_code,
   parsed_errors)`.
3. Update this document.

Same registry-driven pattern as code-health's tier-registry and
check-tests's framework-detection.
