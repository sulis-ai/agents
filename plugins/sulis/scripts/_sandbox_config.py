"""WP-004 — emit the Claude Code OS-sandbox config block (locus iii, Phase 4).

Claude Code SHIPS the OS sandbox (macOS Seatbelt / Linux bubblewrap). Sulis does
NOT build one — this module emits the ``settings.json`` ``sandbox`` block that
ENABLES it with safe defaults, so the operator pastes a generated block instead
of hand-maintaining a path list that would drift from the L2 file-tools scope.

The ONE thing this module must never do is hold its own copy of the writable
roots: ``filesystem.allowWrite`` is taken verbatim from
:func:`_file_scope.sandbox_write_roots`, which reads the SAME ``AllowedRoots``
the file-tools scope check uses (ADR-004 single source of truth, SC-E5). This
module's only literals are the credential deny-read list, the network shape, and
the consumer-managed strict keys — none of which are writable-path state.

Enforcement-locus / threat-scope (the honesty primitive, TDD §Armor):
  * **locus iii (OS)** — the only layer that catches a spawned subprocess
    (`python -c 'urllib…'`, obfuscated curl) the harness hook never sees.
  * **GAP-α (accidental over-reach)** — closed *when the sandbox is enabled*.
  * **GAP-β (TLS-aware egress / deliberate exfil via a permitted domain)** —
    **DEFERRED**; the sandbox proxy does not inspect TLS, so a broad
    ``allowedDomains`` permits domain-fronting. We emit the proxy egress host
    ONLY, and name GAP-β rather than claim it closed.
  * **operator-proof (SC-E9)** — needs consumer-applied *managed* settings;
    Sulis ships defaults + recipe, cannot impose. The strict keys are emitted
    only when ``strict=True`` (the consumer-managed variant).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from _file_scope import AllowedRoots, resolve_allowed_roots, sandbox_write_roots

# Credential directories the sandbox must deny reads on. The sandbox's default
# read policy allows these unless explicitly denied (verified in the Claude Code
# sandboxing docs), so an enabled sandbox without these would leave creds
# readable by a spawned subprocess. These are deny-READ entries, NOT writable
# roots — they never come from the resolver.
CREDENTIAL_DENY_READ: tuple[str, ...] = ("~/.aws", "~/.ssh")


def build_sandbox_config(
    roots: AllowedRoots,
    *,
    proxy_egress_host: str,
    strict: bool = False,
) -> dict[str, Any]:
    """Build the ``sandbox`` settings block from a resolved ``AllowedRoots``.

    ``filesystem.allowWrite`` is :func:`sandbox_write_roots` of ``roots`` — the
    SAME rw root set the L2 file-tools scope check permits for a mutating op, so
    the config and the scope check cannot drift (single source of truth).

    ``network.allowedDomains`` is the safe-fetch proxy egress host ONLY — never a
    broad allowlist (a broad one is the GAP-β domain-fronting exfil surface).

    When ``strict`` is set, the consumer-managed operator-proof keys
    (``failIfUnavailable`` / ``allowUnsandboxedCommands:false``) are added; these
    only bind when applied as *managed* settings (SC-E9), which only a consumer
    can do — Sulis ships the recipe, not the managed policy.
    """
    config: dict[str, Any] = {
        "enabled": True,
        "filesystem": {
            "allowWrite": sandbox_write_roots(roots),
            "denyRead": list(CREDENTIAL_DENY_READ),
        },
        "network": {
            "allowedDomains": [proxy_egress_host],
        },
    }
    if strict:
        # Consumer-managed strict variant (SC-E9). Emitted, not imposed.
        config["failIfUnavailable"] = True
        config["allowUnsandboxedCommands"] = False
    return config


def emit_sandbox_config(
    change_id: str,
    *,
    repo_root: Path,
    proxy_egress_host: str,
    strict: bool = False,
) -> dict[str, Any]:
    """Resolve the allowlist for ``change_id`` and emit the sandbox config.

    Convenience wrapper over :func:`build_sandbox_config`: resolves the canonical
    ``AllowedRoots`` (the single source) then emits — one code path, so the
    wrapper and the explicit-roots form can never diverge. Scope is derived from
    ``change_id`` + ``repo_root`` (the launch environment), never from a caller-
    supplied path list.
    """
    roots = resolve_allowed_roots(change_id, repo_root=Path(repo_root))
    return build_sandbox_config(
        roots, proxy_egress_host=proxy_egress_host, strict=strict
    )
