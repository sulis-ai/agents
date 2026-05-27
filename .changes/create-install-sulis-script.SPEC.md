---
founder_facing: false
---
# Spec — install-sulis.sh + co-shipped marketplace.json drift fix

**Change:** CH-01KSNX · create
**Scope:** top-level installer script for the sulis plugin's full toolchain;
small registry drift fix co-shipped.

## What this should do

### Part A — `plugins/sulis/scripts/install-sulis.sh` (new)

Top-level installer that brings a fresh machine to "everything sulis
can do, works." Today there's only `install-probe-tools.sh` for the
analyse-codebase skill (3 tools); code-health's 7 tiers need ~10 more,
and the core (`gh`, `python3`, etc.) is undocumented.

**Layered model:**

- **Core layer** (required for any sulis flow): `git`, `gh` (GitHub
  CLI), `python3 ≥ 3.11`, `pytest` (developers only — implied by
  Python install).
- **Analyse-codebase layer** (`/sulis:analyse-codebase`):
  `ast-grep`, `lizard` (Terry Yin's — NOT the brew default),
  `scc`, `detect-secrets`. Delegates to the existing
  `install-probe-tools.sh` for these — no duplication.
- **Code-health layer** (`/sulis:code-health` tiers 1, 2, 5):
  `hadolint`, `trivy`, `gitleaks`, `semgrep`, `jscpd`, `ts-prune`,
  `vulture`, `deadcode`. Plus language linters as optional:
  `ruff`, `mypy` (Python); `eslint` (JS/TS); `clippy` (already with
  rust toolchain); `golangci-lint` (Go).

**Flags:**

- `--check` — audit what's installed; no changes.
- `--core-only` — install just the core layer.
- `--with-code-health` — core + analyse-codebase + code-health.
- `--all` — same as `--with-code-health` (alias, more discoverable).
- (no flag) — install core + analyse-codebase (the minimum useful
  default — every sulis user needs these; code-health is
  power-user).
- `--yes` / `-y` — skip interactive confirmations (useful for CI).

**Platform support** (mirroring `install-probe-tools.sh`):

- macOS: Homebrew + `pipx` for Python CLIs + `npm`/`cargo` fallbacks
- Debian/Ubuntu: `apt-get` + `pipx`/`pip3` + `npm`/`cargo` fallbacks
- Fedora/RHEL: same as Debian (package-manager-agnostic logic)
- Other: prints manual-install instructions + exits with code 2

**Graceful-degrade contract:** each missing OPTIONAL tool is a
warning, not an error. Only the core layer fails the script if
missing. Code-health degrades by emitting `NOT_ASSESSED` per tier —
which the SKILL.md already explicitly handles (per the existing
"three invocation modes" section).

**Exit codes (mirroring install-probe-tools.sh):**

- 0 — everything required by selected layers is present
- 1 — at least one required tool missing after install attempts
- 2 — unsupported platform; manual install needed
- 3 — prerequisite missing (no Homebrew on macOS, no package manager
  on Linux)

**Special-cases preserved from probe installer:**

- `lizard` MUST be Terry Yin's complexity analyser, NOT the
  compression utility `brew install lizard` would give you. Use
  `pipx install lizard` on macOS. The verification step greps
  `lizard --help` for "Cyclomatic Complexity Analyzer".
- `pipx` is the preferred Python-CLI installer (handles PATH
  correctly); `pip3 --user` is the fallback.

### Part B — co-shipped registry drift fix

`.claude-plugin/marketplace.json` has two stale version fields:

| Field | Stale | Real |
|---|---|---|
| `metadata.version` | `1.98.1` | `1.111.0` (per latest git tag) |
| `plugins[sulis].version` | `0.55.1` | `0.67.0` (per plugin.json) |

Bump both to match reality. The `investor-coach` entry already
matches (`0.6.0`) — no change.

### Part C — top-level README link

Add a one-line install snippet to `README.md`'s "Start Here" so
founders can run the installer before installing the plugin:

```bash
# Optional — install the tools sulis needs across all skills
bash <(curl -sSL https://raw.githubusercontent.com/sulis-ai/agents/main/plugins/sulis/scripts/install-sulis.sh)
```

(Or clone-then-run for safety-conscious users.)

## How we'll know it's done

- `plugins/sulis/scripts/install-sulis.sh` exists, exec bit set, runs
  `--help` cleanly.
- `bash plugins/sulis/scripts/install-sulis.sh --check` on this
  machine prints a clean audit of what's present + missing across
  the three layers.
- Calling the installer with `--core-only` is idempotent (re-running
  reports "all present" without re-installing).
- The installer correctly delegates analyse-codebase tools to
  `install-probe-tools.sh` (no duplication of those install
  routines).
- `marketplace.json` `metadata.version` = `1.111.0`,
  `plugins[sulis].version` = `0.67.0`.
- README has the install one-liner in the right place.
- Step 4.5 review gate (#30) PASS — the installer is a shell script
  so the gate runs over the script itself + the marketplace.json
  diff.
- Existing 773-test suite still green (this change doesn't touch
  Python; should be no regression).

## What to avoid

- **Do NOT duplicate `install-probe-tools.sh`'s install routines.**
  The new script DELEGATES (calls the existing one). If a platform
  detail changes, only the upstream installer needs editing.
- **Do NOT install language linters unconditionally.** `ruff` is a
  Python linter; installing it on a pure-Go founder's machine is
  wasted bytes. Each language linter is mentioned in the audit
  output as "optional — install if you write {language}" and only
  installed under `--all`.
- **Do NOT touch the founder's `~/.claude/settings.json`.** That's a
  config-modify path that needs `update-config` discipline. The
  installer just puts tools on PATH; configuration is separate.
- **Do NOT auto-`curl | bash` the script in any docs without
  surfacing the clone-then-run alternative** — `curl | bash` is a
  red flag for safety-conscious founders. The README mentions both.

## Verification plan

- `bash install-sulis.sh --help` works
- `bash install-sulis.sh --check` runs on this machine + reports
  honest status
- `bash install-sulis.sh --check --core-only` runs + matches the
  unfiltered core entries
- `bash -n install-sulis.sh` parses cleanly (syntax check)
- `shellcheck install-sulis.sh` clean if available (advisory; not a
  blocker if shellcheck not installed)
- `marketplace.json` validates as JSON with the new versions

## References

- `plugins/sulis/skills/analyse-codebase/scripts/install-probe-tools.sh`
  — existing installer, style template + delegation target
- `plugins/sulis/skills/code-health/SKILL.md` — declares which tools
  each tier needs
- `.claude-plugin/marketplace.json` — registry to fix
- `README.md` — install snippet location
- Git tags for marketplace versioning: `v1.111.0` is current
