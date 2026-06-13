"""L1 safe-fetch package — the agent's only sanctioned outbound path.

This package holds the L1 layer of the harden-agent-execution-boundary change:
a mediated fetch/search gateway so the agent has no raw outbound socket. WP-001
lands only the **contract** — the typed ports the rest of the layer is built
against (``ports``). The production proxy adapter, the agent-facing tool, and
the untrusted-data framing land in WP-002/003.

See ``_safe_fetch.ports`` for the seam definitions and the Stripe-rule note on
why these are ports the domain owns, not Wraps.
"""

from __future__ import annotations
