"""Tests for the shared repo-contract reader + deploy-applicability (L-05).

`read_repo_contract` was promoted out of wpx-arrival-check so the pipeline,
the train, and the arrival check all parse `.sulis/repo-contract.yml` through
ONE function — a duplicated parser drifting from its twin is the bug class
that produced L-02. `deploy_is_applicable` is the new gate that lets the
pipeline/train skip the deploy→health→smoke phase on a non-deployable repo
(this marketplace is a `published-artifact` with `deploy_target: none`, so the
cockpit run had to hand-drive the whole loop).
"""

from __future__ import annotations

from pathlib import Path

from _wpxlib import deploy_is_applicable, read_repo_contract


def _write(repo_root: Path, body: str) -> None:
    sulis = repo_root / ".sulis"
    sulis.mkdir(parents=True, exist_ok=True)
    (sulis / "repo-contract.yml").write_text(body, encoding="utf-8")


# ─── read_repo_contract: parse shape (parity pin) ──────────────────────────


def test_missing_contract_returns_empty_shape(tmp_path):
    c = read_repo_contract(tmp_path)
    assert c == {
        "profile": None, "contribution_model": None,
        "artifacts": [], "deploy_target": None,
        "branch_convention": None,
    }


def test_reads_published_artifact_profile(tmp_path):
    _write(tmp_path, (
        "profile: published-artifact\n"
        "contribution_model: solo\n"
        "deploy_target: none           # back-compat alias\n"
    ))
    c = read_repo_contract(tmp_path)
    assert c["profile"] == "published-artifact"
    assert c["contribution_model"] == "solo"
    assert c["deploy_target"] == "none"  # inline comment stripped
    assert c["artifacts"] == []


def test_reads_deployable_profile(tmp_path):
    _write(tmp_path, "profile: deployable-web-app\ncontribution_model: team\n")
    c = read_repo_contract(tmp_path)
    assert c["profile"] == "deployable-web-app"
    assert c["deploy_target"] is None


# ─── #112: branch_convention key ──────────────────────────────────────────


def test_branch_convention_absent_is_none(tmp_path):
    """When the key is absent the convention is None — callers then default to
    change/{primitive}-{slug} byte-for-byte (zero behaviour change)."""
    _write(tmp_path, "profile: published-artifact\n")
    c = read_repo_contract(tmp_path)
    assert c["branch_convention"] is None


def test_missing_contract_includes_branch_convention_none(tmp_path):
    """The empty shape gains a branch_convention: None field."""
    c = read_repo_contract(tmp_path)
    assert c["branch_convention"] is None


def test_reads_branch_convention_template(tmp_path):
    _write(tmp_path, (
        "profile: deployable-web-app\n"
        "branch_convention: feature/{slug}\n"
    ))
    c = read_repo_contract(tmp_path)
    assert c["branch_convention"] == "feature/{slug}"


def test_reads_branch_convention_bare_prefix(tmp_path):
    _write(tmp_path, "branch_convention: feature/   # bare prefix\n")
    c = read_repo_contract(tmp_path)
    assert c["branch_convention"] == "feature/"  # inline comment stripped


def test_reads_multi_artifact_list(tmp_path):
    _write(tmp_path, (
        "artifacts:\n"
        "  - name: web\n"
        "    type: deployable-web-app\n"
        "  - name: cli\n"
        "    type: internal-tool\n"
    ))
    c = read_repo_contract(tmp_path)
    assert c["artifacts"] == [
        {"name": "web", "type": "deployable-web-app"},
        {"name": "cli", "type": "internal-tool"},
    ]


def test_arrival_check_delegates_to_shared_reader(tmp_path):
    """The arrival-check wrapper must produce byte-identical output to the
    shared reader — pins the delegation so they can't drift (the L-05 point)."""
    import importlib.util
    from importlib.machinery import SourceFileLoader

    _write(tmp_path, "profile: published-artifact\ncontribution_model: solo\n")
    scripts_dir = Path(__file__).resolve().parents[2]  # .../scripts
    # wpx-arrival-check is extensionless — load it with an explicit loader.
    loader = SourceFileLoader(
        "wpx_arrival_check_mod", str(scripts_dir / "wpx-arrival-check"),
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    assert mod._read_contract(tmp_path) == read_repo_contract(tmp_path)


# ─── deploy_is_applicable: the new gate ────────────────────────────────────


def test_published_artifact_is_not_deployable(tmp_path):
    _write(tmp_path, "profile: published-artifact\ndeploy_target: none\n")
    assert deploy_is_applicable(read_repo_contract(tmp_path)) is False


def test_published_artifact_without_deploy_target_still_not_deployable(tmp_path):
    _write(tmp_path, "profile: published-artifact\n")
    assert deploy_is_applicable(read_repo_contract(tmp_path)) is False


def test_internal_tool_is_not_deployable(tmp_path):
    _write(tmp_path, "profile: internal-tool\n")
    assert deploy_is_applicable(read_repo_contract(tmp_path)) is False


def test_deployable_web_app_is_deployable(tmp_path):
    _write(tmp_path, "profile: deployable-web-app\n")
    assert deploy_is_applicable(read_repo_contract(tmp_path)) is True


def test_unset_profile_defaults_to_deployable_strict(tmp_path):
    # No contract at all → strict backward-compat default = deployable.
    assert deploy_is_applicable(read_repo_contract(tmp_path)) is True


def test_deploy_target_none_overrides_unset_profile(tmp_path):
    _write(tmp_path, "deploy_target: none\n")
    assert deploy_is_applicable(read_repo_contract(tmp_path)) is False


def test_multi_artifact_is_deployable_if_any_artifact_is(tmp_path):
    _write(tmp_path, (
        "artifacts:\n"
        "  - name: web\n    type: deployable-web-app\n"
        "  - name: cli\n    type: internal-tool\n"
    ))
    assert deploy_is_applicable(read_repo_contract(tmp_path)) is True


def test_multi_artifact_not_deployable_if_none_are(tmp_path):
    _write(tmp_path, (
        "artifacts:\n"
        "  - name: lib\n    type: published-artifact\n"
        "  - name: cli\n    type: internal-tool\n"
    ))
    assert deploy_is_applicable(read_repo_contract(tmp_path)) is False
