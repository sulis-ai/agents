"""Tests for `_brain_query.read_as_of` — the as-of-time window read (WP-010).

`read_as_of` is the READ side of the bitemporal window chain (ADR-003). WP-009's
`evolve_entity` writes the windows (close prior / open new, keyed by stable
entity id); `read_as_of` answers *"which version was true at instant T?"* —
given `(entity_type, entity_id, as_of)` it returns the window whose half-open
``[valid_from, valid_to)`` interval contains ``as_of``.

Semantics under test (TDD Form #6; the WP Contract):
  - returns the window whose ``[valid_from, valid_to)`` contains ``as_of``;
  - an open window (``valid_to is None``) is treated as ``valid_to == +inf`` —
    so ``as_of`` after the latest window opens returns that open window;
  - ``as_of`` before the first window's ``valid_from`` returns ``None``;
  - the interval is **half-open**: ``as_of == valid_to`` of window N belongs to
    window N+1 (not N) — windows abut exactly with no overlap;
  - it reuses the existing ``iter_entities`` flat-file walk — the same envelope
    layout WP-009 writes — and selects against the persisted ``windows`` list.

These tests run against **real** persisted envelopes over a temp dir (MEA-09 —
no mock at the store seam). Two seeding routes are exercised:
  - directly-written envelopes (precise control of window boundaries), and
  - envelopes produced by the real ``evolve_entity`` helper (proves the read
    selects exactly against what the write side produces).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from _brain_query import read_as_of
from _entity_adapter_local import LocalFileEntityAdapter
from _entity_evolve import evolve_entity


_PRODUCT_ID = "dna:product:01JX0AAAAAAAAAAAAAAAAAAAAA"
_RUN_ID = "dna:lifecyclerun:01JX0RVNRVNRVNRVNRVNRVNRVN"


# ─── direct-envelope seeding (precise window boundaries) ─────────────────────


def _write_envelope(
    base_dir: Path,
    *,
    domain: str,
    entity_type: str,
    entity_id: str,
    windows: list[dict],
) -> None:
    """Write a history envelope directly at the adapter's on-disk layout
    (``{base}/{domain}/{entity_type}/{ulid}.jsonld``), bypassing the write
    helper — gives a test exact control over each window's boundaries."""
    ulid = entity_id.rsplit(":", 1)[-1]
    path = base_dir / domain / entity_type / f"{ulid}.jsonld"
    path.parent.mkdir(parents=True, exist_ok=True)
    envelope = {"id": entity_id, "entity_type": entity_type, "windows": windows}
    path.write_text(json.dumps(envelope, indent=2, sort_keys=True))


def _three_window_envelope(base_dir: Path) -> None:
    """A product with two closed windows + one open window:
    W0: [2026-01-01, 2026-02-01)   state=active
    W1: [2026-02-01, 2026-03-01)   state=maintenance
    W2: [2026-03-01, +inf)         state=deprecated  (open)
    """
    _write_envelope(
        base_dir,
        domain="product-development",
        entity_type="product",
        entity_id=_PRODUCT_ID,
        windows=[
            {
                "id": _PRODUCT_ID,
                "name": "Acme",
                "state": "active",
                "valid_from": "2026-01-01T00:00:00Z",
                "valid_to": "2026-02-01T00:00:00Z",
            },
            {
                "id": _PRODUCT_ID,
                "name": "Acme",
                "state": "maintenance",
                "valid_from": "2026-02-01T00:00:00Z",
                "valid_to": "2026-03-01T00:00:00Z",
            },
            {
                "id": _PRODUCT_ID,
                "name": "Acme",
                "state": "deprecated",
                "valid_from": "2026-03-01T00:00:00Z",
                "valid_to": None,
            },
        ],
    )


@pytest.fixture
def base_dir(tmp_path: Path) -> Path:
    return tmp_path / ".brain" / "instances"


# ─── the window-selection contract ──────────────────────────────────────────


class TestReturnsWindowContainingAsOf:
    """Given three windows, an as-of query returns the window whose half-open
    interval contains the timestamp — one assertion per window."""

    def test_returns_window_containing_as_of(self, base_dir: Path) -> None:
        _three_window_envelope(base_dir)

        # a time inside each closed window returns that window
        w0 = read_as_of(
            entity_type="product",
            entity_id=_PRODUCT_ID,
            as_of="2026-01-15T00:00:00Z",
            base_dir=base_dir,
        )
        assert w0 is not None and w0["state"] == "active"

        w1 = read_as_of(
            entity_type="product",
            entity_id=_PRODUCT_ID,
            as_of="2026-02-15T00:00:00Z",
            base_dir=base_dir,
        )
        assert w1 is not None and w1["state"] == "maintenance"

        w2 = read_as_of(
            entity_type="product",
            entity_id=_PRODUCT_ID,
            as_of="2026-03-15T00:00:00Z",
            base_dir=base_dir,
        )
        assert w2 is not None and w2["state"] == "deprecated"

    def test_valid_from_inclusive_lower_bound(self, base_dir: Path) -> None:
        """``as_of == valid_from`` of a window belongs to THAT window (the lower
        bound is inclusive)."""
        _three_window_envelope(base_dir)
        w = read_as_of(
            entity_type="product",
            entity_id=_PRODUCT_ID,
            as_of="2026-02-01T00:00:00Z",
            base_dir=base_dir,
        )
        assert w is not None and w["state"] == "maintenance"


class TestAsOfInOpenWindowReturnsOpen:
    """``as_of`` after the latest window opens returns the open window
    (``valid_to is None`` == +inf)."""

    def test_as_of_in_open_window_returns_open(self, base_dir: Path) -> None:
        _three_window_envelope(base_dir)
        w = read_as_of(
            entity_type="product",
            entity_id=_PRODUCT_ID,
            as_of="2099-01-01T00:00:00Z",
            base_dir=base_dir,
        )
        assert w is not None
        assert w["state"] == "deprecated"
        assert w["valid_to"] is None, "the open window has no upper bound"


class TestAsOfBeforeFirstReturnsNone:
    """``as_of`` before the first window's ``valid_from`` returns ``None`` —
    the entity did not exist yet."""

    def test_as_of_before_first_returns_none(self, base_dir: Path) -> None:
        _three_window_envelope(base_dir)
        w = read_as_of(
            entity_type="product",
            entity_id=_PRODUCT_ID,
            as_of="2025-12-31T23:59:59Z",
            base_dir=base_dir,
        )
        assert w is None

    def test_unknown_entity_returns_none(self, base_dir: Path) -> None:
        """A never-seen entity id returns ``None`` (no envelope on disk)."""
        _three_window_envelope(base_dir)
        w = read_as_of(
            entity_type="product",
            entity_id="dna:product:01JX0ZZZZZZZZZZZZZZZZZZZZZ",
            as_of="2026-02-15T00:00:00Z",
            base_dir=base_dir,
        )
        assert w is None


class TestBoundaryIsHalfOpen:
    """The interval is half-open: ``as_of == valid_to`` of window N returns
    window N+1, not N (windows abut exactly; no instant maps to two windows)."""

    def test_boundary_is_half_open(self, base_dir: Path) -> None:
        _three_window_envelope(base_dir)
        # 2026-02-01 is W0.valid_to AND W1.valid_from → must return W1.
        w = read_as_of(
            entity_type="product",
            entity_id=_PRODUCT_ID,
            as_of="2026-02-01T00:00:00Z",
            base_dir=base_dir,
        )
        assert w is not None
        assert w["state"] == "maintenance", (
            "as_of == valid_to of W0 is the half-open boundary; it belongs to "
            "W1, not W0"
        )

    def test_no_instant_maps_to_two_windows(self, base_dir: Path) -> None:
        """Every abutting boundary resolves to exactly one window (the later)."""
        _three_window_envelope(base_dir)
        for boundary, expected in (
            ("2026-02-01T00:00:00Z", "maintenance"),
            ("2026-03-01T00:00:00Z", "deprecated"),
        ):
            w = read_as_of(
                entity_type="product",
                entity_id=_PRODUCT_ID,
                as_of=boundary,
                base_dir=base_dir,
            )
            assert w is not None and w["state"] == expected


# ─── real adapter / real evolve_entity (MEA-09) ──────────────────────────────


class TestRunsAgainstRealTempDir:
    """The read selects against envelopes the real ``evolve_entity`` write side
    produces, over a real temp dir — no mock at the store seam (MEA-09)."""

    def test_runs_against_real_temp_dir(self, base_dir: Path) -> None:
        adapter = LocalFileEntityAdapter(
            base_dir=base_dir, domain="product-development"
        )

        body = {
            "id": _PRODUCT_ID,
            "name": "Acme Billing",
            "belongs_to_tenant": "dna:tenant:01JX0TTTTTTTTTTTTTTTTTTTTT",
            "state": "active",
            "sys_status": "active",
        }
        evolve_entity(
            repo=adapter,
            entity_type="product",
            entity_id=_PRODUCT_ID,
            new_fields=body,
            generated_by=_RUN_ID,
            at="2026-01-01T00:00:00Z",
        )
        changed = dict(body, state="maintenance")
        evolve_entity(
            repo=adapter,
            entity_type="product",
            entity_id=_PRODUCT_ID,
            new_fields=changed,
            generated_by=_RUN_ID,
            at="2026-02-01T00:00:00Z",
        )

        # as-of in the first (now closed) window → active
        early = read_as_of(
            entity_type="product",
            entity_id=_PRODUCT_ID,
            as_of="2026-01-15T00:00:00Z",
            base_dir=base_dir,
        )
        assert early is not None and early["state"] == "active"

        # as-of after the second opens → the open maintenance window
        late = read_as_of(
            entity_type="product",
            entity_id=_PRODUCT_ID,
            as_of="2026-06-01T00:00:00Z",
            base_dir=base_dir,
        )
        assert late is not None
        assert late["state"] == "maintenance"
        assert late["valid_to"] is None, "the latest window is open"

    def test_reads_project_in_foundation_domain(self, base_dir: Path) -> None:
        """The signature carries no ``domain`` — a Project (foundation domain,
        no prov edge) is found by the same walk as a product-development
        Product."""
        project_id = "dna:project:01JX0CCCCCCCCCCCCCCCCCCCCC"
        _write_envelope(
            base_dir,
            domain="foundation",
            entity_type="project",
            entity_id=project_id,
            windows=[
                {
                    "id": project_id,
                    "name": "Sulis",
                    "state": "active",
                    "valid_from": "2026-01-01T00:00:00Z",
                    "valid_to": None,
                },
            ],
        )
        w = read_as_of(
            entity_type="project",
            entity_id=project_id,
            as_of="2026-05-01T00:00:00Z",
            base_dir=base_dir,
        )
        assert w is not None and w["name"] == "Sulis"


class TestMissingBaseDir:
    """A base_dir that does not exist yet (no store) returns ``None`` rather
    than raising — the read is total."""

    def test_missing_base_dir_returns_none(self, tmp_path: Path) -> None:
        w = read_as_of(
            entity_type="product",
            entity_id=_PRODUCT_ID,
            as_of="2026-02-15T00:00:00Z",
            base_dir=tmp_path / "does-not-exist",
        )
        assert w is None


class TestMalformedEnvelope:
    """A file at the entity's id without a ``windows`` list (a pre-evolution
    bare snapshot, or corruption) is treated as no-history → ``None``, rather
    than raising."""

    def test_envelope_without_windows_list_returns_none(self, base_dir: Path) -> None:
        # a bare snapshot (no `windows` key) — the shape current-snapshot
        # emitters wrote before evolution turned on.
        ulid = _PRODUCT_ID.rsplit(":", 1)[-1]
        path = base_dir / "product-development" / "product" / f"{ulid}.jsonld"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"id": _PRODUCT_ID, "state": "active"}))

        w = read_as_of(
            entity_type="product",
            entity_id=_PRODUCT_ID,
            as_of="2026-02-15T00:00:00Z",
            base_dir=base_dir,
        )
        assert w is None
