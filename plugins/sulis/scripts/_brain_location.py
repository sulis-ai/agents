"""brain_base_dir — the single, user-configurable resolver for where the brain
lives (#127).

ONE place decides the brain's location, honoured by every call site (the emit
helper, the change-entity wiring, product resolution) so the location is
*uniformly* configurable — closing the gap where the emitters honoured
SULIS_BRAIN_BASE_DIR but the change-entity wiring hard-coded `<repo>/.brain`.

Resolution order (first match wins):
  1. an explicit path a caller already holds
  2. `SULIS_BRAIN_BASE_DIR` env — a transient override
  3. the repo-contract `brain_location` field (`.sulis/repo-contract.yml`) —
     the PERSISTENT, user-set location; may point at any dir, or the user's own
     repo (the spiral's local-first / server-deferred shape; a repo + a
     contribution flow is then a free consequence)
  4. default `<repo_root>/.brain/instances` — UNCHANGED, non-disruptive: Sulis's
     own committed brain stays put; a user sets `brain_location` to relocate.

A relative configured/env path resolves against `repo_root`; `~` expands. The
default is deliberately kept so this change orphans nothing.
"""

from __future__ import annotations

import os
from pathlib import Path


def _resolve(repo_root: Path, raw: str) -> Path:
    p = Path(str(raw).strip()).expanduser()
    return p if p.is_absolute() else (repo_root / p)


def _from_contract(repo_root: Path) -> "str | None":
    """The repo-contract `brain_location` field, or None (best-effort — a
    missing/unreadable contract or absent field just falls through)."""
    try:
        import sys
        here = str(Path(__file__).resolve().parent)
        if here not in sys.path:
            sys.path.insert(0, here)
        from _wpxlib import read_repo_contract

        val = read_repo_contract(repo_root).get("brain_location")
        return str(val).strip() if val else None
    except Exception:  # noqa: BLE001 — config is optional; never break resolution
        return None


def brain_base_dir(repo_root, *, explicit: "str | None" = None) -> Path:
    """Resolve the brain instances dir for `repo_root` (see module docstring)."""
    repo_root = Path(repo_root)
    if explicit:
        return _resolve(repo_root, explicit)
    env = os.environ.get("SULIS_BRAIN_BASE_DIR", "").strip()
    if env:
        return _resolve(repo_root, env)
    configured = _from_contract(repo_root)
    if configured:
        return _resolve(repo_root, configured)
    return repo_root / ".brain" / "instances"
