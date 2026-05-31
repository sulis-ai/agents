"""Tests for `_credential_emission.py`."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from _credential_emission import compose_credential, emit_credential
from _entity_adapter_local import LocalFileEntityAdapter
from _entity_repository import EntityValidationError


_HOLDER = "dna:actor:01ABCDEFGHJKMNPQRSTVWXYZ12"


class TestComposeCredential:
    def test_minimum_valid(self) -> None:
        c = compose_credential(
            holder=_HOLDER, kind="api-key",
            token_ref="secret://credential/ci-deploy",
        )
        assert re.fullmatch(r"^dna:credential:[0-9A-HJKMNP-TV-Z]{26}$", c["id"])
        assert c["kind"] == "api-key"
        assert c["holder"] == _HOLDER
        assert c["state"] == "active"
        assert c["sys_status"] == "active"

    def test_optional_fields_emitted_when_provided(self) -> None:
        c = compose_credential(
            holder=_HOLDER, kind="oauth", token_ref="secret://x",
            issuer="github", scope="repo:write",
            issued_at="2026-05-30T00:00:00Z",
            expires_at="2027-05-30T00:00:00Z",
        )
        assert c["issuer"] == "github"
        assert c["scope"] == "repo:write"
        assert c["issued_at"] == "2026-05-30T00:00:00Z"
        assert c["expires_at"] == "2027-05-30T00:00:00Z"

    def test_invalid_kind_raises(self) -> None:
        with pytest.raises(ValueError, match="kind"):
            compose_credential(holder=_HOLDER, kind="bogus", token_ref="x")

    def test_invalid_state_raises(self) -> None:
        with pytest.raises(ValueError, match="state"):
            compose_credential(
                holder=_HOLDER, kind="api-key", token_ref="x", state="bogus"
            )

    def test_invalid_holder_raises(self) -> None:
        with pytest.raises(ValueError, match="holder"):
            compose_credential(holder="not-an-actor-id", kind="api-key", token_ref="x")

    def test_empty_token_ref_raises(self) -> None:
        with pytest.raises(ValueError, match="token_ref"):
            compose_credential(holder=_HOLDER, kind="api-key", token_ref="")


class TestEmitCredential:
    @pytest.fixture
    def adapter(self, tmp_path: Path) -> LocalFileEntityAdapter:
        return LocalFileEntityAdapter(
            base_dir=tmp_path / ".brain" / "instances",
            domain="foundation",
        )

    def test_persists(self, adapter: LocalFileEntityAdapter, tmp_path: Path) -> None:
        c = emit_credential(
            repo=adapter, holder=_HOLDER, kind="api-key",
            token_ref="secret://credential/ci",
        )
        ulid = c["id"].split(":")[-1]
        assert (
            tmp_path / ".brain" / "instances" / "foundation" / "credential" / f"{ulid}.jsonld"
        ).exists()
