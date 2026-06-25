"""``_session_manager.adapters`` — concrete provider adapters.

One module per agent CLI, each implementing the :class:`ProviderAdapter`
Protocol (``_session_manager.adapter``, §2.4). Claude is adapter #1
(:mod:`_session_manager.adapters.claude`); the interactive Google Antigravity
(``agy``) pty adapter (:mod:`_session_manager.adapters.agy_pty`) is the second
provider — it slots in here with zero change to the manager or either consumer,
exactly the contract's "a new provider is one new file" guarantee. Codex / Gemini
are future modules that slot in the same way.
"""

from __future__ import annotations

from _session_manager.adapters.agy_pty import InteractiveAgyPtyAdapter
from _session_manager.adapters.claude import ClaudeAdapter

__all__ = ["ClaudeAdapter", "InteractiveAgyPtyAdapter"]
