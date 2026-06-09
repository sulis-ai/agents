"""SC-17 — a business decision (BDR) is recorded distinct from a technical ADR.

This is the methodology-tier verification artifact named by WP-012's
`verification.artifact` field. The load-bearing behavioural assertions live in
`tests/unit/test_decision_emission.py` (branch-CI runs only `tests/unit/` —
lesson #60), so this module re-exports the SC-17 cases by name rather than
duplicating them. Binding the SC-17 verification name to the unit-tier cases
means SC-17 resolves under the methodology tier AND runs under the unit tier
where CI exercises it.

SC-17 (DESIGN.md §6.5 T11, FR-17): emitting a BDR carries `kind: bdr`, distinct
from an emitted ADR (`kind: adr`); the absent-kind migration default reads as
`adr` (§9.1); and ≥2 decisions in one run get distinct `@id`s (the bundled
collision fix).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

# Load the unit-tier module by file path so this works under any pytest import
# mode (the `tests` package has no top-level __init__.py, so a `tests.unit.*`
# package import is not reliable across rootdir/import-mode permutations).
_UNIT_MODULE_PATH = (
    Path(__file__).resolve().parent.parent / "unit" / "test_decision_emission.py"
)
_spec = importlib.util.spec_from_file_location(
    "_sc17_decision_emission_cases", _UNIT_MODULE_PATH
)
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

# Re-export the SC-17 behavioural cases so they collect + run here under the
# methodology tier too. Canonical definitions stay unit-tier (CI runs that).
TestKindDiscriminator = _mod.TestKindDiscriminator
TestMultiDecisionNoIdCollision = _mod.TestMultiDecisionNoIdCollision
