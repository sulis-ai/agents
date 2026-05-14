#!/usr/bin/env bash
# install-probe-tools.sh
#
# Installs the toolchain required by /sea:probe:
#   - ast-grep   (tree-sitter-based AST pattern matching)
#   - lizard     (cyclomatic complexity, multi-language)
#   - scc        (loc + complexity + dependency analysis)
#   - repomix    (optional — codebase serialisation for LLM ingest)
#
# Supports: macOS (brew), Debian/Ubuntu (apt + pip + npm/cargo), RHEL/Fedora
# (dnf + pip + npm/cargo). Other platforms: prints manual-install instructions.
#
# Usage:
#   bash install-probe-tools.sh          # install required tools
#   bash install-probe-tools.sh --check  # check only, don't install
#   bash install-probe-tools.sh --with-repomix  # also install the optional repomix
#
# Exit codes:
#   0  — all required tools present (or successfully installed)
#   1  — one or more required tools missing after install attempts
#   2  — unsupported platform; manual install required
#   3  — prerequisite missing (e.g. Homebrew on macOS); user must install it

set -euo pipefail

# ─── Configuration ─────────────────────────────────────────────────────────

REQUIRED_TOOLS=("ast-grep" "lizard" "scc")
OPTIONAL_TOOLS=("repomix")

INSTALL_REPOMIX=0
CHECK_ONLY=0

for arg in "$@"; do
  case "$arg" in
    --check)         CHECK_ONLY=1 ;;
    --with-repomix)  INSTALL_REPOMIX=1 ;;
    -h|--help)
      grep '^#' "$0" | sed 's/^# \?//'
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      exit 1
      ;;
  esac
done

# ─── Logging helpers ───────────────────────────────────────────────────────

c_green="\033[32m"; c_yellow="\033[33m"; c_red="\033[31m"; c_bold="\033[1m"; c_reset="\033[0m"

ok()   { printf "%b✓%b %s\n" "$c_green" "$c_reset" "$1"; }
warn() { printf "%b⚠%b %s\n" "$c_yellow" "$c_reset" "$1"; }
err()  { printf "%b✗%b %s\n" "$c_red" "$c_reset" "$1" >&2; }
info() { printf "%b…%b %s\n" "$c_bold" "$c_reset" "$1"; }

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
    else                                       PLATFORM="linux-other"
    fi
    ;;
esac

# ─── Tool detection ────────────────────────────────────────────────────────

is_installed() { command -v "$1" >/dev/null 2>&1; }

print_status() {
  local missing=0
  printf "\n%bTool status:%b\n" "$c_bold" "$c_reset"
  for t in "${REQUIRED_TOOLS[@]}"; do
    if is_installed "$t"; then ok "$t  (required)"; else err "$t  (required — missing)"; missing=1; fi
  done
  for t in "${OPTIONAL_TOOLS[@]}"; do
    if is_installed "$t"; then ok "$t  (optional)"; else warn "$t  (optional — not installed)"; fi
  done
  return $missing
}

# ─── Install routines ──────────────────────────────────────────────────────

install_macos() {
  if ! is_installed brew; then
    err "Homebrew is required on macOS but not found."
    err "Install Homebrew: https://brew.sh/"
    exit 3
  fi

  for t in "${REQUIRED_TOOLS[@]}"; do
    if ! is_installed "$t"; then
      info "Installing $t via brew…"
      brew install "$t"
    fi
  done

  if [[ "$INSTALL_REPOMIX" -eq 1 ]] && ! is_installed repomix; then
    if is_installed npm; then
      info "Installing repomix via npm…"
      npm install -g repomix
    else
      warn "npm not found; skipping repomix. Install Node.js for: npm install -g repomix"
    fi
  fi
}

install_debian() {
  # ast-grep — install via cargo (preferred) or npm
  if ! is_installed ast-grep; then
    if is_installed cargo; then
      info "Installing ast-grep via cargo…"
      cargo install ast-grep --locked
    elif is_installed npm; then
      info "Installing ast-grep via npm (global)…"
      npm install -g @ast-grep/cli
    else
      err "Need either cargo (rust) or npm to install ast-grep."
      err "Install rust: https://rustup.rs/  OR  apt-get install -y nodejs npm"
      exit 1
    fi
  fi

  # lizard — pip
  if ! is_installed lizard; then
    if is_installed pip3; then
      info "Installing lizard via pip3 (--user)…"
      pip3 install --user lizard
    elif is_installed pip; then
      info "Installing lizard via pip (--user)…"
      pip install --user lizard
    else
      err "pip not found. Try: sudo apt-get install -y python3-pip"
      exit 1
    fi
  fi

  # scc — go install or binary download
  if ! is_installed scc; then
    if is_installed go; then
      info "Installing scc via go install…"
      go install github.com/boyter/scc/v3@latest
    else
      warn "scc requires Go; falling back to manual."
      warn "Download a release from: https://github.com/boyter/scc/releases"
    fi
  fi

  if [[ "$INSTALL_REPOMIX" -eq 1 ]] && ! is_installed repomix; then
    if is_installed npm; then
      info "Installing repomix via npm…"
      npm install -g repomix
    else
      warn "npm not found; skipping repomix."
    fi
  fi
}

install_fedora() { install_debian; }   # same package-manager-agnostic logic
install_rhel()   { install_debian; }
install_arch()   { install_debian; }
install_other()  {
  err "Unsupported Linux variant. See manual-install instructions below."
  show_manual_instructions
  exit 2
}

show_manual_instructions() {
  cat <<EOF

Manual installation instructions:

  ast-grep:    https://ast-grep.github.io/guide/quick-start.html
               (brew install ast-grep  |  cargo install ast-grep --locked  |  npm i -g @ast-grep/cli)
  lizard:      pip install --user lizard
  scc:         https://github.com/boyter/scc/releases
               (brew install scc  |  go install github.com/boyter/scc/v3@latest)
  repomix:     npm install -g repomix   (optional)

Run this script again with --check after installing to verify.
EOF
}

# ─── Main ──────────────────────────────────────────────────────────────────

printf "%b/sea:probe toolchain installer%b\n" "$c_bold" "$c_reset"
printf "Platform: %s\n" "$PLATFORM"

if ! print_status; then
  if [[ "$CHECK_ONLY" -eq 1 ]]; then
    err "Required tools missing. Run without --check to install."
    exit 1
  fi

  printf "\n"; info "Installing missing required tools…"
  case "$PLATFORM" in
    macos)        install_macos ;;
    debian)       install_debian ;;
    fedora)       install_fedora ;;
    rhel)         install_rhel ;;
    arch)         install_arch ;;
    linux-other)  install_other ;;
    *)
      err "Unsupported platform: $OS"
      show_manual_instructions
      exit 2
      ;;
  esac
fi

# Re-verify after install
printf "\n%bVerification:%b\n" "$c_bold" "$c_reset"
final_missing=0
for t in "${REQUIRED_TOOLS[@]}"; do
  if is_installed "$t"; then
    ok "$t  ($(command -v "$t"))"
  else
    err "$t  still missing after install attempt"
    final_missing=1
  fi
done

for t in "${OPTIONAL_TOOLS[@]}"; do
  if is_installed "$t"; then
    ok "$t  ($(command -v "$t"))  (optional)"
  fi
done

if [[ "$final_missing" -eq 1 ]]; then
  err ""
  err "One or more required tools could not be installed automatically."
  show_manual_instructions
  exit 1
fi

printf "\n%bAll required tools installed.%b\n" "$c_green" "$c_reset"
echo "You can now run /sea:probe in any project directory."
exit 0
