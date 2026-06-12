"""The user-configurable brain-location resolver (#127).

One resolver, honoured everywhere: explicit > SULIS_BRAIN_BASE_DIR env >
repo-contract `brain_location` > default `<repo>/.brain/instances`. The default
is unchanged (non-disruptive); a user sets the location via env (transient) or
the contract field (persistent — may point at a dir or their own repo).
"""

from __future__ import annotations

from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2]
import sys  # noqa: E402
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _brain_location import brain_base_dir  # noqa: E402


def _write_contract(repo: Path, brain_location: str | None) -> None:
    d = repo / ".sulis"
    d.mkdir(parents=True, exist_ok=True)
    body = "repo: x/y\nprofile: published-artifact\n"
    if brain_location is not None:
        body += f"brain_location: {brain_location}\n"
    (d / "repo-contract.yml").write_text(body, encoding="utf-8")


def test_default_is_repo_brain_unchanged(tmp_path, monkeypatch):
    monkeypatch.delenv("SULIS_BRAIN_BASE_DIR", raising=False)
    assert brain_base_dir(tmp_path) == tmp_path / ".brain" / "instances"


def test_env_override_absolute(tmp_path, monkeypatch):
    monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", "/tmp/elsewhere/brain")
    assert brain_base_dir(tmp_path) == Path("/tmp/elsewhere/brain")


def test_env_relative_resolves_against_repo(tmp_path, monkeypatch):
    monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", "sub/brain")
    assert brain_base_dir(tmp_path) == tmp_path / "sub" / "brain"


def test_contract_brain_location_persistent(tmp_path, monkeypatch):
    monkeypatch.delenv("SULIS_BRAIN_BASE_DIR", raising=False)
    _write_contract(tmp_path, "/data/my-brain")
    assert brain_base_dir(tmp_path) == Path("/data/my-brain")


def test_contract_relative_resolves_against_repo(tmp_path, monkeypatch):
    monkeypatch.delenv("SULIS_BRAIN_BASE_DIR", raising=False)
    _write_contract(tmp_path, ".sulis/brain")
    assert brain_base_dir(tmp_path) == tmp_path / ".sulis" / "brain"


def test_env_beats_contract(tmp_path, monkeypatch):
    _write_contract(tmp_path, "/data/from-contract")
    monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", "/data/from-env")
    assert brain_base_dir(tmp_path) == Path("/data/from-env")


def test_explicit_beats_all(tmp_path, monkeypatch):
    _write_contract(tmp_path, "/data/from-contract")
    monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", "/data/from-env")
    assert brain_base_dir(tmp_path, explicit="/data/explicit") == Path("/data/explicit")


def test_tilde_expands(tmp_path, monkeypatch):
    monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", "~/sulis-brain")
    assert brain_base_dir(tmp_path) == Path.home() / "sulis-brain"


def test_absent_contract_field_falls_to_default(tmp_path, monkeypatch):
    monkeypatch.delenv("SULIS_BRAIN_BASE_DIR", raising=False)
    _write_contract(tmp_path, None)   # contract exists but no brain_location
    assert brain_base_dir(tmp_path) == tmp_path / ".brain" / "instances"
