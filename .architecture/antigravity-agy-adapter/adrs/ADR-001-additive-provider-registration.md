---
id: ADR-001
title: Register the agy adapter additively under new provider keys, leaving the Claude "pty" key untouched
status: accepted
date: 2026-06-25
change: CH-M7WSQ4
---

# ADR-001 — Additive provider registration for agy

## Context

The session manager selects an adapter by `SessionSpec.provider`, looked up in the
`SessionManager._adapters` dict that the daemon composition root
(`session_manager_daemon.py::_build_server`) builds. Today that dict is
`{"pty": InteractiveClaudePtyAdapter()}` and the only consumer (`session_viewer.py`)
sends `provider="pty"`. The provider key is effectively an **io-model** name
("pty"), and that io-model currently resolves to Claude.

The spec requires agy to be a **selectable** target, **additive** to the Claude
registration, with the Claude path byte-for-byte unchanged.

## Decision

In the daemon composition root, add two new keys to the adapter dict pointing at a
single `InteractiveAgyPtyAdapter` instance:

```python
SessionManager(
    {
        "pty": _build_pty_adapter(),          # UNCHANGED — Claude
        "agy": agy_adapter,                    # NEW
        "antigravity": agy_adapter,            # NEW alias
    },
    start_maintenance=True,
)
```

The `"pty"` key keeps resolving to the Claude adapter exactly as before. A consumer
that wants agy sends `provider="agy"` (or `"antigravity"`). An unknown provider is
still the existing Expected `UNKNOWN_PROVIDER` error — no new error path.

## Alternatives considered

- **Rename `"pty"` → `"claude"` and make the io-model orthogonal.** Rejected: it
  changes the Claude path (the consumer's `provider="pty"` string would break),
  violating the byte-unchanged constraint, and is scope the spec explicitly fences
  off. The io-model-as-key naming is a pre-existing decision this change does not
  relitigate.
- **A separate registry/factory keyed by (provider, io-model) tuple.** Rejected as
  over-engineering for tier S: the manager already keys on a single string and the
  injection point is one dict literal. Adding a tuple-keyed registry is new
  architecture the one-adapter change does not justify (CP: boring beats clever).
- **Register only `"agy"`, no alias.** The `"antigravity"` alias is cheap (same
  instance) and the spec names both; keeping both removes a future rename.

## Consequences

- Adding agy is a one-line edit to the composition root plus the new adapter file —
  no manager, socket-server, or Claude-adapter change.
- The test posture must assert the Claude `"pty"` key still resolves to
  `InteractiveClaudePtyAdapter` after the edit (the no-regression check).
