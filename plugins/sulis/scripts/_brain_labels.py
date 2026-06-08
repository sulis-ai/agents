"""Shared on-disk shape for the Brain sidecar **label** files (ADR-001).

A *label* is a cross-cutting tag that doesn't belong on the tagged record.
The Roadmap flag is the first one: the backing-chain schemas are
``unevaluatedProperties: false``, so a ``roadmap`` property on an Opportunity
or Requirement would fail validation at the adapter boundary. Instead the flag
lives in a per-repo **sidecar** file keyed by entity id —
``.brain/labels/roadmap.jsonld`` — with the shape::

    {"label": "roadmap", "members": ["dna:opportunity:01J...", ...]}

The writer (``_brain_capture.roadmap_add``) and the reader
(``_brain_query.roadmap_members``) both need to agree on the filename, the
``label`` value, and where the file sits under ``.brain/``. That agreement
lives here, **once** — so the two modules can't drift, and if the Brain
contract later grows first-class labels this is the single migration point
(ADR-001 consequence).
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

#: The sidecar's ``label`` value and its on-disk filename stem.
ROADMAP_LABEL: Final[str] = "roadmap"

#: The sidecar path relative to the ``.brain/`` root, as path segments.
ROADMAP_SIDECAR_RELPATH: Final[tuple[str, ...]] = ("labels", "roadmap.jsonld")


def roadmap_sidecar_path(base_dir: Path) -> Path:
    """The Roadmap sidecar's path under a ``.brain/`` root.

    Args:
        base_dir: the ``.brain/`` root.

    Returns:
        ``base_dir / "labels" / "roadmap.jsonld"``.
    """
    return Path(base_dir).joinpath(*ROADMAP_SIDECAR_RELPATH)
