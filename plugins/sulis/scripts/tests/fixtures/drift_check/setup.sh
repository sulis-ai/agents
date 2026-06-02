#!/usr/bin/env bash
# setup.sh — reproducibly (re)create the drift_check fixture git remotes
# (WP-009 DoD Blue: "Fixture local git remotes are reproducible").
#
# The drift-check unit/integration tests build their scripted remotes on
# the fly inside a mktemp dir (so parallel runs never collide). This
# script is the canonical, documented recipe for those remotes — it
# materialises them under fixtures/drift_check/ for inspection /
# debugging, and CI can call it to verify the recipe still works.
#
# Two remotes are produced:
#   repo-clean/origin.git   — origin/main is an ANCESTOR of origin/dev
#                             (no drift; drift_check.sh exits 0).
#   repo-drifted/origin.git — origin/dev is BEHIND origin/main
#                             (drift; drift_check.sh exits 1).
#
# Idempotent: removes and rebuilds the .git remotes each run.
#
# Usage:  bash fixtures/drift_check/setup.sh
# bash-3.2-safe.

set -u
set -o pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

_git() { git -c user.email="fixture@example.com" -c user.name="Fixture" "$@"; }

build_clean() {
    local root="$HERE/repo-clean"
    rm -rf "$root/origin.git" "$root/.work"
    git init --bare --initial-branch=main "$root/origin.git" >/dev/null
    _git clone --quiet "$root/origin.git" "$root/.work"
    (
        cd "$root/.work"
        echo "seed" > seed.txt
        _git add seed.txt
        _git commit --quiet -m "seed main"
        _git push --quiet origin main
        # dev branches off main at the same commit → main is an ancestor.
        _git checkout -b dev
        _git push --quiet origin dev
    )
    rm -rf "$root/.work"
}

build_drifted() {
    local root="$HERE/repo-drifted"
    rm -rf "$root/origin.git" "$root/.work"
    git init --bare --initial-branch=main "$root/origin.git" >/dev/null
    _git clone --quiet "$root/origin.git" "$root/.work"
    (
        cd "$root/.work"
        echo "seed" > seed.txt
        _git add seed.txt
        _git commit --quiet -m "seed main"
        _git push --quiet origin main
        # dev at the seed point...
        _git checkout -b dev
        _git push --quiet origin dev
        # ...then main advances past dev → dev is behind main (drift).
        _git checkout main
        echo "post-release" > release.txt
        _git add release.txt
        _git commit --quiet -m "advance main past dev (post-release state)"
        _git push --quiet origin main
    )
    rm -rf "$root/.work"
}

build_clean
build_drifted

echo "OK: rebuilt fixtures/drift_check/{repo-clean,repo-drifted}/origin.git"
