"""The user-configurable brain-location resolver (#127, de-branch-scoped).

One resolver, honoured everywhere: explicit > SULIS_BRAIN_BASE_DIR env >
repo-contract `brain_location` > default. The default is the **user-level
settings home** (`{sulis_state_base}/.brain/instances`), NOT the per-repo
worktree — so a brain captured inside a change worktree survives the worktree
being removed at ship, and lives next to where the product/project settings
already are. A user sets the location via env (transient) or the contract field
(persistent — may point at a dir, the repo, or their own brain repo).
"""

from __future__ import annotations

from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2]
import sys  # noqa: E402
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _brain_location import brain_base_dir  # noqa: E402
from _change_state import sulis_state_base  # noqa: E402


def _write_contract(repo: Path, brain_location: str | None) -> None:
    d = repo / ".sulis"
    d.mkdir(parents=True, exist_ok=True)
    body = "repo: x/y\nprofile: published-artifact\n"
    if brain_location is not None:
        body += f"brain_location: {brain_location}\n"
    (d / "repo-contract.yml").write_text(body, encoding="utf-8")


def test_default_is_user_level_settings_home(tmp_path, monkeypatch):
    # The default no longer lives in the repo/worktree — it lives in the
    # user-level settings home (de-branch-scoped). SULIS_STATE_DIR isolates
    # the home so the test never touches the real ~/.sulis.
    monkeypatch.delenv("SULIS_BRAIN_BASE_DIR", raising=False)
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path / "home-sulis"))
    repo = tmp_path / "some-repo"
    assert brain_base_dir(repo) == sulis_state_base() / ".brain" / "instances"


def test_default_is_independent_of_worktree(tmp_path, monkeypatch):
    # The de-branch-scoping property: two different repo roots (e.g. a repo
    # and one of its per-change worktrees) with no override resolve to the
    # SAME brain dir — so captures aren't trapped in a throwaway worktree.
    monkeypatch.delenv("SULIS_BRAIN_BASE_DIR", raising=False)
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path / "home-sulis"))
    main_repo = tmp_path / "repo"
    worktree = tmp_path / "repo-change-fix-thing" / "worktree"
    assert brain_base_dir(main_repo) == brain_base_dir(worktree)
    assert brain_base_dir(worktree) == sulis_state_base() / ".brain" / "instances"


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
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path / "home-sulis"))
    _write_contract(tmp_path, None)   # contract exists but no brain_location
    assert brain_base_dir(tmp_path) == sulis_state_base() / ".brain" / "instances"


def test_relative_contract_brain_location_can_pin_in_repo(tmp_path, monkeypatch):
    # KEPT (resolver-capability test, NOT Sulis's own config). This pins the
    # resolver's *capability*: any repo that wants a committed in-repo brain can
    # opt in with a relative brain_location, which still resolves against the
    # repo root. It uses a synthetic tmp contract precisely so it stays true
    # regardless of what Sulis's own .sulis/repo-contract.yml says — Sulis's
    # actual de-branch-scoped behaviour is proved separately in
    # test_dogfood_resolves_central.py. Removing Sulis's own in-repo pin does
    # NOT change this escape-hatch contract, so this test is unchanged.
    monkeypatch.delenv("SULIS_BRAIN_BASE_DIR", raising=False)
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path / "home-sulis"))
    _write_contract(tmp_path, ".brain/instances")
    assert brain_base_dir(tmp_path) == tmp_path / ".brain" / "instances"
