"""Unit tests for wpx-render-contract internal seams (WP-001).

Exercises the parser/builder functions and the CLI command in-process
(loading the extension-less script as a module) to cover the discovery,
degradation, path-safety, and synthesis branches that the keystone
end-to-end tests touch only indirectly.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import types
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_SCRIPTS_DIR = _HERE.parent.parent
_FIXTURES = _HERE.parent / "fixtures" / "render_contract"
_RENDERER_SRC = _SCRIPTS_DIR / "wpx-render-contract"


@pytest.fixture(scope="module")
def rc() -> types.ModuleType:
    """Load the extension-less renderer script as an importable module."""
    spec = importlib.util.spec_from_loader("wpx_render_contract", loader=None)
    mod = importlib.util.module_from_spec(spec)
    mod.__dict__["__name__"] = "wpx_render_contract"
    mod.__dict__["__file__"] = str(_RENDERER_SRC)
    # Register in sys.modules BEFORE exec so @dataclass can resolve the module
    # (dataclasses look up sys.modules[cls.__module__] for InitVar handling).
    sys.modules["wpx_render_contract"] = mod
    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))
    exec(compile(_RENDERER_SRC.read_text(), str(_RENDERER_SRC), "exec"), mod.__dict__)
    return mod


# ─── format sniffing / discovery ────────────────────────────────────────────


def test_sniff_yaml_openapi(rc, tmp_path):
    p = tmp_path / "openapi.yaml"
    p.write_text("openapi: 3.0.3\ninfo:\n  title: Y\n", encoding="utf-8")
    assert rc._sniff_format(p) == "openapi"


def test_sniff_swagger_yaml(rc, tmp_path):
    p = tmp_path / "swagger.yaml"
    p.write_text("swagger: '2.0'\n", encoding="utf-8")
    assert rc._sniff_format(p) == "openapi"


def test_sniff_non_json_non_yaml_is_raw(rc, tmp_path):
    p = tmp_path / "thing.yaml"
    p.write_text("just: some\nplain: yaml\n", encoding="utf-8")
    assert rc._sniff_format(p) == "raw"


def test_sniff_unreadable_returns_none(rc, tmp_path):
    p = tmp_path / "bin.json"
    p.write_bytes(b"\xff\xfe\x00\x01")
    assert rc._sniff_format(p) is None


def test_locate_prefers_servicespec_over_openapi(rc, tmp_path):
    shutil.copy(_FIXTURES / "fixtureB_minimal.jsonld", tmp_path / "spec.jsonld")
    shutil.copy(_FIXTURES / "openapi_no_tags.json", tmp_path / "openapi.json")
    found = rc.locate_contracts(tmp_path)
    assert [f for _, f in found] == ["servicespec", "openapi"]


def test_locate_raw_only_when_no_structured(rc, tmp_path):
    shutil.copy(_FIXTURES / "raw_contract.json", tmp_path / "data-contract.json")
    found = rc.locate_contracts(tmp_path)
    assert [f for _, f in found] == ["raw"]


# ─── form-field projection ───────────────────────────────────────────────────


def test_build_form_fields_skips_hidden(rc):
    schema = {"properties": {"a": {"type": "string"}, "secret": {"type": "string", "hidden": True}}}
    names = [f.name for f in rc.build_form_fields(schema)]
    assert names == ["a"]


def test_build_form_fields_bare_property_basic_field(rc):
    fields = rc.build_form_fields({"properties": {"foo_bar": {"type": "integer"}}})
    assert len(fields) == 1
    assert fields[0].label == "Foo bar"        # humanised
    assert fields[0].input_type == "number"


def test_build_form_fields_non_object_returns_empty(rc):
    assert rc.build_form_fields(None) == []
    assert rc.build_form_fields({"type": "string"}) == []


def test_synthesise_example_handles_types(rc):
    ex = rc.synthesise_example({"properties": {
        "s": {"type": "string"},
        "n": {"type": "integer"},
        "e": {"enum": ["x", "y"]},
    }})
    assert ex["n"] == 0
    assert ex["e"] == "x"


def test_synthesise_example_empty(rc):
    assert rc.synthesise_example({"properties": {}}) is None
    assert rc.synthesise_example(None) is None


# ─── area derivation ─────────────────────────────────────────────────────────


def test_area_from_key(rc):
    assert rc._area_from_key("platform/create-platform") == "platform"
    assert rc._area_from_key("ping") is None


# ─── CLI command (in-process) ────────────────────────────────────────────────


def _args(rc, **kw):
    ns = rc.argparse.Namespace(worktree=None, out=None)
    for k, v in kw.items():
        setattr(ns, k, v)
    return ns


def test_cmd_render_missing_worktree_exits_1(rc, tmp_path):
    with pytest.raises(SystemExit) as exc:
        rc.cmd_render(_args(rc, worktree=str(tmp_path / "absent")))
    assert exc.value.code == 1


def test_cmd_render_empty_worktree_renders_none(rc, tmp_path, capsys):
    wt = tmp_path / "wt"
    wt.mkdir()
    with pytest.raises(SystemExit) as exc:
        rc.cmd_render(_args(rc, worktree=str(wt)))
    assert exc.value.code == 0
    result = json.loads(capsys.readouterr().out)
    assert result["ok"] is True
    assert result["data"]["format"] == "none"
    assert result["data"]["contracts_found"] == 0


def test_cmd_render_custom_out_path(rc, tmp_path, capsys):
    wt = tmp_path / "wt"
    wt.mkdir()
    shutil.copy(_FIXTURES / "fixtureB_minimal.jsonld", wt / "contract.jsonld")
    out = wt / "nested" / "C.html"
    out.parent.mkdir()
    with pytest.raises(SystemExit) as exc:
        rc.cmd_render(_args(rc, worktree=str(wt), out=str(out)))
    assert exc.value.code == 0
    assert out.exists()


def test_cmd_render_rejects_out_escaping_worktree(rc, tmp_path):
    wt = tmp_path / "wt"
    wt.mkdir()
    shutil.copy(_FIXTURES / "fixtureB_minimal.jsonld", wt / "contract.jsonld")
    escape = tmp_path / "outside.html"
    with pytest.raises(SystemExit) as exc:
        rc.cmd_render(_args(rc, worktree=str(wt), out=str(escape)))
    assert exc.value.code == 1
