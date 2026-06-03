"""WP-013 — the dogfood: the two verification journeys run from-graph, GREEN.

This is the **terminal** WP — the bootstrapping-circularity resolver. The two
verification scenarios verify the capture/emit path, which only exists once
WP-001..WP-012 are built; so the Requirement + scenario emission is deferred
here and emitted **through the new capture path itself** (FR-10), never via
the old ``--from-srd`` path (the MUST asserted in the WP's Green section).

These tests build the whole world in a **temp** ``.brain/instances`` (MEA-09:
real ``LocalFileEntityAdapter`` against the real vendored schemas, no store
mock) so the suite is repeatable in CI. The Act 1-3 dogfood that writes to the
REAL repo ``.brain`` store (so the captured ideas + scenario bundle ship on the
branch) is driven by the executor's commands, not by this test — but the exact
same code paths these tests exercise.

The five named tests (WP-013 Red):

- ``test_capture_and_traverse_journeys_run_green`` — author + emit both
  journeys into a temp store, run ``sulis-verify-acceptance --scenario`` for
  each; assert both green (verdict ``pass`` + gate ``pass``).
- ``test_capture_journey_lands_whole_chain`` — the capture journey's from-graph
  run produces an Opportunity + draft Requirement with a whole
  ``source`` → ``for_product`` → ``belongs_to_tenant`` chain.
- ``test_traverse_journey_reads_brain_not_change_store`` — the traverse journey
  answers "what's open" from brain entities, not from ``.changes/``.
- ``test_dogfood_requirements_source_resolves`` — the two dogfood Requirements'
  ``source`` resolves to the matured Opportunity id (no dangling, no synthetic).
- ``test_dogfood_ideas_are_roadmap_labelled`` — both dogfood ideas appear in the
  roadmap sidecar.

GREEN note (the load-bearing design decision): a Scenario runs ``pass`` only if
every Step yields step-status ``pass``. With no standing app, the only
no-network path to ``pass`` is the ``subprocess`` driver with a matching
``expect_exit`` (``_scenario_dispatch.execute_step``). So the journeys are
authored with ``mechanism: deterministic`` steps that reference ``subprocess``
Tools whose ``mechanism_detail`` carries a ``cmd`` invoking the real
capture/query CLI against the temp store. ``mechanism: human`` would surface as
``manual-pending`` — a BLOCKING gate verdict, not green.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_SCRIPTS_DIR = _HERE.parent.parent  # plugins/sulis/scripts
_CAPTURE_CLI = _SCRIPTS_DIR / "sulis-capture"
_QUERY_CLI = _SCRIPTS_DIR / "sulis-brain-query"
_AUTHOR_CLI = _SCRIPTS_DIR / "sulis-author-scenario"
_VERIFY_CLI = _SCRIPTS_DIR / "sulis-verify-acceptance"

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from _entity_adapter_local import LocalFileEntityAdapter  # noqa: E402
from _opportunity_emission import (  # noqa: E402
    _deterministic_ulid_from,
    compose_opportunity_from_idea,
)

_OPP_ID_RE = re.compile(r"^dna:opportunity:[0-9A-HJKMNP-TV-Z]{26}$")
_REQ_ID_RE = re.compile(r"^dna:requirement:[0-9A-HJKMNP-TV-Z]{26}$")

# The change's own why (the dogfood subject) — kept short; this is the matured
# Opportunity's job_statement.
_JOB_STATEMENT = (
    "When a scoped-out idea or requirement is raised mid-conversation, the "
    "founder can deposit it durably rooted in its why, and later ask the brain "
    "what is open, deferred, or on the roadmap."
)

# The two pieces of THIS change, captured as draft Requirements (Act 2).
_REQ_CAPTURE_WHAT = (
    "The capture path deposits a scoped-out idea into the brain rooted in its why."
)
_REQ_TRAVERSE_WHAT = (
    "The brain-traversal command asks what is open, deferred, or on the roadmap "
    "off the brain graph."
)


# ─── fixtures ────────────────────────────────────────────────────────────────
# The temp-store + repo-contract trio (repo_root / base_dir / brain_root) is the
# shared brain-store fixture set in ``conftest.py`` (brain_repo_root /
# brain_base_dir / brain_label_root) — extracted at the 2-consumer threshold
# (this suite + test_capture_e2e). Aliased here to the names the tests read.


@pytest.fixture
def repo_root(brain_repo_root: Path) -> Path:
    return brain_repo_root


@pytest.fixture
def base_dir(brain_base_dir: Path) -> Path:
    return brain_base_dir


@pytest.fixture
def brain_root(brain_label_root: Path) -> Path:
    return brain_label_root


# ─── CLI helpers ─────────────────────────────────────────────────────────────


def _run(cli: Path, *args: str) -> subprocess.CompletedProcess:
    """Invoke one of the real CLIs as a subprocess through the test interpreter."""
    return subprocess.run(
        [sys.executable, str(cli), *args],
        capture_output=True, text=True, timeout=120,
    )


def _parse(proc: subprocess.CompletedProcess) -> dict:
    assert proc.stdout.strip(), f"no stdout; stderr={proc.stderr!r}"
    return json.loads(proc.stdout)


def _pd_repo(base_dir: Path) -> LocalFileEntityAdapter:
    """A product-development repository against the temp store + vendored schemas.

    The ``LocalFileEntityAdapter`` IS the ``EntityRepository`` port
    implementation (it satisfies the Protocol) — callers use it directly.
    """
    return LocalFileEntityAdapter(base_dir, domain="product-development")


# ─── world builder: Act 1 + Act 2 + Act 3, against the temp store ────────────


def _mature_opportunity(repo_root: Path, base_dir: Path) -> str:
    """Act 1 — mature this change's own Opportunity into the store.

    Drives the analyst's emission path directly via the single-idea emission
    seam (``compose_opportunity_from_idea``, ADR-005) since the test is
    non-interactive — the point is a *matured* Opportunity entity (state
    advanced past ``hypothesis``, with a real ``job_statement`` + evidence +
    impact) lands with a real id, exactly as the analyst (ADR-004) would write
    it. Returns the ``dna:opportunity:<ulid>``.
    """
    opp = compose_opportunity_from_idea(
        job_statement=_JOB_STATEMENT,
        # First-call bootstrap chain product id is derived by capture; but the
        # Opportunity's for_product must match what the capture full-path
        # resolves. We let the capture bootstrap own the chain, then point the
        # Opportunity at the bootstrapped product. To keep Act 1 self-contained
        # and chain-whole, we bootstrap first via a throwaway quick capture,
        # read the product id back, then emit the matured Opportunity onto it.
        for_product=_bootstrap_product_id(repo_root, base_dir),
        seed="brain-backlog-why",
        state="validated",  # advanced past hypothesis — matured (ADR-004 / FR-10)
        evidence="Ideas raised in conversation get lost when scope narrows.",
        impact="A durable, why-rooted backlog the founder can interrogate.",
    )
    _pd_repo(base_dir).save("opportunity", opp)
    return opp["id"]


def _bootstrap_product_id(repo_root: Path, base_dir: Path) -> str:
    """Bootstrap the Tenant+Product chain (idempotent) and return the product id.

    Runs a throwaway quick capture so ``bootstrap_backing_chain`` fires, then
    reads the resolved product id back from the envelope. The matured
    Opportunity (Act 1) is rooted on this product so its ``for_product`` chain
    is whole.
    """
    proc = _run(
        _CAPTURE_CLI,
        "--repo-root", str(repo_root),
        "--base-dir", str(base_dir),
        "--why-intensity", "quick",
        "--why", "bootstrap the backing chain for the dogfood",
        "--seed", "dogfood-bootstrap",
    )
    env = _parse(proc)
    assert env["ok"] is True, env
    return env["data"]["chain"]["product_id"]


def _capture_two_requirements(repo_root: Path, base_dir: Path, opp_id: str) -> dict:
    """Act 2 — capture the two pieces of THIS change as draft Requirements.

    Both go THROUGH ``sulis-capture`` on the **full** path, rooted in Act-1's
    matured Opportunity (``--opportunity-id``), Roadmap-labelled (``--roadmap``).
    HARD CONSTRAINT: no ``--from-srd`` anywhere. Returns {seed: requirement_id}.
    """
    out: dict = {}
    for seed, what in (
        ("dogfood-req-capture-path", _REQ_CAPTURE_WHAT),
        ("dogfood-req-traverse-command", _REQ_TRAVERSE_WHAT),
    ):
        proc = _run(
            _CAPTURE_CLI,
            "--repo-root", str(repo_root),
            "--base-dir", str(base_dir),
            "--why-intensity", "full",
            "--opportunity-id", opp_id,
            "--what", what,
            "--seed", seed,
            "--roadmap",
        )
        env = _parse(proc)
        assert env["ok"] is True, f"capture {seed} failed: {env}"
        out[seed] = env["data"]["requirement_id"]
    return out


def _author_and_emit_journey(
    repo_root: Path,
    base_dir: Path,
    *,
    name: str,
    seed: str,
    verifies: list[str],
    tenant: str,
    steps: list[dict],
    out_path: Path,
) -> str:
    """Act 3 — author + emit one journey from-graph; return the Scenario id.

    Authors via the shipped ``sulis-author-scenario`` (reuse the PR #154 loop,
    no new machinery), writes the durable bundle to ``out_path`` (travels with
    the change under ``.changes/``), and emits the Scenario+Workflow+Steps into
    the temp brain so ``sulis-verify-acceptance --scenario`` can load it.
    """
    journey = {
        "name": name,
        "verifies": verifies,
        # No real Design entity for this change (script-only kind: backend); a
        # synthetic-but-shaped ref keeps the Scenario.exercises field valid.
        "exercises": "dna:design:" + ("0" * 26),
        "tenant": tenant,
        "seed": seed,
        "steps": steps,
    }
    journey_path = out_path.with_suffix(".journey.json")
    journey_path.write_text(json.dumps(journey, indent=2), encoding="utf-8")
    proc = _run(
        _AUTHOR_CLI,
        "--journey", str(journey_path),
        "--out", str(out_path),
        "--emit",
        "--repo-root", str(repo_root),
        "--base-dir", str(base_dir),
    )
    env = _parse(proc)
    assert env["ok"] is True, f"author {name} failed: {env}"
    return env["data"]["scenario_id"]


def _subprocess_tool(tool_id: str, name: str, tenant: str, *, kind: str) -> dict:
    """A foundation ``subprocess`` Tool — the invocation contract for a journey
    step (design doc: tool invocation is modelled, not annotated). ``kind`` is
    the Tool-schema operation kind (``query`` for read-only traverse, ``hybrid``
    for the capture step that deposits then reads back)."""
    return {
        "id": tool_id,
        "name": name,
        "for_domain": tenant,
        "kind": kind,
        "implementation_kind": "subprocess",
        "inputs_schema_ref": "n/a",
        "outputs_schema_ref": "n/a",
        "version": "1.0.0",
        "state": "active",
        "sys_status": "active",
    }


def _emit_tool(base_dir: Path, tool: dict) -> None:
    """Persist a foundation Tool so a Step's ``tool_ref`` resolves at load."""
    LocalFileEntityAdapter(base_dir, domain="foundation").save("tool", tool)


def _deterministic_step(*, instruction: str, asserts: list[str], tool_ref: str,
                        cmd: str) -> dict:
    """A journey beat that runs ``cmd`` as a subprocess and passes on exit 0.

    ``mechanism: deterministic`` + a ``subprocess`` ``tool_ref`` + a
    ``mechanism_detail`` carrying the cmd is the only no-standing-app path to a
    ``pass`` step status (``_scenario_dispatch``). ``expect_exit: 0`` is the
    default; the cmd invokes the real CLI against the temp store. The beat
    declares no external need — it's self-contained against the local store, so
    the journey's own data-flow chain (``test-target`` → step outputs) satisfies
    availability at run-time (``_scenario_runner``).
    """
    return {
        "instruction": instruction,
        "asserts": asserts,
        "mechanism": "deterministic",
        "tool_ref": tool_ref,
        "mechanism_detail": json.dumps({"cmd": cmd, "expect_exit": 0}),
    }


def _build_world(repo_root: Path, base_dir: Path) -> dict:
    """Run Act 1 + Act 2 + Act 3 against the temp store; return the artifacts.

    Returns a dict with: opportunity_id, requirement_ids (by seed),
    capture_scenario_id, traverse_scenario_id, tenant_id, bundle paths.
    """
    opp_id = _mature_opportunity(repo_root, base_dir)
    req_ids = _capture_two_requirements(repo_root, base_dir, opp_id)

    # The tenant the Steps/Workflow live under — the bootstrapped canonical id.
    tenant_id = _tenant_id_from_store(base_dir)

    # Two subprocess Tools — one per journey's invocation surface. Ids are
    # deterministic ULIDs (Crockford-base32, the schema pattern) from a stable
    # seed so re-running the dogfood overwrites in place (NFR-04).
    cap_tool = "dna:tool:" + _deterministic_ulid_from("dogfood-tool:capture-cli")
    trav_tool = "dna:tool:" + _deterministic_ulid_from("dogfood-tool:brain-query-cli")
    _emit_tool(base_dir, _subprocess_tool(cap_tool, "capture-cli", tenant_id, kind="hybrid"))
    _emit_tool(base_dir, _subprocess_tool(trav_tool, "brain-query-cli", tenant_id, kind="query"))

    py = sys.executable
    cap_req = req_ids["dogfood-req-capture-path"]

    # Capture journey — deposit a journey-LOCAL probe idea (its own seed, so a
    # journey run never clobbers the shipped dogfood Requirement), idempotent
    # (exit 0), then confirm a captured draft Requirement reads back off the
    # graph. The probe shares the matured Opportunity as its real source.
    capture_steps = [
        _deterministic_step(
            instruction="Deposit an idea: its why is matured into an "
                         "Opportunity and its what becomes a draft Requirement "
                         "rooted in that why.",
            asserts=["an Opportunity and a draft Requirement sourced from it land"],
            tool_ref=cap_tool,
            cmd=(
                f"{py} {_CAPTURE_CLI} --repo-root {repo_root} "
                f"--base-dir {base_dir} --why-intensity full "
                f"--opportunity-id {opp_id} "
                f"--what 'capture-journey probe: the deposit path works end to end' "
                f"--seed dogfood-capture-journey-probe"
            ),
        ),
        _deterministic_step(
            instruction="Read the captured Requirement back by id; the chain is "
                         "whole.",
            asserts=["the Requirement resolves with a source pointing at the "
                     "Opportunity"],
            tool_ref=cap_tool,
            cmd=(
                f"{py} {_QUERY_CLI} --base-dir {base_dir} --by-id {cap_req}"
            ),
        ),
    ]

    # Traverse journey — ask what's open / on the roadmap / done, off the graph.
    traverse_steps = [
        _deterministic_step(
            instruction="Ask the brain what is open.",
            asserts=["open ideas come back off the brain graph"],
            tool_ref=trav_tool,
            cmd=f"{py} {_QUERY_CLI} --base-dir {base_dir} --open",
        ),
        _deterministic_step(
            instruction="Ask the brain what is on the roadmap.",
            asserts=["roadmap members come back off the brain graph"],
            tool_ref=trav_tool,
            cmd=f"{py} {_QUERY_CLI} --base-dir {base_dir} --roadmap",
        ),
        _deterministic_step(
            instruction="Ask the brain what is done.",
            asserts=["done ideas come back off the brain graph"],
            tool_ref=trav_tool,
            cmd=f"{py} {_QUERY_CLI} --base-dir {base_dir} --done",
        ),
    ]

    changes_dir = repo_root / ".changes"
    changes_dir.mkdir(parents=True, exist_ok=True)
    cap_bundle = changes_dir / "capture-journey.scenarios.jsonld"
    trav_bundle = changes_dir / "traverse-journey.scenarios.jsonld"

    cap_scenario = _author_and_emit_journey(
        repo_root, base_dir,
        name="Capture journey — deposit an idea rooted in its why",
        seed="dogfood-capture-journey",
        verifies=[cap_req],
        tenant=tenant_id,
        steps=capture_steps,
        out_path=cap_bundle,
    )
    trav_scenario = _author_and_emit_journey(
        repo_root, base_dir,
        name="Traverse journey — ask what is open, deferred, on the roadmap",
        seed="dogfood-traverse-journey",
        verifies=[req_ids["dogfood-req-traverse-command"]],
        tenant=tenant_id,
        steps=traverse_steps,
        out_path=trav_bundle,
    )

    return {
        "opportunity_id": opp_id,
        "requirement_ids": req_ids,
        "capture_scenario_id": cap_scenario,
        "traverse_scenario_id": trav_scenario,
        "tenant_id": tenant_id,
        "capture_bundle": cap_bundle,
        "traverse_bundle": trav_bundle,
    }


def _tenant_id_from_store(base_dir: Path) -> str:
    """Read the single bootstrapped Tenant's id back from the temp store."""
    tenants = sorted((base_dir / "foundation" / "tenant").glob("*.jsonld"))
    assert tenants, "no tenant bootstrapped in the temp store"
    return json.loads(tenants[0].read_text())["id"]


def _run_scenario(repo_root: Path, base_dir: Path, scenario_id: str) -> dict:
    """Run one emitted Scenario from-graph; return the --json verdict envelope.

    No ``--available-artifacts`` needed: the journeys are self-contained against
    the local store, so the runner's journey-internal data-flow (``test-target``
    seed → each step's outputs) satisfies availability. The gate still doesn't
    fake green — a genuinely-external undeclared need would surface as deferred.
    """
    proc = _run(
        _VERIFY_CLI,
        "--scenario", scenario_id,
        "--base-dir", str(base_dir),
        "--repo-root", str(repo_root),
        "--json",
    )
    assert proc.stdout.strip(), f"no stdout; stderr={proc.stderr!r}"
    return json.loads(proc.stdout)


# ─── the five named tests (WP-013 Red) ───────────────────────────────────────


def test_capture_and_traverse_journeys_run_green(
    repo_root: Path, base_dir: Path
) -> None:
    """Author + emit both journeys; run each from-graph; both green."""
    world = _build_world(repo_root, base_dir)

    cap = _run_scenario(repo_root, base_dir, world["capture_scenario_id"])
    assert cap["verdict"] == "pass", cap
    assert cap["gate"] == "pass", cap
    assert all(s["status"] == "pass" for s in cap["steps"]), cap

    trav = _run_scenario(repo_root, base_dir, world["traverse_scenario_id"])
    assert trav["verdict"] == "pass", trav
    assert trav["gate"] == "pass", trav
    assert all(s["status"] == "pass" for s in trav["steps"]), trav


def test_capture_journey_lands_whole_chain(
    repo_root: Path, base_dir: Path
) -> None:
    """The capture journey's from-graph run produces an Opportunity + draft
    Requirement with a whole source → for_product → belongs_to_tenant chain."""
    world = _build_world(repo_root, base_dir)
    # Run the capture journey (its steps deposit + read back the idea).
    cap = _run_scenario(repo_root, base_dir, world["capture_scenario_id"])
    assert cap["verdict"] == "pass", cap

    opp_id = world["opportunity_id"]
    req_id = world["requirement_ids"]["dogfood-req-capture-path"]

    def _load(domain: str, etype: str, eid: str) -> dict:
        ulid = eid.rsplit(":", 1)[-1]
        path = base_dir / domain / etype / f"{ulid}.jsonld"
        assert path.exists(), f"missing {path}"
        return json.loads(path.read_text())

    requirement = _load("product-development", "requirement", req_id)
    opportunity = _load("product-development", "opportunity", opp_id)
    product = _load("product-development", "product", opportunity["for_product"])
    tenant = _load("foundation", "tenant", product["belongs_to_tenant"])

    # Whole chain — no dangling ref.
    assert requirement["source"] == opp_id
    assert requirement["state"] == "draft"
    assert opportunity["for_product"] == product["id"]
    assert product["belongs_to_tenant"] == tenant["id"]


def test_traverse_journey_reads_brain_not_change_store(
    repo_root: Path, base_dir: Path
) -> None:
    """The traverse journey answers "what's open" from brain entities — the
    returned ids resolve in the brain store, and none is sourced from
    ``.changes/``."""
    world = _build_world(repo_root, base_dir)
    trav = _run_scenario(repo_root, base_dir, world["traverse_scenario_id"])
    assert trav["verdict"] == "pass", trav

    # The traverse answer itself: query --open directly and assert every entity
    # is a real brain id resolvable in the store, never a .changes/ artifact.
    proc = _run(_QUERY_CLI, "--base-dir", str(base_dir), "--open")
    env = _parse(proc)
    assert env["ok"] is True, env
    entities = env["data"]["entities"]
    assert entities, "the open backlog should contain the dogfood ideas"

    changes_dir = repo_root / ".changes"
    for ent in entities:
        ent_id = ent["id"] if isinstance(ent, dict) else ent
        assert ent_id.startswith("dna:"), ent_id
        ulid = ent_id.rsplit(":", 1)[-1]
        # The entity resolves under the brain store, not under .changes/.
        in_brain = list(base_dir.rglob(f"{ulid}.jsonld"))
        assert in_brain, f"open entity {ent_id} not found in the brain store"
        in_changes = list(changes_dir.rglob(f"*{ulid}*")) if changes_dir.exists() else []
        assert not in_changes, f"open entity {ent_id} sourced from .changes/"


def test_dogfood_requirements_source_resolves(
    repo_root: Path, base_dir: Path
) -> None:
    """The two dogfood Requirements' ``source`` resolves to the matured
    Opportunity id — no dangling, no synthetic ref (ADR-005)."""
    world = _build_world(repo_root, base_dir)
    opp_id = world["opportunity_id"]
    assert _OPP_ID_RE.match(opp_id), opp_id

    repo = _pd_repo(base_dir)
    # The matured Opportunity actually exists and is advanced past hypothesis.
    opp = repo.find_by_id("opportunity", opp_id)
    assert opp is not None, f"matured opportunity {opp_id} not in store"
    assert opp["state"] != "hypothesis", opp["state"]

    for seed, req_id in world["requirement_ids"].items():
        assert _REQ_ID_RE.match(req_id), (seed, req_id)
        req = repo.find_by_id("requirement", req_id)
        assert req is not None, f"requirement {req_id} ({seed}) not in store"
        # Real source — the matured Opportunity, not a synthetic placeholder.
        assert req["source"] == opp_id, (seed, req["source"])


def test_dogfood_ideas_are_roadmap_labelled(
    repo_root: Path, base_dir: Path, brain_root: Path
) -> None:
    """Both dogfood Requirements (and the rooted Opportunity) appear in the
    roadmap sidecar (ADR-001 / SRD acceptance)."""
    world = _build_world(repo_root, base_dir)

    sidecar = brain_root / "labels" / "roadmap.jsonld"
    assert sidecar.exists(), f"missing roadmap sidecar at {sidecar}"
    members = set(json.loads(sidecar.read_text())["members"])

    for req_id in world["requirement_ids"].values():
        assert req_id in members, f"{req_id} not roadmap-labelled"
    # The capture full-path marks the rooting Opportunity Roadmap too.
    assert world["opportunity_id"] in members, "opportunity not roadmap-labelled"
