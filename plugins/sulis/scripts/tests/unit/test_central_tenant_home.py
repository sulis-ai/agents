"""Tests for the central Tenant home wiring (WP-013, ADR-005).

ADR-005 is a **reuse, not build** decision: the cross-repo Platform home for
living entities (Product / Opportunity) is the EXISTING ``LocalFileEntityAdapter``
pointed at the EXISTING convention ``~/.sulis/instances/{tenant_id}/``, read back
by the EXISTING ``iter_entities`` flat-file walk. No new SQLite store, no new
adapter, no new query class — SQLite is deferred behind the same port.

This change wires the "follow-up slice" the ``_tenant_emission.py`` module
docstring already promised: it adds

  - ``central_tenant_home(tenant_id)`` — resolves the central Tenant-namespaced
    home (``{sulis_state_base()}/instances/{tenant_id}/``), the single cross-repo
    boundary keyed by the deterministic Tenant ULID; and
  - ``find_current_for_tenant(*, tenant_id, entity_type)`` — every OPEN-window
    (current) entity of ``entity_type`` for the Tenant, read from that central
    home via the existing ``iter_entities`` walk.

These run against a **real** ``LocalFileEntityAdapter`` over a real temp central
home (MEA-09 — no mock at the store seam). ``SULIS_STATE_DIR`` is repointed at a
tmp dir for every test by the root conftest's ``_isolate_sulis_state`` fixture,
so ``central_tenant_home`` (which routes through ``sulis_state_base()``) resolves
hermetically without any patching here.

The cross-repo proof (``test_cross_repo_tenant_read``) is the load-bearing one:
two emits "from two different repos" (two writers, two distinct repo roots) land
in the SAME central Tenant home and are BOTH visible to one Tenant-scoped read —
which a single repo-local ``.brain/instances`` walk cannot do. That is the whole
point of the central home, and the assertion that proves it is reuse done right.
"""

from __future__ import annotations

import os
from pathlib import Path

from _brain_query import find_current_for_tenant
from _brain_emit_helper import central_tenant_home
from _entity_adapter_local import LocalFileEntityAdapter
from _entity_evolve import evolve_entity
from _tenant_emission import _deterministic_ulid_from


_DOMAIN = "product-development"
_RUN_ID = "dna:lifecyclerun:01JX0RUNRUNRUNRUNRUNRUNRUN"

# A deterministic Tenant id (same recipe _tenant_emission uses) — the cross-repo
# identity every repo naming this Tenant resolves to.
_TENANT_NAME = "Acme Co"
_TENANT_ID = f"dna:tenant:{_deterministic_ulid_from(f'tenant-name:{_TENANT_NAME}')}"

_PRODUCT_ID = "dna:product:01JX0AAAAAAAAAAAAAAAAAAAAA"
_PRODUCT_ID_2 = "dna:product:01JX0BBBBBBBBBBBBBBBBBBBBB"


def _product_body(eid: str, *, name: str, state: str = "active") -> dict:
    """A schema-valid Product body (the load-bearing required fields)."""
    return {
        "id": eid,
        "name": name,
        "belongs_to_tenant": _TENANT_ID,
        "state": state,
        "sys_status": "active",
    }


def _central_adapter(tenant_id: str) -> LocalFileEntityAdapter:
    """The EXISTING file adapter pointed at the central Tenant home — the whole
    of ADR-005's wiring is exactly this ``base_dir`` (no new adapter type)."""
    return LocalFileEntityAdapter(
        base_dir=central_tenant_home(tenant_id), domain=_DOMAIN
    )


# ─── central_tenant_home resolution ──────────────────────────────────────────


class TestCentralTenantHomeResolution:
    """``central_tenant_home`` resolves the central convention
    ``{sulis_state_base()}/instances/{tenant_id}/``."""

    def test_resolves_instances_tenant_subtree(self) -> None:
        home = central_tenant_home(_TENANT_ID)
        # The conftest points SULIS_STATE_DIR at a tmp dir; the home lives under
        # {that}/instances/{tenant_id}/.
        state_base = Path(os.environ["SULIS_STATE_DIR"])
        assert home == state_base / "instances" / _TENANT_ID


class TestTenantUlidReusesExistingDerivation:
    """The Tenant ULID in the home path is the EXISTING deterministic derivation
    (``_deterministic_ulid_from('tenant-name:<name>')``) byte-exact — no new
    mint, no second recipe (ADR-005 Blue gate)."""

    def test_tenant_ulid_reuses_existing_derivation(self) -> None:
        # Derive the Tenant id the same way _tenant_emission does, independently,
        # and assert the home is namespaced by exactly that id.
        expected_ulid = _deterministic_ulid_from(f"tenant-name:{_TENANT_NAME}")
        expected_id = f"dna:tenant:{expected_ulid}"
        assert _TENANT_ID == expected_id, "the test fixture id must match the recipe"

        home = central_tenant_home(expected_id)
        # The final path component is the deterministic Tenant id, unaltered.
        assert home.name == expected_id


# ─── round-trip against the existing adapter ─────────────────────────────────


class TestRoundTripCentralHome:
    """Save a living-entity version to the central home via the existing adapter,
    read it back via the Tenant-scoped read — reuse, no new persistence code."""

    def test_round_trip_central_home(self) -> None:
        adapter = _central_adapter(_TENANT_ID)
        evolve_entity(
            repo=adapter,
            entity_type="product",
            entity_id=_PRODUCT_ID,
            new_fields=_product_body(_PRODUCT_ID, name="Acme Billing"),
            generated_by=_RUN_ID,
            at="2026-01-01T00:00:00Z",
        )

        current = find_current_for_tenant(
            tenant_id=_TENANT_ID, entity_type="product"
        )
        assert len(current) == 1
        assert current[0]["id"] == _PRODUCT_ID
        assert current[0]["name"] == "Acme Billing"
        assert current[0]["state"] == "active"
        # the returned window is the OPEN one
        assert current[0].get("valid_to") in (None, "")


# ─── the cross-repo proof (the load-bearing test) ────────────────────────────


class TestCrossRepoTenantRead:
    """Two emits "from two different repos" (two writers at two distinct repo
    roots) under ONE Tenant land in the SAME central Tenant home and are BOTH
    returned by ``find_current_for_tenant``. A single repo-local tree read
    cannot return both — that is why the central home exists (ADR-005)."""

    def test_cross_repo_tenant_read(self, tmp_path: Path) -> None:
        # Repo A and Repo B are two distinct working copies. Each one's living
        # emit points base_dir at the SAME central home (resolved purely from the
        # Tenant id, NOT from the repo root) — that is the cross-repo wiring.
        repo_a_local = tmp_path / "repo-a" / ".brain" / "instances"
        repo_b_local = tmp_path / "repo-b" / ".brain" / "instances"

        # Emit Product-1 "from repo A", Product-2 "from repo B" — both through the
        # central-home adapter (one adapter instance per writer, same base_dir).
        adapter_from_a = _central_adapter(_TENANT_ID)
        evolve_entity(
            repo=adapter_from_a,
            entity_type="product",
            entity_id=_PRODUCT_ID,
            new_fields=_product_body(_PRODUCT_ID, name="From Repo A"),
            generated_by=_RUN_ID,
            at="2026-01-01T00:00:00Z",
        )

        adapter_from_b = _central_adapter(_TENANT_ID)
        evolve_entity(
            repo=adapter_from_b,
            entity_type="product",
            entity_id=_PRODUCT_ID_2,
            new_fields=_product_body(_PRODUCT_ID_2, name="From Repo B"),
            generated_by=_RUN_ID,
            at="2026-01-01T00:00:00Z",
        )

        # The Tenant-scoped read over the central home returns BOTH — across repos.
        current = find_current_for_tenant(
            tenant_id=_TENANT_ID, entity_type="product"
        )
        names = sorted(w["name"] for w in current)
        assert names == ["From Repo A", "From Repo B"], (
            "both same-Tenant Products, emitted from two repos, must be visible "
            "from the one central Tenant home"
        )

        # Control: neither repo-local tree alone can return both — that's the
        # whole reason the central home is needed (the proof it's load-bearing).
        from _brain_query import find_entities

        from_a_only = find_entities(
            repo_a_local, domain=_DOMAIN, entity_type="product"
        )
        from_b_only = find_entities(
            repo_b_local, domain=_DOMAIN, entity_type="product"
        )
        assert from_a_only == [] and from_b_only == [], (
            "a repo-local .brain/instances walk sees neither Product — they live "
            "in the central Tenant home, not in either repo tree"
        )


# ─── only-open-windows + durability ──────────────────────────────────────────


class TestOnlyOpenWindowsReturned:
    """A closed window (an evolved-past version) is NOT returned by
    ``find_current_for_tenant`` — only the current OPEN window per entity."""

    def test_only_open_windows_returned(self) -> None:
        adapter = _central_adapter(_TENANT_ID)
        # First version (will be closed), then an evolution (the new open window).
        evolve_entity(
            repo=adapter,
            entity_type="product",
            entity_id=_PRODUCT_ID,
            new_fields=_product_body(_PRODUCT_ID, name="Acme", state="active"),
            generated_by=_RUN_ID,
            at="2026-01-01T00:00:00Z",
        )
        evolve_entity(
            repo=adapter,
            entity_type="product",
            entity_id=_PRODUCT_ID,
            new_fields=_product_body(_PRODUCT_ID, name="Acme", state="maintenance"),
            generated_by=_RUN_ID,
            at="2026-02-01T00:00:00Z",
        )

        current = find_current_for_tenant(
            tenant_id=_TENANT_ID, entity_type="product"
        )
        # exactly ONE current entry — the open (maintenance) window, not the
        # closed (active) one.
        assert len(current) == 1
        assert current[0]["state"] == "maintenance"
        assert current[0].get("valid_to") in (None, "")


class TestAtomicWriteDurable:
    """Central-home write durability is the file adapter's existing atomic
    write-tmp-then-rename (inherited, not re-implemented): a committed window
    survives, and no half-written ``.tmp`` file is ever visible to the read."""

    def test_atomic_write_durable(self) -> None:
        adapter = _central_adapter(_TENANT_ID)
        evolve_entity(
            repo=adapter,
            entity_type="product",
            entity_id=_PRODUCT_ID,
            new_fields=_product_body(_PRODUCT_ID, name="Durable"),
            generated_by=_RUN_ID,
            at="2026-01-01T00:00:00Z",
        )

        # The committed window survives and is readable.
        current = find_current_for_tenant(
            tenant_id=_TENANT_ID, entity_type="product"
        )
        assert len(current) == 1 and current[0]["name"] == "Durable"

        # No half-written tmp file is left visible in the on-disk tree (the
        # write-tmp-then-rename leaves only the final {ulid}.jsonld).
        type_dir = central_tenant_home(_TENANT_ID) / _DOMAIN / "product"
        leftovers = [p.name for p in type_dir.iterdir() if p.name.endswith(".tmp")]
        assert leftovers == [], f"no torn-write tmp files must remain: {leftovers}"
