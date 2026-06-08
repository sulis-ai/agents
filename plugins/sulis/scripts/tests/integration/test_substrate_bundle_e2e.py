"""WP-006 — the closing integration proof for the verification substrate.

The end-to-end drive that proves the producer/consumer seams of the reconciled
substrate meet for real. A FRESH authored scenario bundle carrying the new
contract fields (``isolation`` + ``verdict_invariant``) goes
author → emit → load → run, and the run **exercises** the whole reconciled
spine (CH-01KTMA + main #207/#197 back-integration):

1. The bundle is authored with the REAL ``assemble_scenario_graph`` (no
   hand-built graph), then the scenario is augmented with the two new OPTIONAL
   fields and EMITTED through the REAL ``LocalFileEntityAdapter`` into a temp
   ``.brain/instances`` — which validates every entity against the REAL vendored
   compiled schemas (``scenario.schema.json`` enforces
   ``unevaluatedProperties: false``). Loading it back through the real
   ``load_scenario_journey`` and finding the two new fields intact IS the
   schema round-trip proof (MEA-09 — no schema mock).

2. The loaded journey is driven IN-PROCESS via ``run_scenario`` with INJECTED
   transports — a fake ``browser`` returning
   ``SimpleNamespace(ok=True, detail=..., saved_record=...)`` (exactly as main's
   own browser unit tests do) and a fake ``run`` for the subprocess step. There
   is **NO real Playwright import** anywhere in this path; the injected fake is
   the seam. The in-process runner is the drive surface (not the
   ``sulis-verify-acceptance`` CLI) because the CLI's JSON envelope does not
   surface ``tiers`` / ``isolation_rung`` / ``invariant_result`` and cannot take
   an injected browser transport — the recorded substrate fields are read
   straight off the ``AcceptanceResult``.

What the single run proves, co-existing on ONE ``AcceptanceResult``:

- a ``browser``-driver step DERIVES tier ``scripted`` (the reconciled
  ``SCRIPTED_KINDS`` includes ``browser``, WP-007 / main #207);
- the machine ``verdict_invariant`` (``equality`` over the REAL captured
  ``saved_record``) emits ``observed`` — the field #95's gate reads — on the
  SAME run that reports the browser tier (the deterministic-driver path and the
  machine-invariant path co-exist, neither masking the other);
- the ``isolation`` rung is recorded on the run (declared ``reset``);
- an ``agent-step``-tier step reports ``deferred`` naming #92 — its execution is
  NOT driven (scope guard; the machine-invariant route and the
  deferred-to-attestation/#92 route are alternatives, not duplicates, ADR-003);
- the founder-summary surface still renders.

Real-data-not-mock guard (ADR-003): the ``saved_record`` the invariant
evaluates is the artifact the (faked-transport-but-real-shape) browser step
produced — never a mock of the record itself.

Schema-enum note (registered finding, NOT this WP's fix): the vendored
``foundation/tool.schema.json`` ``implementation_kind`` enum does not yet carry
``browser`` (main added the driver to the Python runtime ``IMPLEMENTATION_KINDS``
during back-integration, but the compiled tool schema enum was not reconciled).
So a ``browser``-kind foundation Tool cannot be PERSISTED through the adapter
today. The runner does not validate Tools against the schema, so the browser
step is driven from an in-memory ``tools_by_id`` (the legitimate injected seam
this WP prescribes); the new SCENARIO fields — the round-trip this WP must prove
— live on ``scenario.schema.json``, which DOES support them, and so go through
the real emit → load adapter path. Reconciling the tool-schema enum is WP-007's
scope, captured as a finding.

Stdlib + pytest + jsonschema (via the adapter). Builds its whole world in a temp
store (bootstrap-from-zero); never touches the real repo ``.brain``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

_HERE = Path(__file__).resolve().parent
_SCRIPTS_DIR = _HERE.parent.parent  # plugins/sulis/scripts

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from _entity_adapter_local import LocalFileEntityAdapter  # noqa: E402
from _scenario_authoring import assemble_scenario_graph  # noqa: E402
from _scenario_graph_load import load_scenario_journey  # noqa: E402
from _scenario_runner import (  # noqa: E402
    format_founder_summary,
    run_scenario,
)

# Crockford-base32 ULID bodies (the schema id pattern). Fixed so the authored
# graph is deterministic and the refs resolve in the temp store.
_REQ_ID = "dna:requirement:" + "0" * 26
_DESIGN_ID = "dna:design:" + "0" * 26
_TENANT_ID = "dna:tenant:" + "0" * 26
# The browser step's tool — referenced in-memory only (see module docstring:
# the compiled tool-schema enum lacks `browser`, so it isn't persisted).
_BROWSER_TOOL_ID = "dna:tool:" + "B" * 26

# The REAL artifact the browser step produces and the equality invariant checks
# against — the record crosses the seam, never mocked (ADR-003).
_SAVED_RECORD = {"order_id": "ord-42", "status": "confirmed"}

# The canonical deferral identifiers the agent-step tier names (ADR-001).
_AGENT_STEP_OWNER = "#92"


def _author_substrate_bundle() -> dict:
    """Author a fresh three-beat journey via the REAL assembler.

    The beats span the reconciled tier surface:
      1. a ``subprocess`` (scripted) beat — round-trips through the adapter
         (its ``implementation_kind`` is in the compiled tool-schema enum);
      2. a ``browser`` (scripted, reconciled) beat — the reconciliation point;
      3. an ``mcp_server`` (agent-step) beat — declared, deferred to #92.

    Each beat carries an observable check (the authoring verifiability gate,
    journey-rigor #5) and the final beat's check is observable.
    """
    return assemble_scenario_graph(
        name="substrate e2e — checkout proves across the reconciled tiers",
        verifies=[_REQ_ID],
        exercises=_DESIGN_ID,
        tenant=_TENANT_ID,
        seed="wp006-substrate-e2e",
        steps=[
            {
                "instruction": "POST the checkout against the API",
                "asserts": ["the order is saved"],
                "mechanism": "deterministic",
                "tool_ref": "dna:tool:" + "A" * 26,
                "mechanism_detail": json.dumps({"cmd": "true", "expect_exit": 0}),
            },
            {
                "instruction": "Confirm the order landed in the browser UI",
                "asserts": ["the confirmation is visible in the UI"],
                "mechanism": "deterministic",
                "tool_ref": _BROWSER_TOOL_ID,
                "mechanism_detail": json.dumps(
                    {"url": "/checkout", "assert": {"visible": "Confirmed"}}
                ),
            },
            {
                "instruction": "Have an agent judge the receipt screenshot",
                "asserts": ["the agent confirms the receipt matches the order"],
                "mechanism": "probabilistic",
                "tool_ref": "dna:tool:" + "C" * 26,
            },
        ],
    )


def _scripted_tool(tool_id: str, name: str, impl_kind: str, op_kind: str) -> dict:
    """A foundation Tool whose ``implementation_kind`` resolves a driver.

    Only emitted for kinds the compiled tool schema enumerates (``subprocess`` /
    ``mcp_server``); the ``browser`` tool is referenced in-memory only.
    """
    return {
        "id": tool_id,
        "name": name,
        "for_domain": _TENANT_ID,
        "kind": op_kind,
        "implementation_kind": impl_kind,
        "inputs_schema_ref": "n/a",
        "outputs_schema_ref": "n/a",
        "version": "1.0.0",
        "state": "active",
        "sys_status": "active",
    }


def _emit_bundle_with_new_fields(base_dir: Path, bundle: dict) -> str:
    """Emit the authored bundle, augmenting the scenario with the two new
    OPTIONAL contract fields, through the REAL adapter (real schema validation).

    Returns the scenario id. The adapter's ``save`` runs
    ``Draft202012Validator`` against the REAL vendored compiled schema — so a
    successful emit IS the schema round-trip proof for the new scenario fields
    (MEA-09). The persisted Tools are the subprocess + mcp_server ones (their
    kinds are schema-valid); the browser tool is injected at run time.
    """
    foundation = LocalFileEntityAdapter(base_dir=base_dir, domain="foundation")
    product = LocalFileEntityAdapter(base_dir=base_dir, domain="product-development")

    for step in bundle["steps"]:
        foundation.save("step", step)
    for wf in bundle["workflows"]:
        foundation.save("workflow", wf)

    # Persist the schema-valid Tools the resolver will dereference at load.
    foundation.save(
        "tool",
        _scripted_tool(
            "dna:tool:" + "A" * 26, "checkout-api", "subprocess", "mutation"
        ),
    )
    foundation.save(
        "tool",
        _scripted_tool(
            "dna:tool:" + "C" * 26, "receipt-judge", "mcp_server", "side-effect"
        ),
    )

    scenario = dict(bundle["scenarios"][0])
    # The two NEW optional contract fields (WP-001) — carried onto the authored
    # scenario and emitted through the real schema.
    scenario["isolation"] = "reset"
    scenario["verdict_invariant"] = {
        "kind": "equality",
        "expected_ref": "contracts/expected/checkout-confirmed.json",
    }
    product.save("scenario", scenario)
    return scenario["id"]


def _fake_browser(url, actions, assert_spec):
    """An INJECTED deterministic browser transport — main's own browser-test
    seam shape: returns ``SimpleNamespace(ok, detail, saved_record)``. NO real
    Playwright. The ``saved_record`` is the REAL artifact the step produced, fed
    to the verdict-invariant (ADR-003 real-data-not-mock)."""
    return SimpleNamespace(
        ok=True,
        detail=f"visible(Confirmed) at {url}",
        saved_record=dict(_SAVED_RECORD),
    )


def _fake_run(cmd):
    """An INJECTED subprocess transport — the scripted subprocess beat passes on
    exit 0 (the authored ``expect_exit``)."""
    return SimpleNamespace(returncode=0)


def test_authored_bundle_carries_and_exercises_substrate_fields(
    brain_base_dir: Path,
) -> None:
    """The closing proof: a fresh authored bundle carries the new fields through
    author → emit → load → run, and the single run exercises the reconciled
    whole — browser→scripted tier AND machine verdict-invariant co-existing,
    isolation rung recorded, agent-step deferred-to-#92, founder summary intact.
    """
    # ── author → emit (real adapter + real schema) ───────────────────────────
    bundle = _author_substrate_bundle()
    scenario_id = _emit_bundle_with_new_fields(brain_base_dir, bundle)

    # ── load back through the real graph loader ──────────────────────────────
    loaded = load_scenario_journey(brain_base_dir, scenario_id)
    assert not loaded.missing_steps, loaded.missing_steps

    # Schema round-trip: the two NEW optional fields survived emit → load against
    # the REAL vendored scenario.schema.json (unevaluatedProperties:false). MEA-09.
    assert loaded.scenario["isolation"] == "reset", loaded.scenario
    assert loaded.scenario["verdict_invariant"]["kind"] == "equality", loaded.scenario

    # The browser step needs its tool injected (the compiled tool-schema enum
    # lacks `browser` — see module docstring + the registered finding). The
    # loaded subprocess + mcp_server tools came back from the store.
    tools_by_id = dict(loaded.tools_by_id)
    tools_by_id[_BROWSER_TOOL_ID] = {
        "@id": _BROWSER_TOOL_ID,
        "id": _BROWSER_TOOL_ID,
        "implementation_kind": "browser",
    }

    # The equality invariant's expected shape, resolved (the executable resolves
    # `expected_ref`; in-process we supply the resolved `expected` the evaluator
    # reads). It matches the REAL saved_record the browser step produces.
    scenario = dict(loaded.scenario)
    scenario["verdict_invariant"] = {
        "kind": "equality",
        "expected": dict(_SAVED_RECORD),
    }

    # ── run IN-PROCESS with injected transports (NO real Playwright) ──────────
    result = run_scenario(
        scenario,
        loaded.workflow,
        loaded.steps_by_name,
        tools_by_id,
        target_base_url="http://local",
        browser=_fake_browser,
        run=_fake_run,
    )

    step_names = list(loaded.workflow["steps"])
    subprocess_step, browser_step, agent_step = step_names

    # 1. The driver tier is REPORTED per step. The browser step derives the
    #    reconciled `scripted` tier (proves SCRIPTED_KINDS ∋ browser, WP-007).
    assert result.tiers[browser_step] == "scripted", result.tiers
    assert result.tiers[subprocess_step] == "scripted", result.tiers
    assert result.tiers[agent_step] == "agent-step", result.tiers

    # 2. The isolation rung is RECORDED on the run (declared `reset`).
    assert result.isolation_rung == "reset", result

    # 3. The machine verdict-invariant is EMITTED — `observed` (equality over the
    #    REAL captured saved_record) — on the SAME run that reports the browser
    #    tier. The deterministic-driver path and the machine-invariant path
    #    co-exist; neither masks the other.
    assert result.invariant_result == "observed", result
    assert result.tiers[browser_step] == "scripted" and result.invariant_result, result

    # 4. The agent-step beat reports `deferred` naming #92 — execution NOT driven
    #    (scope guard); its need names the agent-step driver.
    agent_row = next(s for s in result.steps if s["name"] == agent_step)
    assert agent_row["status"] == "deferred", agent_row
    assert _AGENT_STEP_OWNER in agent_row["detail"], agent_row
    assert agent_row["need"], agent_row

    # The scripted beats ran (the browser + subprocess steps passed) — the only
    # non-pass step is the deliberately-deferred agent beat.
    statuses = {s["name"]: s["status"] for s in result.steps}
    assert statuses[subprocess_step] == "pass", statuses
    assert statuses[browser_step] == "pass", statuses

    # The run disposition is `deferred` (worst-wins: the agent beat deferred),
    # DISTINCT from the machine `invariant_result` (`observed`) — exactly the
    # two-axis split this substrate exists to surface (ADR-003).
    assert result.verdict == "deferred", result

    # 5. The founder-summary surface still renders for the run.
    summary = format_founder_summary(result)
    assert result.scenario_name in summary, summary
    assert "deferred" in summary, summary


def test_run_built_entirely_in_temp_store(brain_base_dir: Path) -> None:
    """Blue guard: the whole world is built in the temp store — the emitted
    scenario lands under the temp ``.brain``, and the real repo ``.brain`` is
    never written (bootstrap-from-zero)."""
    bundle = _author_substrate_bundle()
    scenario_id = _emit_bundle_with_new_fields(brain_base_dir, bundle)

    ulid = scenario_id.rsplit(":", 1)[-1]
    persisted = brain_base_dir / "product-development" / "scenario" / f"{ulid}.jsonld"
    assert persisted.exists(), persisted
    # The emitted scenario on disk carries the new fields (durable round-trip).
    on_disk = json.loads(persisted.read_text(encoding="utf-8"))
    assert on_disk["isolation"] == "reset", on_disk
    assert on_disk["verdict_invariant"]["kind"] == "equality", on_disk

    # The temp store is under the pytest tmp tree — never the real repo .brain.
    repo_brain = _SCRIPTS_DIR.parents[2] / ".brain" / "instances"
    assert repo_brain not in persisted.parents, persisted
