"""WP-004 — tests for ``_brain_capture.capture_idea`` (the orchestrator).

``capture_idea`` is the gate that makes "no orphan requirements" real in code
(ADR-003 / ADR-004 / ADR-005). It is **one function, two depths**
(``why_intensity`` = ``quick`` | ``full``):

* **quick** — the orchestrator roots the idea itself: bootstrap the backing
  chain, emit a ``hypothesis`` Opportunity from the founder's one-line why, and
  (when a ``what`` is given) a draft Requirement sourced from that real
  Opportunity id.
* **full** — the opportunity-analyst has already emitted/matured an Opportunity
  (ADR-004 store hand-off); capture reads it back **by id**, confirms it
  resolves and its ``for_product`` chain is whole, and only then emits the
  Requirement sourced from it. A dangling / chain-broken id ⇒ ``CaptureError``
  and **no orphan Requirement**.

The load-bearing invariant across both depths: the Requirement is the **last**
write and only fires after its ``source`` resolves to a real Opportunity. The
why-first gate is a literal ``if`` — ``quick`` with a blank ``why`` raises
``CaptureError`` and emits **nothing** (FR-02).

No store mocks (MEA-09): the tests run against a temp ``.brain/instances`` and
the real ``LocalFileEntityAdapter`` validating against the real vendored
schemas under ``plugins/sulis/brain/compiled/{foundation,product-development}/``.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from _brain_capture import CaptureError, capture_idea
from _brain_query import roadmap_members
from _entity_adapter_local import LocalFileEntityAdapter
from _opportunity_emission import compose_opportunity_from_idea

_REPO = "sulis-ai/agents"
_OPP_ID_RE = re.compile(r"^dna:opportunity:[0-9A-HJKMNP-TV-Z]{26}$")
_REQ_ID_RE = re.compile(r"^dna:requirement:[0-9A-HJKMNP-TV-Z]{26}$")

_WHY = "Captured ideas keep getting lost because they have no why."
_WHAT = "Every captured idea is rooted in an Opportunity before it lands."


@pytest.fixture
def base_root(tmp_path: Path) -> Path:
    """The ``.brain/`` root (parent of ``instances`` and of the label sidecar)."""
    return tmp_path / ".brain"


@pytest.fixture
def instances_dir(base_root: Path) -> Path:
    """The ``.brain/instances`` directory the entity adapters write under."""
    return base_root / "instances"


@pytest.fixture
def repo_foundation(instances_dir: Path) -> LocalFileEntityAdapter:
    return LocalFileEntityAdapter(base_dir=instances_dir, domain="foundation")


@pytest.fixture
def repo_pd(instances_dir: Path) -> LocalFileEntityAdapter:
    return LocalFileEntityAdapter(base_dir=instances_dir, domain="product-development")


def _instance_files(instances_dir: Path) -> list[Path]:
    """Every ``.jsonld`` instance file under the temp store, sorted."""
    return sorted(instances_dir.rglob("*.jsonld"))


def test_quick_capture_rejects_missing_why(
    repo_foundation: LocalFileEntityAdapter,
    repo_pd: LocalFileEntityAdapter,
    base_root: Path,
    instances_dir: Path,
) -> None:
    """``quick`` + blank ``why`` → ``CaptureError``; store unchanged (FR-02).

    The why-first gate fires *before* anything is written — not even the
    backing chain. Nothing is emitted, so the store is byte-empty afterwards.
    """
    with pytest.raises(CaptureError) as excinfo:
        capture_idea(
            repo_foundation=repo_foundation,
            repo_pd=repo_pd,
            repo_org_slash_name=_REPO,
            roadmap_base_dir=base_root,
            why_intensity="quick",
            why="   ",  # blank after strip
            what=_WHAT,
            seed="rejects-missing-why",
        )

    assert "why" in str(excinfo.value).lower()
    # Nothing emitted at all — not even the backing chain.
    assert _instance_files(instances_dir) == []


def test_quick_capture_lands_opportunity_and_requirement(
    repo_foundation: LocalFileEntityAdapter,
    repo_pd: LocalFileEntityAdapter,
    base_root: Path,
) -> None:
    """``quick`` + why + what → a hypothesis Opportunity + a draft Requirement
    whose ``source`` == the opp id; the chain is whole on disk."""
    result = capture_idea(
        repo_foundation=repo_foundation,
        repo_pd=repo_pd,
        repo_org_slash_name=_REPO,
        roadmap_base_dir=base_root,
        why_intensity="quick",
        why=_WHY,
        what=_WHAT,
        seed="lands-opp-and-req",
    )

    assert _OPP_ID_RE.match(result["opportunity_id"])
    assert _REQ_ID_RE.match(result["requirement_id"])
    assert result["roadmap"] is False
    assert result["bootstrapped"] is True

    opp = repo_pd.find_by_id("opportunity", result["opportunity_id"])
    req = repo_pd.find_by_id("requirement", result["requirement_id"])
    assert opp is not None, "Opportunity was not persisted"
    assert req is not None, "Requirement was not persisted"

    # The Opportunity is a thinly-populated hypothesis (quick path).
    assert opp["state"] == "hypothesis"
    # The Requirement traces to the *real* Opportunity id capture just emitted.
    assert req["source"] == result["opportunity_id"]

    # Chain whole: opp.for_product resolves to a Product, which resolves to a
    # Tenant — all on disk.
    product = repo_pd.find_by_id("product", opp["for_product"])
    assert product is not None
    assert product["id"] == result["chain"]["product_id"]
    tenant = repo_foundation.find_by_id("tenant", product["belongs_to_tenant"])
    assert tenant is not None
    assert tenant["id"] == result["chain"]["tenant_id"]


def test_quick_capture_what_none_opportunity_stands_alone(
    repo_foundation: LocalFileEntityAdapter,
    repo_pd: LocalFileEntityAdapter,
    base_root: Path,
) -> None:
    """``what=None`` → Opportunity stands alone as hypothesis; no Requirement,
    ``requirement_id`` is ``None`` (FR-03 tail clause)."""
    result = capture_idea(
        repo_foundation=repo_foundation,
        repo_pd=repo_pd,
        repo_org_slash_name=_REPO,
        roadmap_base_dir=base_root,
        why_intensity="quick",
        why=_WHY,
        what=None,
        seed="opp-stands-alone",
    )

    assert _OPP_ID_RE.match(result["opportunity_id"])
    assert result["requirement_id"] is None

    opp = repo_pd.find_by_id("opportunity", result["opportunity_id"])
    assert opp is not None
    assert opp["state"] == "hypothesis"

    # No Requirement instance anywhere.
    req_dir = repo_pd.base_dir / "product-development" / "requirement"
    assert not req_dir.exists() or list(req_dir.glob("*.jsonld")) == []


def test_full_capture_reads_analyst_opportunity_by_id(
    repo_foundation: LocalFileEntityAdapter,
    repo_pd: LocalFileEntityAdapter,
    base_root: Path,
) -> None:
    """``full`` path: given an Opportunity the analyst already emitted (ADR-004
    store hand-off), capture reads it back by id and sources the Requirement
    from it — without re-emitting the Opportunity."""
    # Simulate the analyst's prior emission: bootstrap the chain, then emit a
    # matured (validated) Opportunity against the real Product. This is the
    # store hand-off — capture and the analyst share the entity, not a call.
    from _brain_capture import bootstrap_backing_chain

    chain = bootstrap_backing_chain(
        repo_foundation=repo_foundation,
        repo_pd=repo_pd,
        repo_org_slash_name=_REPO,
    )
    analyst_opp = compose_opportunity_from_idea(
        job_statement="A matured why the analyst pressure-tested.",
        for_product=chain.product_id,
        seed="analyst-opp-001",
        state="validated",
    )
    repo_pd.save("opportunity", analyst_opp)

    result = capture_idea(
        repo_foundation=repo_foundation,
        repo_pd=repo_pd,
        repo_org_slash_name=_REPO,
        roadmap_base_dir=base_root,
        why_intensity="full",
        what=_WHAT,
        seed="full-reads-analyst",
        opportunity_id=analyst_opp["id"],
    )

    # Capture sourced the Requirement from the analyst's id (not a new opp).
    assert result["opportunity_id"] == analyst_opp["id"]
    assert _REQ_ID_RE.match(result["requirement_id"])

    req = repo_pd.find_by_id("requirement", result["requirement_id"])
    assert req is not None
    assert req["source"] == analyst_opp["id"]

    # The analyst's Opportunity was read back, not overwritten — its matured
    # state survives.
    opp = repo_pd.find_by_id("opportunity", analyst_opp["id"])
    assert opp is not None
    assert opp["state"] == "validated"


def test_full_capture_dangling_opportunity_degrades(
    repo_foundation: LocalFileEntityAdapter,
    repo_pd: LocalFileEntityAdapter,
    base_root: Path,
) -> None:
    """``full`` path with an ``opportunity_id`` that doesn't resolve →
    ``CaptureError``, and **no Requirement emitted** (NFR-01, no orphan)."""
    dangling = "dna:opportunity:" + "0123456789ABCDEFGHJKMNPQRS"

    with pytest.raises(CaptureError):
        capture_idea(
            repo_foundation=repo_foundation,
            repo_pd=repo_pd,
            repo_org_slash_name=_REPO,
            roadmap_base_dir=base_root,
            why_intensity="full",
            what=_WHAT,
            seed="full-dangling",
            opportunity_id=dangling,
        )

    # No Requirement was emitted — the orphan was refused.
    req_dir = repo_pd.base_dir / "product-development" / "requirement"
    assert not req_dir.exists() or list(req_dir.glob("*.jsonld")) == []


def test_capture_is_idempotent_on_seed(
    repo_foundation: LocalFileEntityAdapter,
    repo_pd: LocalFileEntityAdapter,
    base_root: Path,
    instances_dir: Path,
) -> None:
    """Capturing twice with the same seed → same ids, same file set (NFR-04)."""
    kwargs = dict(
        repo_foundation=repo_foundation,
        repo_pd=repo_pd,
        repo_org_slash_name=_REPO,
        roadmap_base_dir=base_root,
        why_intensity="quick",
        why=_WHY,
        what=_WHAT,
        seed="idempotent-seed",
    )

    first = capture_idea(**kwargs)  # type: ignore[arg-type]
    files_after_first = _instance_files(instances_dir)

    second = capture_idea(**kwargs)  # type: ignore[arg-type]
    files_after_second = _instance_files(instances_dir)

    assert second["opportunity_id"] == first["opportunity_id"]
    assert second["requirement_id"] == first["requirement_id"]
    # No new instance files — overwrite-in-place, no duplicates.
    assert files_after_second == files_after_first


def test_roadmap_flag_appends_members(
    repo_foundation: LocalFileEntityAdapter,
    repo_pd: LocalFileEntityAdapter,
    base_root: Path,
) -> None:
    """``roadmap=True`` → both the opp and req ids land in the Roadmap sidecar
    (WP-005), with idempotent set semantics on re-capture."""
    result = capture_idea(
        repo_foundation=repo_foundation,
        repo_pd=repo_pd,
        repo_org_slash_name=_REPO,
        roadmap_base_dir=base_root,
        why_intensity="quick",
        why=_WHY,
        what=_WHAT,
        seed="roadmap-flag",
        roadmap=True,
    )

    assert result["roadmap"] is True

    members = roadmap_members(base_root)
    assert result["opportunity_id"] in members
    assert result["requirement_id"] in members

    # Idempotent: a second capture (same seed) doesn't duplicate members.
    capture_idea(
        repo_foundation=repo_foundation,
        repo_pd=repo_pd,
        repo_org_slash_name=_REPO,
        roadmap_base_dir=base_root,
        why_intensity="quick",
        why=_WHY,
        what=_WHAT,
        seed="roadmap-flag",
        roadmap=True,
    )
    members_again = roadmap_members(base_root)
    assert members_again == members
    assert members_again.count(result["opportunity_id"]) == 1


# ─── NFR-01 no-orphan + degradation contracts (explicit branch pins) ─────


def test_full_capture_missing_opportunity_id_degrades(
    repo_foundation: LocalFileEntityAdapter,
    repo_pd: LocalFileEntityAdapter,
    base_root: Path,
    instances_dir: Path,
) -> None:
    """``full`` with no ``opportunity_id`` → ``CaptureError`` naming the missing
    id; no Requirement emitted (the full path *needs* the analyst's id)."""
    with pytest.raises(CaptureError) as excinfo:
        capture_idea(
            repo_foundation=repo_foundation,
            repo_pd=repo_pd,
            repo_org_slash_name=_REPO,
            roadmap_base_dir=base_root,
            why_intensity="full",
            what=_WHAT,
            seed="full-missing-id",
            opportunity_id=None,
        )

    assert "opportunity" in str(excinfo.value).lower()
    req_dir = instances_dir / "product-development" / "requirement"
    assert not req_dir.exists() or list(req_dir.glob("*.jsonld")) == []


def test_full_capture_chain_broken_opportunity_degrades(
    repo_foundation: LocalFileEntityAdapter,
    repo_pd: LocalFileEntityAdapter,
    base_root: Path,
    instances_dir: Path,
) -> None:
    """``full`` where the Opportunity resolves but its ``for_product`` does NOT
    → ``CaptureError`` (chain incomplete); no orphan Requirement (NFR-01).

    Construct an Opportunity that points at a Product id with no instance on
    disk — the analyst (or a partial write) left a dangling parent ref.
    """
    orphan_product = "dna:product:" + "0123456789ABCDEFGHJKMNPQRS"
    analyst_opp = compose_opportunity_from_idea(
        job_statement="A why whose product was never persisted.",
        for_product=orphan_product,
        seed="chain-broken-opp",
        state="validated",
    )
    repo_pd.save("opportunity", analyst_opp)

    with pytest.raises(CaptureError) as excinfo:
        capture_idea(
            repo_foundation=repo_foundation,
            repo_pd=repo_pd,
            repo_org_slash_name=_REPO,
            roadmap_base_dir=base_root,
            why_intensity="full",
            what=_WHAT,
            seed="full-chain-broken",
            opportunity_id=analyst_opp["id"],
        )

    assert "chain" in str(excinfo.value).lower()
    # No Requirement was emitted; only the (deliberately) chain-broken opp file.
    req_dir = instances_dir / "product-development" / "requirement"
    assert not req_dir.exists() or list(req_dir.glob("*.jsonld")) == []


def test_brain_unavailable_store_degrades_to_capture_error(
    base_root: Path,
) -> None:
    """A brain-unavailable store yields ``CaptureError``, never an uncaught
    crash (NFR-01) — mirroring ``_brain_emit_helper``'s defensive discipline.

    A repository whose ``save`` raises (here: a missing vendored schema, by
    pointing the adapter at an empty schemas dir) must surface as a plain
    ``CaptureError``, not propagate the raw exception to the host.
    """
    broken_foundation = LocalFileEntityAdapter(
        base_dir=base_root / "instances",
        domain="foundation",
        schemas_dir=base_root / "no-such-schemas",
    )
    broken_pd = LocalFileEntityAdapter(
        base_dir=base_root / "instances",
        domain="product-development",
        schemas_dir=base_root / "no-such-schemas",
    )

    with pytest.raises(CaptureError) as excinfo:
        capture_idea(
            repo_foundation=broken_foundation,
            repo_pd=broken_pd,
            repo_org_slash_name=_REPO,
            roadmap_base_dir=base_root,
            why_intensity="quick",
            why=_WHY,
            what=_WHAT,
            seed="brain-unavailable",
        )

    assert "store is unavailable" in str(excinfo.value).lower()
