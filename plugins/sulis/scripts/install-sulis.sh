#!/usr/bin/env bash
# install-sulis.sh
#
# Top-level installer for the sulis plugin's full toolchain. Brings a fresh
# machine to "everything sulis can do, works."
#
# Layered:
#   Core               — git, gh, python3, pipx     (REQUIRED for any sulis flow)
#   Analyse-codebase   — ast-grep, lizard, scc,
#                        detect-secrets             (delegates to install-probe-tools.sh)
#   Code-health        — hadolint, trivy, gitleaks,
#                        semgrep, jscpd, ts-prune,
#                        vulture, ruff, mypy        (each is optional;
#                                                    missing = NOT_ASSESSED, not fail)
#
# Supports: macOS (Homebrew + pipx + cargo + npm), Debian/Ubuntu (apt + pipx
# + cargo + npm), Fedora/RHEL (dnf + same fallbacks). Other platforms:
# prints manual-install instructions.
#
# Usage:
#   bash install-sulis.sh                  # core + analyse-codebase (default)
#   bash install-sulis.sh --check          # audit only; no changes
#   bash install-sulis.sh --core-only      # just core (git/gh/python3/pipx)
#   bash install-sulis.sh --with-code-health   # core + analyse + code-health
#   bash install-sulis.sh --with-browser   # core + analyse + browser-proving
#                                          #   (Node + Playwright + chromium,
#                                          #    for /sulis:prove on UI/auth flows)
#   bash install-sulis.sh --all            # core + analyse + code-health (NOT
#                                          #   browser — that's heavy + opt-in)
#   bash install-sulis.sh -y / --yes       # skip interactive prompts (CI)
#
# Exit codes:
#   0  — every tool in the selected layer is present (or installed cleanly)
#   1  — at least one REQUIRED tool missing after install attempts
#   2  — unsupported platform; manual install needed
#   3  — prerequisite missing (e.g. Homebrew on macOS, no package manager)

set -euo pipefail

# ─── Argument parsing ──────────────────────────────────────────────────────

LAYER_CORE=1
LAYER_PROBE=1
LAYER_CODE_HEALTH=0
LAYER_BROWSER=0
CHECK_ONLY=0
ASSUME_YES=0

for arg in "$@"; do
  case "$arg" in
    --check)              CHECK_ONLY=1 ;;
    --core-only)          LAYER_PROBE=0; LAYER_CODE_HEALTH=0; LAYER_BROWSER=0 ;;
    --with-code-health)   LAYER_CODE_HEALTH=1 ;;
    --with-browser)       LAYER_BROWSER=1 ;;
    --all)                LAYER_CODE_HEALTH=1 ;;
    -y|--yes)             ASSUME_YES=1 ;;
    -h|--help)
      grep '^#' "$0" | sed 's/^# \?//'
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      echo "Run 'bash install-sulis.sh --help' for usage." >&2
      exit 1
      ;;
  esac
done

# ─── Logging helpers ───────────────────────────────────────────────────────

c_green="\033[32m"
c_yellow="\033[33m"
c_red="\033[31m"
c_bold="\033[1m"
c_dim="\033[2m"
c_reset="\033[0m"

ok()    { printf "%b✓%b %s\n" "$c_green"  "$c_reset" "$1"; }
warn()  { printf "%b⚠%b %s\n" "$c_yellow" "$c_reset" "$1"; }
err()   { printf "%b✗%b %s\n" "$c_red"    "$c_reset" "$1" >&2; }
info()  { printf "%b…%b %s\n" "$c_bold"   "$c_reset" "$1"; }
hdr()   { printf "\n%b%s%b\n" "$c_bold"   "$1" "$c_reset"; }
dim()   { printf "%b%s%b\n"   "$c_dim"    "$1" "$c_reset"; }

# ─── Platform detection ────────────────────────────────────────────────────

OS="$(uname -s 2>/dev/null || echo unknown)"
PLATFORM="unknown"

case "$OS" in
  Darwin) PLATFORM="macos" ;;
  Linux)
    if   command -v apt-get >/dev/null 2>&1; then PLATFORM="debian"
    elif command -v dnf     >/dev/null 2>&1; then PLATFORM="fedora"
    elif command -v yum     >/dev/null 2>&1; then PLATFORM="rhel"
    elif command -v pacman  >/dev/null 2>&1; then PLATFORM="arch"
    else                                          PLATFORM="linux-other"
    fi
    ;;
esac

# ─── Tool detection ────────────────────────────────────────────────────────

is_installed() { command -v "$1" >/dev/null 2>&1; }

# Each layer's tools, formatted "tool|required|notes-for-audit"
CORE_TOOLS=(
  "git|required|version control"
  "gh|required|GitHub CLI (for sulis-change ship + sulis-issues)"
  "python3|required|Python 3.11 or newer"
  "pipx|optional|isolated Python-CLI installer (recommended)"
)

# Probe tools — the existing install-probe-tools.sh installs these.
# Audited here for the unified status report; install delegated.
PROBE_TOOLS=(
  "ast-grep|required|tree-sitter pattern matching"
  "lizard|required|McCabe complexity (Terry Yin's — NOT the brew default)"
  "scc|required|LOC + complexity totals"
  "detect-secrets|optional|credential scanning (Phase 1.17)"
)

CODE_HEALTH_TOOLS=(
  "hadolint|optional|Dockerfile linter (Tier 1)"
  "trivy|optional|container vuln scanner (Tier 1, 2)"
  "gitleaks|optional|repo secret scanner (Tier 1, 2)"
  "semgrep|optional|security analysis (Tier 2)"
  "jscpd|optional|JS/TS duplication detector (Tier 5)"
  "ts-prune|optional|TS dead-code detector"
  "vulture|optional|Python dead-code detector"
  "ruff|optional|Python linter (Tier 5)"
  "mypy|optional|Python type-checker"
)

# ─── Python version check ──────────────────────────────────────────────────

check_python_version() {
  if ! is_installed python3; then
    return 1
  fi
  # 3.11 minimum per pyproject.tooling. Use python3's own version reporter.
  python3 - <<'PYEOF' >/dev/null 2>&1
import sys
sys.exit(0 if sys.version_info >= (3, 11) else 1)
PYEOF
}

# ─── Audit ──────────────────────────────────────────────────────────────────

audit_tool_list() {
  # Args: "label" "tool1|required|notes" "tool2|optional|notes" ...
  local label="$1"; shift
  hdr "$label"
  local any_required_missing=0
  for spec in "$@"; do
    local tool="${spec%%|*}"
    local rest="${spec#*|}"
    local req="${rest%%|*}"
    local notes="${rest#*|}"
    if is_installed "$tool"; then
      ok  "$tool"
      dim "    $notes"
    else
      if [[ "$req" == "required" ]]; then
        err  "$tool  (required — missing)"
        any_required_missing=1
      else
        warn "$tool  (optional — not installed)"
      fi
      dim "    $notes"
    fi
  done
  return $any_required_missing
}

audit_all() {
  local missing=0
  if [[ "$LAYER_CORE" -eq 1 ]]; then
    audit_tool_list "Core layer (required)" "${CORE_TOOLS[@]}" || missing=1
    if is_installed python3 && ! check_python_version; then
      err "  python3 is present but < 3.11 (sulis needs ≥ 3.11)"
      missing=1
    fi
  fi
  if [[ "$LAYER_PROBE" -eq 1 ]]; then
    audit_tool_list "Analyse-codebase layer" "${PROBE_TOOLS[@]}" || missing=1
  fi
  if [[ "$LAYER_CODE_HEALTH" -eq 1 ]]; then
    audit_tool_list "Code-health layer (all optional — missing tools \
become NOT_ASSESSED tiers)" "${CODE_HEALTH_TOOLS[@]}" || true
    # Code-health tools are ALL optional — never count toward `missing`.
  fi
  if [[ "$LAYER_BROWSER" -eq 1 ]]; then
    audit_browser_layer || true   # all optional — never counts toward `missing`
  fi
  return $missing
}

# ─── Core install routines ─────────────────────────────────────────────────

install_core_macos() {
  if ! is_installed brew; then
    err "Homebrew is required on macOS but not found."
    err "Install Homebrew first: https://brew.sh/"
    exit 3
  fi
  for t in git gh python3 pipx; do
    if ! is_installed "$t"; then
      info "Installing $t via brew…"
      # python3 might already be on PATH via Xcode CLT or system; only
      # install if `command -v` says it's absent. Same for git (Xcode CLT
      # ships git on macOS by default).
      brew install "$t"
    fi
  done
  if is_installed pipx; then
    pipx ensurepath >/dev/null 2>&1 || true
  fi
}

install_core_debian() {
  if ! command -v sudo >/dev/null 2>&1; then
    err "sudo is required on Debian/Ubuntu but not found."
    err "Run this script as root, or install sudo first."
    exit 3
  fi
  info "Updating apt index…"
  sudo apt-get update -y
  info "Installing core: git gh python3 python3-pip pipx…"
  # GitHub CLI on Ubuntu 22.04+ is in the default repos as `gh`; on older,
  # users may need the keyring setup at https://cli.github.com/manual/installation.
  sudo apt-get install -y git python3 python3-pip pipx
  if ! is_installed gh; then
    warn "gh not in default apt repos for this Ubuntu version."
    warn "Follow: https://cli.github.com/manual/installation"
  fi
  if is_installed pipx; then
    pipx ensurepath >/dev/null 2>&1 || true
  fi
}

install_core_fedora() {
  info "Installing core: git gh python3 python3-pip pipx…"
  sudo dnf install -y git gh python3 python3-pip pipx
  if is_installed pipx; then
    pipx ensurepath >/dev/null 2>&1 || true
  fi
}

install_core() {
  case "$PLATFORM" in
    macos)        install_core_macos ;;
    debian)       install_core_debian ;;
    fedora|rhel)  install_core_fedora ;;
    arch)         err "Arch unsupported by this installer; install git gh python pipx via pacman manually."; exit 2 ;;
    *)            err "Unsupported platform: $OS"; show_manual_instructions; exit 2 ;;
  esac
}

# ─── Analyse-codebase delegation ───────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROBE_INSTALLER="$SCRIPT_DIR/../skills/analyse-codebase/scripts/install-probe-tools.sh"

install_probe_layer() {
  if [[ ! -f "$PROBE_INSTALLER" ]]; then
    err "Probe installer not found at: $PROBE_INSTALLER"
    err "Have you cloned the full sulis plugin tree? install-sulis.sh has"
    err "to live next to skills/analyse-codebase/scripts/install-probe-tools.sh."
    exit 1
  fi
  info "Delegating to install-probe-tools.sh (analyse-codebase deps)…"
  bash "$PROBE_INSTALLER"
}

# ─── Code-health install routines ──────────────────────────────────────────

install_code_health_macos() {
  if ! is_installed brew; then
    err "Homebrew is required on macOS for code-health tools."
    exit 3
  fi
  # Available via brew directly.
  for t in hadolint trivy gitleaks semgrep; do
    if ! is_installed "$t"; then
      info "Installing $t via brew (code-health, optional)…"
      brew install "$t" || warn "$t install failed; tier will degrade to NOT_ASSESSED."
    fi
  done
  # Available via npm.
  if is_installed npm; then
    for t in jscpd ts-prune; do
      if ! is_installed "$t"; then
        info "Installing $t via npm -g (code-health, optional)…"
        npm install -g "$t" || warn "$t install failed; tier will degrade."
      fi
    done
  else
    warn "npm not found; skipping jscpd + ts-prune. Install Node.js to enable them."
  fi
  # Available via pipx.
  if is_installed pipx; then
    for t in vulture ruff mypy; do
      if ! is_installed "$t"; then
        info "Installing $t via pipx (code-health, optional)…"
        pipx install "$t" || warn "$t install failed; tier will degrade."
      fi
    done
  else
    warn "pipx not found; skipping vulture/ruff/mypy. Run --core-only first."
  fi
}

install_code_health_debian() {
  # gitleaks is in default repos on recent Ubuntu; hadolint isn't (it's a
  # Haskell binary — use the GitHub release). trivy needs Aqua's apt repo.
  # We do best-effort installs and degrade loudly on misses.
  info "Installing code-health tools that ship via apt…"
  sudo apt-get install -y gitleaks 2>/dev/null || \
    warn "gitleaks not in this distro's apt; download from https://github.com/gitleaks/gitleaks/releases"
  if ! is_installed hadolint; then
    warn "hadolint not in apt; install from https://github.com/hadolint/hadolint/releases"
  fi
  if ! is_installed trivy; then
    warn "trivy not in apt by default. Install via Aqua's apt repo:"
    warn "  https://aquasecurity.github.io/trivy/latest/getting-started/installation/"
  fi
  if is_installed pipx; then
    for t in semgrep vulture ruff mypy; do
      if ! is_installed "$t"; then
        info "Installing $t via pipx (code-health, optional)…"
        pipx install "$t" || warn "$t install failed; tier will degrade."
      fi
    done
  fi
  if is_installed npm; then
    for t in jscpd ts-prune; do
      if ! is_installed "$t"; then
        npm install -g "$t" || warn "$t install failed; tier will degrade."
      fi
    done
  fi
}

install_code_health_fedora() { install_code_health_debian; }
install_code_health_rhel()   { install_code_health_debian; }

install_code_health() {
  case "$PLATFORM" in
    macos)        install_code_health_macos ;;
    debian)       install_code_health_debian ;;
    fedora|rhel)  install_code_health_fedora ;;
    *)            warn "code-health install routines not supported for $PLATFORM; tier will mostly degrade." ;;
  esac
}

# ─── Browser-proving install routines (opt-in; --with-browser) ───────────────
# The deterministic browser driver + the Playwright MCP (declared in .mcp.json)
# need: the Python `playwright` package (the `browser` extra), a chromium binary,
# and Node/npx (for the @playwright/mcp server). ALL OPTIONAL — absent,
# browser-proving degrades to the human-attest path (never a fake green), the
# same way code-health tools degrade to NOT_ASSESSED.

playwright_python_present() {
  [ -x "$SCRIPT_DIR/.venv/bin/python" ] && \
    "$SCRIPT_DIR/.venv/bin/python" -c "import playwright" >/dev/null 2>&1
}

chromium_present() {
  ls "${PLAYWRIGHT_BROWSERS_PATH:-$HOME/Library/Caches/ms-playwright}"/chromium-* >/dev/null 2>&1 || \
  ls "$HOME/.cache/ms-playwright"/chromium-* >/dev/null 2>&1
}

audit_browser_layer() {
  hdr "Browser-proving layer (opt-in — for /sulis:prove on UI/auth flows)"
  if is_installed node; then ok "node"; dim "    JS runtime (for the @playwright/mcp server)"
  else warn "node  (optional — needed for the Playwright MCP; install Node.js)"; fi
  if is_installed npx; then ok "npx"; else warn "npx  (optional — ships with Node.js)"; fi
  if playwright_python_present; then ok "playwright (python)"; dim "    the 'browser' extra"
  else warn "playwright (python)  (optional — installed by --with-browser)"; fi
  if chromium_present; then ok "chromium (playwright browser)"
  else warn "chromium  (optional — run: uv run playwright install chromium)"; fi
  return 0   # all optional — never counts toward `missing`
}

install_browser_layer() {
  if ! is_installed uv; then
    warn "uv not found — needed to install the playwright extra."
    warn "  Install uv: https://docs.astral.sh/uv/  — then re-run with --with-browser."
    return 0
  fi
  info "Installing the playwright extra (uv sync --extra browser)…"
  ( cd "$SCRIPT_DIR" && uv sync --extra browser ) \
    || warn "playwright extra install failed; browser-proving degrades to human-attest."
  info "Installing the chromium browser binary…"
  ( cd "$SCRIPT_DIR" && uv run playwright install chromium ) \
    || warn "chromium install failed; browser-proving degrades."
  if ! is_installed node; then
    warn "Node.js not found — the @playwright/mcp server (declared in .mcp.json) needs it."
    warn "  Install Node.js to enable agent-driven browser proving: https://nodejs.org/"
  fi
}

# ─── Manual instructions ───────────────────────────────────────────────────

show_manual_instructions() {
  cat <<'EOF'

Manual installation:

  Core:
    git           — usually preinstalled; otherwise package manager
    gh            — https://cli.github.com/manual/installation
    python3 ≥3.11 — https://www.python.org/downloads/
    pipx          — https://pipx.pypa.io/stable/installation/

  Analyse-codebase:
    See plugins/sulis/skills/analyse-codebase/scripts/install-probe-tools.sh
    (run it directly; it has macOS + Debian + Fedora install routines)

  Code-health (all optional — missing tools become NOT_ASSESSED tiers):
    hadolint   — https://github.com/hadolint/hadolint
    trivy      — https://trivy.dev/
    gitleaks   — https://github.com/gitleaks/gitleaks
    semgrep    — pipx install semgrep
    jscpd      — npm install -g jscpd
    ts-prune   — npm install -g ts-prune
    vulture    — pipx install vulture
    ruff       — pipx install ruff
    mypy       — pipx install mypy

Re-run this script with --check after installing to verify.
EOF
}

# ─── Main ──────────────────────────────────────────────────────────────────

printf "%bSulis plugin installer%b\n" "$c_bold" "$c_reset"
printf "Platform: %s\n" "$PLATFORM"

# Print selected layers so the founder knows what's about to be touched.
layers=()
[[ "$LAYER_CORE"         -eq 1 ]] && layers+=("core")
[[ "$LAYER_PROBE"        -eq 1 ]] && layers+=("analyse-codebase")
[[ "$LAYER_CODE_HEALTH"  -eq 1 ]] && layers+=("code-health")
[[ "$LAYER_BROWSER"      -eq 1 ]] && layers+=("browser-proving")
printf "Layers:   %s\n" "${layers[*]}"
if [[ "$CHECK_ONLY" -eq 1 ]]; then
  printf "Mode:     audit-only (--check; no changes)\n"
fi

# Initial audit.
audit_all || INITIAL_REQUIRED_MISSING=1
INITIAL_REQUIRED_MISSING=${INITIAL_REQUIRED_MISSING:-0}

if [[ "$CHECK_ONLY" -eq 1 ]]; then
  if [[ "$INITIAL_REQUIRED_MISSING" -eq 1 ]]; then
    err ""
    err "One or more required tools missing. Run without --check to install."
    exit 1
  fi
  printf "\n%bAll required tools present for selected layers.%b\n" "$c_green" "$c_reset"
  exit 0
fi

# Install.
if [[ "$LAYER_CORE" -eq 1 ]] && [[ "$INITIAL_REQUIRED_MISSING" -eq 1 ]]; then
  hdr "Installing core layer…"
  install_core
fi

if [[ "$LAYER_PROBE" -eq 1 ]]; then
  hdr "Installing analyse-codebase layer…"
  install_probe_layer
fi

if [[ "$LAYER_CODE_HEALTH" -eq 1 ]]; then
  hdr "Installing code-health layer (all optional)…"
  install_code_health
fi

if [[ "$LAYER_BROWSER" -eq 1 ]]; then
  hdr "Installing browser-proving layer (opt-in)…"
  install_browser_layer
fi

# Final audit.
hdr "Verification"
audit_all || FINAL_REQUIRED_MISSING=1
FINAL_REQUIRED_MISSING=${FINAL_REQUIRED_MISSING:-0}

if [[ "$FINAL_REQUIRED_MISSING" -eq 1 ]]; then
  err ""
  err "Required tools still missing after install attempts."
  show_manual_instructions
  exit 1
fi

printf "\n%bAll required tools installed. You're ready to use sulis.%b\n" "$c_green" "$c_reset"
echo ""
echo "Next steps:"
echo "  /plugin marketplace add sulis-ai/agents"
echo "  /plugin install sulis@sulis-ai-agents"
echo "  claude --agent sulis"
exit 0
