"""WP-005 — tests for the Roadmap sidecar reader + writer (ADR-001).

The Roadmap flag is stored in a per-repo sidecar file
``.brain/labels/roadmap.jsonld`` keyed by entity id — never a field on the
entity (the vendored schemas are ``unevaluatedProperties: false``, so a
``roadmap`` property would fail validation at the adapter boundary; ADR-001).

This WP owns both ends of the sidecar:

* the **writer** — ``_brain_capture.roadmap_add`` (set semantics, sorted,
  idempotent; creates the file/dir; rewrites a malformed file cleanly), and
* the **member reader** — ``_brain_query.roadmap_members`` (returns sorted
  ids; missing OR malformed file → ``[]``, never raises — NFR-01).

``base_dir`` is the ``.brain/`` root; the sidecar lives at
``base_dir / "labels" / "roadmap.jsonld"`` (ADR-001 on-disk shape:
``{"label": "roadmap", "members": [...]}``).

No mocks: the functions are plain ``json`` read/write over a temp ``.brain/``,
so the tests run against the real filesystem (MEA-09 — no mocking what you own).
"""

from __future__ import annotations

import json
from pathlib import Path

from _brain_capture import roadmap_add
from _brain_query import roadmap_members

_OPP = "dna:opportunity:01J0000000000000000000000A"
_REQ = "dna:requirement:01J0000000000000000000000B"


def _sidecar_path(base_dir: Path) -> Path:
    return base_dir / "labels" / "roadmap.jsonld"


def test_add_creates_file_on_first_call(tmp_path: Path) -> None:
    """Fresh temp dir; after ``roadmap_add`` the sidecar exists with the member."""
    base = tmp_path / ".brain"

    roadmap_add(base, [_OPP])

    sidecar = _sidecar_path(base)
    assert sidecar.exists()
    data = json.loads(sidecar.read_text())
    assert data["label"] == "roadmap"
    assert data["members"] == [_OPP]


def test_add_is_idempotent_set_semantics(tmp_path: Path) -> None:
    """Adding the same id twice → one member; members stay sorted (NFR-04)."""
    base = tmp_path / ".brain"

    roadmap_add(base, [_REQ, _OPP])
    roadmap_add(base, [_OPP])  # re-add existing → no-op

    members = json.loads(_sidecar_path(base).read_text())["members"]
    assert members == sorted([_OPP, _REQ])
    assert members.count(_OPP) == 1


def test_members_empty_when_file_absent(tmp_path: Path) -> None:
    """``roadmap_members`` on a dir with no sidecar → ``[]``, no error."""
    base = tmp_path / ".brain"  # never created

    assert roadmap_members(base) == []


def test_members_empty_when_file_malformed(tmp_path: Path) -> None:
    """Sidecar containing junk → ``[]``, no error (best-effort, NFR-01)."""
    base = tmp_path / ".brain"
    sidecar = _sidecar_path(base)
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text("}{ this is not json")

    assert roadmap_members(base) == []


def test_add_rewrites_malformed_file(tmp_path: Path) -> None:
    """``roadmap_add`` over a malformed file produces a clean valid sidecar."""
    base = tmp_path / ".brain"
    sidecar = _sidecar_path(base)
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text("not json at all")

    roadmap_add(base, [_OPP])

    data = json.loads(sidecar.read_text())
    assert data == {"label": "roadmap", "members": [_OPP]}


def test_round_trip(tmp_path: Path) -> None:
    """``roadmap_add([a, b])`` then ``roadmap_members`` → ``[a, b]`` sorted."""
    base = tmp_path / ".brain"

    roadmap_add(base, [_REQ, _OPP])

    assert roadmap_members(base) == sorted([_OPP, _REQ])


def test_members_empty_when_members_not_a_list(tmp_path: Path) -> None:
    """Well-formed JSON but ``members`` is the wrong shape → ``[]`` (NFR-01).

    A sidecar that parses as JSON but whose ``members`` is not a list (e.g. a
    string) must degrade to ``[]`` rather than raising — the best-effort read
    contract covers shape corruption, not just parse corruption.
    """
    base = tmp_path / ".brain"
    sidecar = _sidecar_path(base)
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text(json.dumps({"label": "roadmap", "members": "not-a-list"}))

    assert roadmap_members(base) == []


def test_add_over_wrong_shape_rewrites_clean(tmp_path: Path) -> None:
    """``roadmap_add`` over a parses-but-wrong-shape sidecar rewrites cleanly.

    Tolerant write (ADR-001 "Armor" row): an existing sidecar whose ``members``
    is not a list is treated as having no members and is rewritten to the clean
    canonical shape rather than failing.
    """
    base = tmp_path / ".brain"
    sidecar = _sidecar_path(base)
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text(json.dumps({"label": "roadmap", "members": 42}))

    roadmap_add(base, [_OPP])

    data = json.loads(sidecar.read_text())
    assert data == {"label": "roadmap", "members": [_OPP]}
