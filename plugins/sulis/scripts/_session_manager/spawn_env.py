"""Spawn-env policy — the Rule-of-Two credential exclusion (WP-003).

SPEC §L1(d) / ADR-001: secrets are kept **out of the agent's fetch-path
environment**. This is the **primary** credential-exclusion control — the wall
that WP-002's outbound secret scrub merely braces (defence-in-depth). If a
credential is never in the child process's environment, it cannot be read into
an outbound request in the first place; the format-based scrub is the belt to
those braces, catching a value that nonetheless reaches a request line.

This module is the **pure policy**: given the parent environment, compute the
child environment the session is spawned with. ``_session_manager.manager.\
SessionManager._spawn_process`` applies it by passing the result as ``env=`` to
``subprocess.Popen`` (previously Popen inherited the full parent env). Keeping
the policy here — pure, no I/O, no global state — lets it be unit-tested in
isolation and keeps the ``_spawn_process`` diff minimal (the pipe/pty branch
logic is untouched).

The credential-name convention is the **same** one ``_secret_patterns`` uses for
its ``env-secret`` category: an env-var name ending in ``KEY`` / ``SECRET`` /
``TOKEN`` / ``PASSWORD`` / ``PASSWD`` (one source of truth for "what a
credential-bearing variable looks like"). Names not matching pass through
unchanged so the session still works (PATH, HOME, LANG, SULIS_* …).

Honest limit (recorded, ADR-001): excluding credential-*named* variables does
not make the agent's egress *impossible* — a hijacked process can still open a
raw socket; that wall is L3's (``l3-os-egress-denial``). This control removes
the credential from the fetch path; it is not the egress wall.
"""

from __future__ import annotations

from collections.abc import Mapping

# The env var the agent-facing tool (``_safe_fetch.tool``) reads to find the
# sanctioned proxy endpoint. Set in the child env at spawn time. ``SULIS_``
# prefix matches the established convention for this codebase's env surface.
PROXY_ENDPOINT_ENV = "SULIS_SAFE_FETCH_PROXY"

# Credential-bearing name suffixes — the SAME convention as
# ``_secret_patterns``' ``env-secret`` category (KEY / SECRET / TOKEN /
# PASSWORD / PASSWD). A name ending in any of these is treated as carrying a
# credential and is excluded from the child environment.
_CREDENTIAL_SUFFIXES = ("KEY", "SECRET", "TOKEN", "PASSWORD", "PASSWD")

# Well-known credential variables whose names do NOT end in a catalogued suffix
# and so would otherwise pass the suffix check — closing the gap that
# ``AWS_ACCESS_KEY_ID`` (ends ``ID``), ``GOOGLE_APPLICATION_CREDENTIALS`` (ends
# ``CREDENTIALS``), and ``SSH_AUTH_SOCK`` (a path to the SSH agent socket — a
# live credential channel) would each slip through. An explicit boring allowlist
# of the credential names common in a CI / dev environment (CP-01); extend it as
# new credential-bearing variables appear. Whole-name match, case-insensitive.
_CREDENTIAL_EXACT_NAMES = frozenset(
    {
        "AWS_ACCESS_KEY_ID",
        "AWS_SESSION_TOKEN",  # also caught by suffix; listed for completeness
        "GOOGLE_APPLICATION_CREDENTIALS",
        "SSH_AUTH_SOCK",
        "AZURE_CLIENT_CERTIFICATE_PASSWORD",  # suffix-caught; documented here too
        "DOCKER_AUTH_CONFIG",
    }
)


def is_credential_var(name: str) -> bool:
    """Whether the env var ``name`` is credential-bearing by name convention.

    True when the upper-cased name (a) ends in one of the catalogued credential
    suffixes (``*_KEY`` / ``*_SECRET`` / ``*_TOKEN`` / ``*_PASSWORD`` /
    ``*_PASSWD``, and the bare suffix itself, e.g. ``SECRET``), mirroring the
    ``_secret_patterns`` env-secret naming so there is one definition of "looks
    like a credential variable"; OR (b) is one of the well-known
    credential-variable names whose form does not end in a suffix
    (:data:`_CREDENTIAL_EXACT_NAMES`, e.g. ``AWS_ACCESS_KEY_ID``,
    ``GOOGLE_APPLICATION_CREDENTIALS``, ``SSH_AUTH_SOCK``).
    """
    upper = name.upper()
    if upper in _CREDENTIAL_EXACT_NAMES:
        return True
    return any(upper.endswith(suffix) for suffix in _CREDENTIAL_SUFFIXES)


def child_spawn_env(
    parent_env: Mapping[str, str],
    *,
    proxy_endpoint: str | None,
    change_id: str | None = None,
) -> dict[str, str]:
    """Compute the child environment for a spawned agent session.

    Returns a NEW dict (the ``parent_env`` is never mutated) that:

    1. **excludes** every credential-bearing variable (:func:`is_credential_var`)
       — the Rule-of-Two control (SPEC §L1(d)): the credential is not in the
       fetch path's scope, so it cannot be read into an outbound request;
    2. **sets** :data:`PROXY_ENDPOINT_ENV` to ``proxy_endpoint`` when one is
       supplied (``None`` → not set, e.g. a session spawned before the proxy is
       wired — the credential exclusion is unconditional regardless);
    3. **passes through** every other variable unchanged, so PATH/HOME/LANG and
       the session's own ``SULIS_*`` context still reach the child and normal
       work is unaffected;
    4. **stamps** ``SULIS_CHANGE_ID`` per spawn from ``change_id`` (this change's
       ADR-001): when ``change_id`` is supplied it **overrides** any inherited
       value (the session carries its own target change, never the daemon's
       launch-time value); when ``change_id`` is ``None`` (the default) it
       **removes** ``SULIS_CHANGE_ID`` from the child so a session with no bound
       change does not silently adopt a stale inherited one. Callers must opt in
       to a target by passing ``change_id``.
    """
    child = {
        name: value for name, value in parent_env.items() if not is_credential_var(name)
    }
    if proxy_endpoint is not None:
        child[PROXY_ENDPOINT_ENV] = proxy_endpoint
    if change_id:
        child["SULIS_CHANGE_ID"] = change_id
    else:
        child.pop("SULIS_CHANGE_ID", None)
    return child
