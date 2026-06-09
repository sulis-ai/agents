"""plugin_version() — the installed Sulis plugin version, read from the nearest
``.claude-plugin/plugin.json`` above this file.

Used by the daemon version-skew guard (#102): the session daemon is a singleton
that survives plugin updates, so a viewer from a NEW plugin version can connect
to a daemon still running OLD code (the crash/hang we hit). The daemon stamps
its version in its ``status`` reply; ``ensure_daemon`` compares it to its OWN
version and restarts the daemon on a mismatch, so the two always run the same
code.

Reading ``plugin.json`` (rather than parsing the version out of the cache path)
works identically in the versioned plugin cache (``…/sulis/{ver}/scripts/``) AND
the dev tree (``plugins/sulis/scripts/``) — both carry the version in
``plugin.json`` — so the dev tree returns its own version (and a dev↔dev compare
never triggers a spurious restart). Stdlib only. Python 3.11-safe.
"""

from __future__ import annotations

import json
from pathlib import Path


def plugin_version(start: str | None = None) -> str | None:
    """Return the sulis plugin version from the nearest ``.claude-plugin/
    plugin.json`` at or above ``start`` (defaults to this file's location), or
    ``None`` if not found / unreadable.

    ``scripts/`` sits at ``plugins/sulis/scripts/``; the manifest is one level
    up at ``plugins/sulis/.claude-plugin/plugin.json``. Ascends defensively in
    case of layout drift.
    """
    here = Path(start or __file__).resolve()
    for parent in here.parents:
        cand = parent / ".claude-plugin" / "plugin.json"
        if cand.is_file():
            try:
                ver = json.loads(cand.read_text(encoding="utf-8")).get("version")
            except (ValueError, OSError):
                return None
            return str(ver) if ver else None
    return None
