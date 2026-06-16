"""WP-004 — sandbox-enable recipe: the locus-iii backstop, single-sourced (SC-E5/E6).

Phase 4 is doc/config: Claude Code SHIPS the OS sandbox (Seatbelt/bubblewrap);
Sulis does not build one — it ships a recipe + safe defaults that ENABLE it.

These tests pin the two drift-proof guarantees and the honesty discipline:

  * the sandbox ``filesystem.allowWrite`` list is GENERATED from
    ``_file_scope.sandbox_write_roots`` (WP-002), never a hand-maintained second
    list — so it cannot drift from the L2 file-tools scope (ADR-004 single
    source of truth);
  * the emitted defaults match the verified Claude Code sandbox contract:
    ``denyRead`` on credential dirs, ``allowedDomains`` = the proxy egress host
    ONLY, and the consumer-managed STRICT variant
    (``failIfUnavailable``/``allowUnsandboxedCommands:false``);
  * the recipe doc exists and labels its enforcement-locus (iii / OS) and
    threat-scope honestly: GAP-alpha (accidental over-reach) closed only when
    enabled; GAP-beta (TLS-aware egress / deliberate exfil) DEFERRED; operator-
    proof (SC-E9) + the sandbox-blocks half of SC-E7 + SC-E8 labelled
    deferred-attested, NOT claimed green.

SULIS_STATE_DIR is redirected to tmp so the change-state roots resolve under the
test dir (mirrors test_write_roots_resolver.py).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[2]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _change_state import change_worktree_dir  # noqa: E402
from _file_scope import resolve_allowed_roots, sandbox_write_roots  # noqa: E402
from _sandbox_config import build_sandbox_config, emit_sandbox_config  # noqa: E402

_CID = "0123456789ABCDEFGHJKMNPQRS"
_PROXY = "egress.proxy.internal"

# The recipe doc — a shippable plugin reference (versions with the plugin).
_RECIPE = (
    Path(__file__).resolve().parents[3] / "references" / "sandbox-enable-recipe.md"
)


@pytest.fixture(autouse=True)
def _state_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path))
    monkeypatch.delenv("SULIS_BRAIN_BASE_DIR", raising=False)
    return tmp_path


@pytest.fixture
def repo_root(tmp_path):
    rr = tmp_path / "repo"
    rr.mkdir(parents=True, exist_ok=True)
    # Make the change worktree exist so resolve_allowed_roots has a real tree.
    change_worktree_dir(_CID).mkdir(parents=True, exist_ok=True)
    return rr


# ─── the single-source guarantee (the whole point of WP-004) ─────────────────


def test_allow_write_is_generated_from_resolver(repo_root):
    """``allowWrite`` is EXACTLY ``sandbox_write_roots(resolver output)`` — no
    hand-maintained second list. This is the drift-proof contract: the recipe's
    writable paths and the L2 file-tools scope derive from one ``AllowedRoots``.
    """
    roots = resolve_allowed_roots(_CID, repo_root=repo_root)
    cfg = build_sandbox_config(
        roots, proxy_egress_host=_PROXY, strict=False
    )
    assert cfg["filesystem"]["allowWrite"] == sandbox_write_roots(roots)


def test_allow_write_not_hand_duplicated(repo_root):
    """A change in the resolver's rw root-set flows through to ``allowWrite``
    with no separate edit — the emitter holds NO literal path of its own.
    """
    roots = resolve_allowed_roots(_CID, repo_root=repo_root)
    cfg = build_sandbox_config(roots, proxy_egress_host=_PROXY, strict=False)
    # Every emitted writable path is one the resolver produced; nothing extra.
    assert set(cfg["filesystem"]["allowWrite"]) == set(sandbox_write_roots(roots))


def test_emit_wrapper_resolves_and_matches(repo_root):
    """The convenience wrapper resolves roots from change_id+repo_root and emits
    the same config the explicit-roots path does (one code path)."""
    roots = resolve_allowed_roots(_CID, repo_root=repo_root)
    via_wrapper = emit_sandbox_config(
        _CID, repo_root=repo_root, proxy_egress_host=_PROXY, strict=False
    )
    via_roots = build_sandbox_config(roots, proxy_egress_host=_PROXY, strict=False)
    assert via_wrapper == via_roots


# ─── the verified Claude Code sandbox contract (safe defaults) ───────────────


def test_sandbox_enabled(repo_root):
    roots = resolve_allowed_roots(_CID, repo_root=repo_root)
    cfg = build_sandbox_config(roots, proxy_egress_host=_PROXY, strict=False)
    assert cfg["enabled"] is True


def test_deny_read_creds(repo_root):
    """Credential dirs are denyRead — the default read policy allows them unless
    denied (verified in the sandbox docs)."""
    roots = resolve_allowed_roots(_CID, repo_root=repo_root)
    cfg = build_sandbox_config(roots, proxy_egress_host=_PROXY, strict=False)
    deny = cfg["filesystem"]["denyRead"]
    assert "~/.aws" in deny
    assert "~/.ssh" in deny


def test_allowed_domains_proxy_only(repo_root):
    """``allowedDomains`` = the safe-fetch proxy egress host ONLY — never a broad
    allowlist (a broad one is the GAP-beta domain-fronting exfil surface)."""
    roots = resolve_allowed_roots(_CID, repo_root=repo_root)
    cfg = build_sandbox_config(roots, proxy_egress_host=_PROXY, strict=False)
    assert cfg["network"]["allowedDomains"] == [_PROXY]


def test_strict_variant_managed_keys(repo_root):
    """The consumer-managed STRICT variant adds the operator-proof keys."""
    roots = resolve_allowed_roots(_CID, repo_root=repo_root)
    cfg = build_sandbox_config(roots, proxy_egress_host=_PROXY, strict=True)
    assert cfg["failIfUnavailable"] is True
    assert cfg["allowUnsandboxedCommands"] is False


def test_non_strict_omits_managed_keys(repo_root):
    """Non-strict (the shipped default) does NOT impose the managed keys — only a
    consumer can make it operator-proof (SC-E9); Sulis ships defaults, not
    managed settings."""
    roots = resolve_allowed_roots(_CID, repo_root=repo_root)
    cfg = build_sandbox_config(roots, proxy_egress_host=_PROXY, strict=False)
    assert "failIfUnavailable" not in cfg
    assert "allowUnsandboxedCommands" not in cfg


# ─── honesty labelling on the recipe doc (SC-E6 surface) ─────────────────────


def test_recipe_doc_exists():
    assert _RECIPE.is_file(), f"recipe doc missing at {_RECIPE}"


def test_recipe_labels_locus_and_threat_scope():
    text = _RECIPE.read_text(encoding="utf-8")
    # locus-iii (OS) — the only layer catching subprocess bypass.
    assert "locus iii" in text.lower() or "locus-iii" in text.lower()
    # GAP-alpha closed (accidental); GAP-beta deferred (TLS exfil).
    assert "GAP-α" in text or "GAP-alpha" in text.lower()
    assert "GAP-β" in text or "GAP-beta" in text.lower()
    assert "deferred" in text.lower()


def test_recipe_labels_operator_proof_and_attested_deferrals():
    text = _RECIPE.read_text(encoding="utf-8")
    # operator-proof = consumer-managed (SC-E9); SC-E7 sandbox half + SC-E8 attested.
    assert "SC-E9" in text
    assert "SC-E7" in text
    assert "SC-E8" in text
    # Names the consumer-managed requirement honestly.
    assert "managed" in text.lower()


def test_recipe_instructs_generate_not_handwrite():
    """The recipe MUST tell the operator to GENERATE allowWrite from the
    resolver (run the emitter), not hand-type a path list — the single-source
    discipline made operational."""
    text = _RECIPE.read_text(encoding="utf-8")
    assert "sandbox_write_roots" in text
    assert "sulis-sandbox-config" in text
