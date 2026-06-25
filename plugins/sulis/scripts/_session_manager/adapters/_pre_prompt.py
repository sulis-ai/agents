"""``_session_manager.adapters._pre_prompt`` — the shared CH-GJ9KQR pre-prompt
sidecar reader (EP-02 extracted primitive; WP-001, CH-M7WSQ4).

Both interactive pty adapters — Claude
(:mod:`~_session_manager.adapters.claude_pty`) and agy
(:mod:`~_session_manager.adapters.agy_pty`) — seed their session from the SAME
CH-GJ9KQR portable-context brief, read from the SAME launcher-written sidecar
(``~/.sulis/changes/{change_id}/pre_prompt.txt``). Before WP-001 only the Claude
adapter did this; WP-001's agy adapter is the second consumer, so the
byte-identical read/validate logic is extracted here rather than duplicated
(EP-02 REFACTOR step — extract the shared primitive at the 2-consumer threshold,
in the same PR, not "later").

The two properties this helper preserves (both load-bearing, both inherited by
every consumer for free):

- **Reuse the launcher's sidecar constant, not a copy (#86, EP-03).** The path is
  built from :data:`_terminal_launcher._PRE_PROMPT_SIDECAR`, so a re-point of the
  launcher's constant is followed here automatically — there is no duplicated
  literal to drift.
- **The change id rides the SessionSpec, never the ambient env (CH-GJ9KQR
  ADR-001).** Under the shared daemon the ambient ``SULIS_CHANGE_ID`` is constant
  across every spawned session, so reading the brief target from the env briefed
  every session for the daemon's start-time change. The target is
  ``spec.brief_change_id`` — the per-session change id the consumer already uses
  as the ``open()`` key — and the env is never consulted. The value is validated
  as a real change ULID before it is joined into a filesystem path (defence in
  depth, on top of ``SessionSpec.__post_init__``'s leading-``-`` / control-char
  guard) — a malformed value is ignored rather than turned into a path.
"""

from __future__ import annotations

from pathlib import Path

import _terminal_launcher
from _session_manager.adapter import SessionSpec
from _wpxlib import validate_change_ulid


def read_pre_prompt_sidecar(spec: SessionSpec) -> str | None:
    """Return the change's pre-prompt brief text iff ``spec.brief_change_id`` is a
    valid change ULID and the sidecar file exists; else ``None``.

    Shared by the Claude and agy interactive pty adapters — both pass the returned
    text as a single argv element (the manager spawns argv directly, no shell, so
    the brief's bytes are never shell-parsed; #86 / MUC-2). The change id comes
    from ``spec.brief_change_id`` (CH-GJ9KQR ADR-001), NOT the ambient
    ``SULIS_CHANGE_ID``."""
    change_id = (spec.brief_change_id or "").strip()
    if not change_id:
        return None
    ok, _reason = validate_change_ulid(change_id)
    if not ok:
        return None
    sidecar = (
        Path.home()
        / ".sulis"
        / "changes"
        / change_id
        / _terminal_launcher._PRE_PROMPT_SIDECAR
    )
    if not sidecar.is_file():
        return None
    return sidecar.read_text(encoding="utf-8")
