"""WP-003 (testable-state-done) — the run-contract resolver.

Automating a Scenario needs to know HOW to stand the app up locally and WHERE
to reach it (local + deployed). That's a repo-contract extension: a
`commands.standup` / `commands.seed` recipe + a `targets.{local,deployed}`
block. This is the concrete "local infra" contract the runner reads to put the
app into a testable state before running steps.

Pure resolver over the parsed repo-contract dict.

Stdlib + pytest. Python 3.11-safe.
"""

from __future__ import annotations

from _run_contract import resolve_run_contract, target_url


def test_resolves_standup_seed_and_targets():
    rc = resolve_run_contract({
        "commands": {"standup": "docker compose up -d", "seed": "npm run seed"},
        "targets": {"local": "http://localhost:5173", "deployed": "https://app.example.com"},
    })
    assert rc.standup == "docker compose up -d"
    assert rc.seed == "npm run seed"
    assert rc.local_url == "http://localhost:5173"
    assert rc.deployed_url == "https://app.example.com"


def test_missing_blocks_resolve_to_none():
    rc = resolve_run_contract({})
    assert rc.standup is None and rc.seed is None
    assert rc.local_url is None and rc.deployed_url is None


def test_target_url_selects_leg():
    rc = resolve_run_contract({"targets": {"local": "http://l", "deployed": "https://d"}})
    assert target_url(rc, "local") == "http://l"
    assert target_url(rc, "deployed") == "https://d"


def test_target_url_none_when_leg_absent():
    rc = resolve_run_contract({"targets": {"local": "http://l"}})
    assert target_url(rc, "deployed") is None


def test_target_url_rejects_unknown_leg():
    rc = resolve_run_contract({"targets": {"local": "http://l"}})
    assert target_url(rc, "staging") is None
