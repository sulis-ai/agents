"""test_migrate_dogfood — WP-005 (HD-004, ADR-002).

Unit tests for `migrate_dogfood_to_central.py`, the one-shot tool that moves the
repo's `product-development/*` records + `foundation/tenant` + the roadmap label
sidecar into the central brain, re-points the `for_product` edges onto the
surviving central product (ADR-002 MERGE), and reports the files to `git rm`.

SAFETY (WP-005 critical boundary): every test runs against synthetic `tmp_path`
fixtures with synthetic ULIDs. No test touches the real `~/.sulis/.brain`, and
no test runs the real migration. The git-rm acceptance is simulated in a tmp git
repo, never the real repo.

The tool is exercised through its importable functions (the hexagonal core) and,
where the contract is the file move, through the `migrate`/`build_manifest`
entry points directly — no mocks; real files under real tmp dirs.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[2]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import migrate_dogfood_to_central as mig  # noqa: E402

# ─── Synthetic fixture ids (NEVER the real RQ69/HHCZZ ULIDs) ────────────────

_SURVIVOR = "dna:product:AAAA56789ABCDEFGHJKMNPQRS0"  # central, canonical (HHCZZ stand-in)
_RETIREE = "dna:product:BBBB56789ABCDEFGHJKMNPQRS0"   # repo, retired (RQ69 stand-in)
_TENANT = "dna:tenant:CCCC56789ABCDEFGHJKMNPQRS0"


def _ulid_of(entity_id: str) -> str:
    return entity_id.rsplit(":", 1)[-1]


def _write(base: Path, domain: str, etype: str, record: dict) -> Path:
    """Write a record under `<base>/<domain>/<etype>/<ulid>.jsonld`."""
    d = base / domain / etype
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{_ulid_of(record['id'])}.jsonld"
    p.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return p


def _requirement(n: int, *, for_product: str | None) -> dict:
    ulid = f"REQ{n:023d}"  # 26-char synthetic-ish stem (3 + 23)
    r = {"id": f"dna:requirement:{ulid}", "statement": f"req {n}",
         "priority": "must", "state": "draft", "sys_status": "active",
         "verification_method": "test"}
    if for_product:
        r["for_product"] = for_product
    return r


@pytest.fixture
def repo_brain(tmp_path: Path) -> Path:
    """A synthetic REPO `.brain/` carrying the migration set + library.

    product-development: 1 product (retiree) + 3 requirements (for_product->retiree)
                         + 1 scenario (for_product->retiree) + 1 decision (no edge).
    foundation: 1 tenant (MIGRATES) + 1 workflow + 1 step + 1 tool (STAY).
    labels/roadmap.jsonld present.
    """
    brain = tmp_path / "repo" / ".brain"
    inst = brain / "instances"
    # product-development (migrates, minus the product file which is retired)
    _write(inst, "product-development", "product",
           {"id": _RETIREE, "name": "Repo Product", "state": "active",
            "sys_status": "active", "belongs_to_tenant": _TENANT,
            "repo_only_note": "keep me onto survivor"})
    for n in range(1, 4):
        _write(inst, "product-development", "requirement", _requirement(n, for_product=_RETIREE))
    _write(inst, "product-development", "scenario",
           {"id": "dna:scenario:SCN00000000000000000000000", "for_product": _RETIREE,
            "state": "draft", "sys_status": "active"})
    _write(inst, "product-development", "decision",
           {"id": "dna:decision:DEC00000000000000000000000", "state": "accepted",
            "sys_status": "active"})
    # foundation/tenant migrates; workflow/step/tool STAY
    _write(inst, "foundation", "tenant",
           {"id": _TENANT, "name": "T", "sys_status": "active"})
    _write(inst, "foundation", "workflow",
           {"id": "dna:workflow:WFL00000000000000000000000", "sys_status": "active"})
    _write(inst, "foundation", "step",
           {"id": "dna:step:STP00000000000000000000000A", "sys_status": "active"})
    _write(inst, "foundation", "tool",
           {"id": "dna:tool:TOL00000000000000000000000A", "sys_status": "active"})
    # roadmap label sidecar
    labels = brain / "labels"
    labels.mkdir(parents=True, exist_ok=True)
    (labels / "roadmap.jsonld").write_text(
        json.dumps({"label": "roadmap", "members": [_requirement(1, for_product=None)["id"]]}),
        encoding="utf-8")
    return brain


@pytest.fixture
def central_brain(tmp_path: Path) -> Path:
    """A synthetic CENTRAL `.brain/` holding ONLY the survivor product + its
    existing live records (1 lifecyclerun, 1 foundation/project) — to prove
    merge-not-collide preserves them."""
    brain = tmp_path / "central" / ".brain"
    inst = brain / "instances"
    _write(inst, "product-development", "product",
           {"id": _SURVIVOR, "name": "Central Product", "state": "active",
            "sys_status": "active"})
    _write(inst, "product-development", "lifecyclerun",
           {"id": "dna:lifecyclerun:LCR0000000000000000000000A", "sys_status": "active"})
    _write(inst, "foundation", "project",
           {"id": "dna:project:PRJ0000000000000000000000A", "sys_status": "active"})
    return brain


# ─── RED ────────────────────────────────────────────────────────────────────


def test_records_present_in_repo_not_central(repo_brain: Path, central_brain: Path):
    """Pre-migration characterisation: the 5 product-dev records + tenant live in
    the REPO brain and are absent from CENTRAL; central holds only its own."""
    repo_inst = repo_brain / "instances"
    central_inst = central_brain / "instances"

    # the repo's requirements exist in the repo, not centrally
    repo_reqs = list((repo_inst / "product-development" / "requirement").glob("*.jsonld"))
    assert len(repo_reqs) == 3
    assert not (central_inst / "product-development" / "requirement").exists()

    # the repo carries the retiree product; central carries the survivor
    assert (repo_inst / "product-development" / "product" / f"{_ulid_of(_RETIREE)}.jsonld").exists()
    assert (central_inst / "product-development" / "product" / f"{_ulid_of(_SURVIVOR)}.jsonld").exists()

    # the migration set the tool computes characterises exactly what is misplaced:
    # everything under product-development EXCEPT the retired product file, plus
    # foundation/tenant — and never foundation workflow/step/tool.
    plan = mig.compute_migration_set(repo_inst, retiree_product_id=_RETIREE)
    rels = {e.rel_path for e in plan}
    assert "product-development/requirement/" + f"{_ulid_of(_requirement(1, for_product=None)['id'])}.jsonld" in rels
    assert "foundation/tenant/" + f"{_ulid_of(_TENANT)}.jsonld" in rels
    # library stays out of the set
    assert not any(r.startswith("foundation/workflow/") for r in rels)
    assert not any(r.startswith("foundation/step/") for r in rels)
    assert not any(r.startswith("foundation/tool/") for r in rels)
    # the retired product file is NOT copied (it is retired, merged onto survivor)
    assert not any(r.startswith("product-development/product/") for r in rels)


# ─── GREEN ────────────────────────────────────────────────────────────────────


def _run_migration(repo_brain: Path, central_brain: Path):
    return mig.migrate(
        src_brain_root=repo_brain,
        dest_brain_root=central_brain,
        survivor_product_id=_SURVIVOR,
        retiree_product_id=_RETIREE,
        two_products="merge",
    )


def test_migration_copies_all_records_plus_label_to_central(repo_brain, central_brain):
    """Every migrated record + the roadmap label lands centrally; nothing orphaned.

    Migration set = (product-dev records minus the retired product) + tenant.
    Repo brain has 3 req + 1 scenario + 1 decision + 1 tenant = 6 copied records,
    plus the roadmap sidecar.
    """
    result = _run_migration(repo_brain, central_brain)
    central_inst = central_brain / "instances"

    assert len(list((central_inst / "product-development" / "requirement").glob("*.jsonld"))) == 3
    assert (central_inst / "product-development" / "scenario" / "SCN00000000000000000000000.jsonld").exists()
    assert (central_inst / "product-development" / "decision" / "DEC00000000000000000000000.jsonld").exists()
    assert (central_inst / "foundation" / "tenant" / f"{_ulid_of(_TENANT)}.jsonld").exists()
    # roadmap label copied to central brain root
    assert (central_brain / "labels" / "roadmap.jsonld").exists()
    # nothing orphaned: every entry in the manifest exists at its dest
    for e in result.manifest:
        assert Path(e["dest"]).exists(), f"orphaned: {e['dest']}"


def test_migration_is_idempotent(repo_brain, central_brain):
    """Second run: 0 new files, 0 duplicates."""
    _run_migration(repo_brain, central_brain)
    central_inst = central_brain / "instances"
    before = {p for p in central_inst.rglob("*.jsonld")}

    second = _run_migration(repo_brain, central_brain)
    after = {p for p in central_inst.rglob("*.jsonld")}

    assert before == after, "second run created/changed files"
    assert second.copied_count == 0, "second run copied records"
    # no ulid appears twice anywhere
    stems = [p.stem for p in after]
    assert len(stems) == len(set(stems)), "duplicate ULID files present"


def test_migration_merges_not_collides(repo_brain, central_brain):
    """An existing-id central record is not duplicated; central's existing
    lifecyclerun + foundation/project are preserved untouched."""
    central_inst = central_brain / "instances"
    lcr = central_inst / "product-development" / "lifecyclerun" / "LCR0000000000000000000000A.jsonld"
    prj = central_inst / "foundation" / "project" / "PRJ0000000000000000000000A.jsonld"
    lcr_before = lcr.read_text(encoding="utf-8")
    prj_before = prj.read_text(encoding="utf-8")

    _run_migration(repo_brain, central_brain)

    # central's pre-existing live records are byte-for-byte preserved
    assert lcr.read_text(encoding="utf-8") == lcr_before
    assert prj.read_text(encoding="utf-8") == prj_before
    # the survivor product is still exactly one file (not duplicated)
    prods = list((central_inst / "product-development" / "product").glob("*.jsonld"))
    assert len(prods) == 1
    assert prods[0].stem == _ulid_of(_SURVIVOR)


def test_migration_reversible_by_record(repo_brain, central_brain):
    """The manifest restores one record AND its original for_product edge."""
    result = _run_migration(repo_brain, central_brain)
    # pick the manifest entry for a requirement that was re-pointed
    entry = next(e for e in result.manifest
                 if "/requirement/" in e["dest"] and e.get("edge_rewrite"))
    dest = Path(entry["dest"])

    # post-migration the dest record points at the survivor
    assert json.loads(dest.read_text(encoding="utf-8"))["for_product"] == _SURVIVOR

    # reverse it: the record is restored with its ORIGINAL edge (retiree)
    restored = mig.reverse_record(entry)
    assert restored["id"] == entry["id"]
    assert restored["for_product"] == _RETIREE
    # the restored bytes match the recorded source sha256
    restored_sha = hashlib.sha256(
        json.dumps(restored, indent=2).encode("utf-8")).hexdigest()
    assert restored_sha == entry["src_sha256"]


def test_library_not_migrated(repo_brain, central_brain):
    """foundation workflow/step/tool are never copied centrally."""
    _run_migration(repo_brain, central_brain)
    central_inst = central_brain / "instances"
    assert not (central_inst / "foundation" / "workflow").exists()
    assert not (central_inst / "foundation" / "step").exists()
    assert not (central_inst / "foundation" / "tool").exists()
    # and they remain in the repo, untouched
    repo_inst = repo_brain / "instances"
    assert (repo_inst / "foundation" / "workflow" / "WFL00000000000000000000000.jsonld").exists()


def test_git_ls_files_brain_shows_only_library(tmp_path, repo_brain, central_brain):
    """Acceptance #5: after the migration's git-rm step, `git ls-files` under
    the repo brain shows ONLY the foundation library (+ retired product gone).

    Simulated in a throwaway tmp git repo — never the real repo.
    """
    # build a tmp git repo whose .brain mirrors repo_brain
    gitrepo = tmp_path / "gitrepo"
    gitrepo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=gitrepo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=gitrepo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=gitrepo, check=True)
    # copy the repo brain into the git repo
    import shutil
    shutil.copytree(repo_brain, gitrepo / ".brain")
    subprocess.run(["git", "add", "-A"], cwd=gitrepo, check=True)
    subprocess.run(["git", "commit", "-qm", "seed"], cwd=gitrepo, check=True)

    # run migration against the git repo's brain, then git-rm the reported set
    result = mig.migrate(
        src_brain_root=gitrepo / ".brain",
        dest_brain_root=central_brain,
        survivor_product_id=_SURVIVOR,
        retiree_product_id=_RETIREE,
        two_products="merge",
    )
    rel_paths = [str(Path(p).relative_to(gitrepo)) for p in result.git_rm]
    subprocess.run(["git", "rm", "-q", *rel_paths], cwd=gitrepo, check=True)
    subprocess.run(["git", "commit", "-qm", "migrate"], cwd=gitrepo, check=True)

    tracked = subprocess.run(
        ["git", "ls-files", ".brain"], cwd=gitrepo,
        capture_output=True, text=True, check=True).stdout.split()
    # only library (workflow/step/tool) + the labels dir survive under instances?
    # the migration removes all product-development + foundation/tenant + label.
    for t in tracked:
        assert "/product-development/" not in t, f"product-dev record still tracked: {t}"
        assert "/foundation/tenant/" not in t, f"tenant still tracked: {t}"
    # the foundation library is still tracked
    assert any("/foundation/workflow/" in t for t in tracked)
    assert any("/foundation/step/" in t for t in tracked)
    assert any("/foundation/tool/" in t for t in tracked)


def test_merge_yields_single_product_with_all_requirements(repo_brain, central_brain, monkeypatch):
    """ADR-002 post-condition: after --two-products=merge, central has EXACTLY ONE
    product (survivor), all requirements re-pointed to it, and resolve_for_product
    returns it."""
    _run_migration(repo_brain, central_brain)
    central_inst = central_brain / "instances"

    # exactly one product centrally
    prods = list((central_inst / "product-development" / "product").glob("*.jsonld"))
    assert len(prods) == 1
    assert prods[0].stem == _ulid_of(_SURVIVOR)

    # every migrated requirement now points at the survivor
    for p in (central_inst / "product-development" / "requirement").glob("*.jsonld"):
        assert json.loads(p.read_text(encoding="utf-8"))["for_product"] == _SURVIVOR
    # the scenario back-ref was re-pointed too
    scn = central_inst / "product-development" / "scenario" / "SCN00000000000000000000000.jsonld"
    assert json.loads(scn.read_text(encoding="utf-8"))["for_product"] == _SURVIVOR

    # resolve_for_product returns the single survivor (pin brain at central)
    from _change_emission import resolve_for_product
    monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", str(central_inst))
    assert resolve_for_product(central_brain.parent) == _SURVIVOR


def test_repoint_is_idempotent(repo_brain, central_brain):
    """Second run re-points zero edges — they already point at the survivor."""
    _run_migration(repo_brain, central_brain)
    second = _run_migration(repo_brain, central_brain)
    assert second.repointed_count == 0, "second run re-pointed edges already on survivor"


def test_retiree_metadata_merged_onto_survivor(repo_brain, central_brain):
    """RQ69-only metadata is merged ONTO the survivor; RQ69 is not written as a
    second product (ADR-002 step 3)."""
    _run_migration(repo_brain, central_brain)
    central_inst = central_brain / "instances"
    survivor_file = central_inst / "product-development" / "product" / f"{_ulid_of(_SURVIVOR)}.jsonld"
    survivor = json.loads(survivor_file.read_text(encoding="utf-8"))
    # the retiree-only field is carried onto the survivor
    assert survivor.get("repo_only_note") == "keep me onto survivor"
    # the survivor keeps its own identity (not overwritten by the retiree)
    assert survivor["id"] == _SURVIVOR
    assert survivor["name"] == "Central Product"
    # the retiree id is absent centrally
    assert not (central_inst / "product-development" / "product" / f"{_ulid_of(_RETIREE)}.jsonld").exists()


# ─── dry-run: mutate nothing ──────────────────────────────────────────────────


def test_dry_run_mutates_nothing_and_writes_manifest(repo_brain, central_brain, tmp_path):
    """--dry-run computes the set + writes a reversibility manifest but copies
    no records and rewrites no edges."""
    central_inst = central_brain / "instances"
    before = {p: p.read_text(encoding="utf-8") for p in central_inst.rglob("*.jsonld")}
    repo_before = {p: p.read_text(encoding="utf-8") for p in (repo_brain / "instances").rglob("*.jsonld")}

    manifest_path = tmp_path / "manifest.json"
    plan = mig.build_manifest(
        src_brain_root=repo_brain,
        dest_brain_root=central_brain,
        survivor_product_id=_SURVIVOR,
        retiree_product_id=_RETIREE,
        manifest_path=manifest_path,
    )

    # central + repo unchanged
    assert {p: p.read_text(encoding="utf-8") for p in central_inst.rglob("*.jsonld")} == before
    assert {p: p.read_text(encoding="utf-8") for p in (repo_brain / "instances").rglob("*.jsonld")} == repo_before
    # no records copied into central
    assert len(list((central_inst / "product-development" / "requirement").glob("*.jsonld"))) == 0
    # the manifest was written and lists planned edge rewrites
    assert manifest_path.exists()
    written = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert any(e.get("edge_rewrite") for e in written["records"])
    assert plan  # non-empty plan returned


# ─── CLI wiring (WPB-09: done means wired) ───────────────────────────────────


def _layout_repo_and_central(tmp_path: Path, monkeypatch) -> tuple[Path, Path]:
    """Lay out a repo (with .brain to migrate) + a separate central brain, and
    pin `brain_base_dir` at the central via SULIS_BRAIN_BASE_DIR. Returns
    (repo_root, central_brain_root)."""
    repo_root = tmp_path / "repo"
    central_root = tmp_path / "central"
    repo_brain = repo_root / ".brain"
    central_brain = central_root / ".brain"
    # reuse the fixture builders by writing directly
    inst = repo_brain / "instances"
    _write(inst, "product-development", "product",
           {"id": _RETIREE, "name": "Repo Product", "state": "active",
            "sys_status": "active", "repo_only_note": "keep"})
    for n in range(1, 3):
        _write(inst, "product-development", "requirement", _requirement(n, for_product=_RETIREE))
    _write(inst, "foundation", "tenant", {"id": _TENANT, "sys_status": "active"})
    _write(inst, "foundation", "workflow",
           {"id": "dna:workflow:WFL00000000000000000000000", "sys_status": "active"})
    (repo_brain / "labels").mkdir(parents=True, exist_ok=True)
    (repo_brain / "labels" / "roadmap.jsonld").write_text(
        json.dumps({"label": "roadmap", "members": []}), encoding="utf-8")
    # central survivor
    cinst = central_brain / "instances"
    _write(cinst, "product-development", "product",
           {"id": _SURVIVOR, "name": "Central Product", "state": "active", "sys_status": "active"})
    monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", str(cinst))
    return repo_root, central_brain


def test_cli_dry_run_is_default_and_mutates_nothing(tmp_path, monkeypatch, capsys):
    """`main` with no mode flag defaults to dry-run: writes the manifest, copies
    nothing centrally."""
    repo_root, central_brain = _layout_repo_and_central(tmp_path, monkeypatch)
    manifest = tmp_path / "m.json"
    rc = mig.main([
        "--repo-root", str(repo_root),
        "--two-products", "merge",
        "--survivor-product-id", _SURVIVOR,
        "--retiree-product-id", _RETIREE,
        "--manifest", str(manifest),
    ])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["mode"] == "dry-run"
    assert out["records"] == 3  # 2 requirements + 1 tenant
    assert out["edge_rewrites"] == 2
    assert manifest.exists()
    # nothing copied centrally
    assert not (central_brain / "instances" / "product-development" / "requirement").exists()


def test_cli_execute_copies_and_reports_git_rm(tmp_path, monkeypatch, capsys):
    """`main --execute` copies the set centrally and prints the git-rm list."""
    repo_root, central_brain = _layout_repo_and_central(tmp_path, monkeypatch)
    rc = mig.main([
        "--repo-root", str(repo_root),
        "--two-products", "merge",
        "--survivor-product-id", _SURVIVOR,
        "--retiree-product-id", _RETIREE,
        "--execute",
    ])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["mode"] == "execute"
    assert out["copied"] == 3
    # central now holds the 2 migrated requirements
    reqs = list((central_brain / "instances" / "product-development" / "requirement").glob("*.jsonld"))
    assert len(reqs) == 2
    for r in reqs:
        assert json.loads(r.read_text(encoding="utf-8"))["for_product"] == _SURVIVOR
    # the retiree product file is in the git-rm set; no second product centrally
    assert any(_ulid_of(_RETIREE) in g for g in out["git_rm"])
    cprods = list((central_brain / "instances" / "product-development" / "product").glob("*.jsonld"))
    assert len(cprods) == 1 and cprods[0].stem == _ulid_of(_SURVIVOR)


def test_unsupported_policy_raises():
    """The policy is never guessed: a non-merge policy raises."""
    with pytest.raises(ValueError, match="only 'merge'"):
        mig.migrate(
            src_brain_root=Path("/nonexistent"),
            dest_brain_root=Path("/nonexistent2"),
            survivor_product_id=_SURVIVOR,
            retiree_product_id=_RETIREE,
            two_products="keep-both",
        )
