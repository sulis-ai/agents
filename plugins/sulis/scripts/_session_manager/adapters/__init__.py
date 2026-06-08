"""``_session_manager.adapters`` — concrete provider adapters.

One module per agent CLI, each implementing the :class:`ProviderAdapter`
Protocol (``_session_manager.adapter``, §2.4). Claude is adapter #1
(:mod:`_session_manager.adapters.claude`); Codex / Gemini are future modules
that slot in here with zero change to the manager or either consumer.
"""

from __future__ import annotations

from _session_manager.adapters.claude import ClaudeAdapter

__all__ = ["ClaudeAdapter"]
