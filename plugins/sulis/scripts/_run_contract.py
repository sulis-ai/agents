"""Run-contract resolver — how to stand the app up + where to reach it.

A repo-contract extension for the testable-state runner: the `commands.standup`
/ `commands.seed` recipe (put the app into a standing, seeded state locally) +
a `targets.{local,deployed}` block (the base URLs the runner exercises). This
is the concrete "local infra" contract — a Scenario can't be automated unless
the runner can stand the app up and reach it.

Pure resolver over the parsed repo-contract dict (the runner does the YAML I/O).

Stdlib only. Python 3.11-safe.
"""

from __future__ import annotations

from dataclasses import dataclass

_KNOWN_TARGETS = ("local", "deployed")


@dataclass
class RunContract:
    standup: str | None = None   # command to stand the app up locally
    seed: str | None = None      # command to seed/reset test data
    local_url: str | None = None
    deployed_url: str | None = None


def resolve_run_contract(contract: dict) -> RunContract:
    """Read the standup/seed recipe + the local/deployed target URLs from a
    parsed repo-contract dict. Absent fields resolve to None (the runner then
    defers the legs it can't reach)."""
    contract = contract or {}
    commands = contract.get("commands") or {}
    targets = contract.get("targets") or {}
    return RunContract(
        standup=commands.get("standup") or None,
        seed=commands.get("seed") or None,
        local_url=targets.get("local") or None,
        deployed_url=targets.get("deployed") or None,
    )


def target_url(rc: RunContract, target: str) -> str | None:
    """The base URL for a known target leg (`local` | `deployed`), or None."""
    if target == "local":
        return rc.local_url
    if target == "deployed":
        return rc.deployed_url
    return None  # unknown leg
