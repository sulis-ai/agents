"""Unit tests for plugin_version() — the version signal the #102 daemon
version-skew guard compares against."""

from __future__ import annotations

import json

from _plugin_version import plugin_version


def _make_plugin(tmp_path, version):
    (tmp_path / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": "sulis", "version": version}), encoding="utf-8")
    scripts = tmp_path / "scripts"
    scripts.mkdir(exist_ok=True)
    f = scripts / "x.py"
    f.write_text("# marker\n", encoding="utf-8")
    return f


def test_reads_version_from_nearest_plugin_json(tmp_path):
    f = _make_plugin(tmp_path, "1.2.3")
    assert plugin_version(start=str(f)) == "1.2.3"


def test_none_when_no_manifest(tmp_path):
    (tmp_path / "x.py").write_text("# none\n", encoding="utf-8")
    assert plugin_version(start=str(tmp_path / "x.py")) is None


def test_none_when_version_missing(tmp_path):
    (tmp_path / ".claude-plugin").mkdir(parents=True)
    (tmp_path / ".claude-plugin" / "plugin.json").write_text("{}", encoding="utf-8")
    f = tmp_path / "scripts" / "x.py"
    f.parent.mkdir()
    f.write_text("# x\n", encoding="utf-8")
    assert plugin_version(start=str(f)) is None


def test_none_when_malformed(tmp_path):
    (tmp_path / ".claude-plugin").mkdir(parents=True)
    (tmp_path / ".claude-plugin" / "plugin.json").write_text("{bad", encoding="utf-8")
    f = tmp_path / "scripts" / "x.py"
    f.parent.mkdir()
    f.write_text("# x\n", encoding="utf-8")
    assert plugin_version(start=str(f)) is None


def test_real_plugin_reports_a_version():
    # The actual sulis plugin.json must resolve to a non-empty version string.
    v = plugin_version()
    assert isinstance(v, str) and v, f"expected a real version, got {v!r}"
