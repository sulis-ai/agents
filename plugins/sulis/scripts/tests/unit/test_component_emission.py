"""Tests for `_component_emission.py`."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from _component_emission import compose_component_from_yaml, emit_component_from_yaml
from _entity_adapter_local import LocalFileEntityAdapter


_DESIGN = "dna:design:01ABCDEFGHJKMNPQRSTVWXYZ12"
_REQ = "dna:requirement:01BCDEFGHJKMNPQRSTVWXYZ123"


_COMPONENT = f"""
repo: github.com/sulis-ai/agents
path: plugins/sulis/scripts
version: 525b79d
license: MIT
implements:
  - {_DESIGN}
  - {_REQ}
dependencies:
  - pkg:pypi/jsonschema@4.21.1
  - pkg:npm/react@18.2.0
"""


class TestComposeComponent:
    def test_emits_one(self) -> None:
        result = compose_component_from_yaml(_COMPONENT, source_path="x")
        assert len(result) == 1
        c = result[0]
        assert re.fullmatch(r"^dna:component:[0-9A-HJKMNP-TV-Z]{26}$", c["id"])
        assert c["repo"] == "github.com/sulis-ai/agents"
        assert c["path"] == "plugins/sulis/scripts"
        assert c["version"] == "525b79d"
        assert c["license"] == "MIT"
        assert c["implements"] == [_DESIGN, _REQ]
        assert c["dependencies"] == ["pkg:pypi/jsonschema@4.21.1", "pkg:npm/react@18.2.0"]

    def test_deterministic_id_from_repo_and_path(self) -> None:
        a = compose_component_from_yaml(_COMPONENT, source_path="x")
        # Different version, same repo+path → same ID
        b_yaml = _COMPONENT.replace("525b79d", "abcdef0")
        b = compose_component_from_yaml(b_yaml, source_path="y")
        assert a[0]["id"] == b[0]["id"]
        assert a[0]["version"] != b[0]["version"]

    def test_missing_required_returns_empty(self) -> None:
        # missing version
        bad = "repo: x\npath: y\nlicense: MIT\n"
        assert compose_component_from_yaml(bad, source_path="x") == []

    def test_bad_implements_refs_filtered(self) -> None:
        c = compose_component_from_yaml(
            "repo: x\npath: y\nversion: z\nlicense: MIT\nimplements:\n  - not-a-ref\n",
            source_path="x",
        )
        # implements key only included if any clean refs survive
        assert "implements" not in c[0]


class TestEmitComponent:
    @pytest.fixture
    def adapter(self, tmp_path: Path) -> LocalFileEntityAdapter:
        return LocalFileEntityAdapter(
            base_dir=tmp_path / ".brain" / "instances",
            domain="product-development",
        )

    def test_persists(self, adapter: LocalFileEntityAdapter, tmp_path: Path) -> None:
        p = tmp_path / "comp.yaml"
        p.write_text(_COMPONENT)
        emitted = emit_component_from_yaml(p, adapter)
        ulid = emitted[0]["id"].split(":")[-1]
        assert (
            tmp_path / ".brain" / "instances" / "product-development" / "component" / f"{ulid}.jsonld"
        ).exists()
