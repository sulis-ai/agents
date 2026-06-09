"""#258 — the runtime driver allow-list and the vendored schema enum MUST agree.

`_scenario_runtime.IMPLEMENTATION_KINDS` is the runtime allow-list: which
`Tool.implementation_kind` values the scenario runtime knows how to resolve to
a driver. `plugins/sulis/brain/compiled/foundation/tool.schema.json`'s
`implementation_kind` enum is the *persistence* allow-list: which values the
LocalFileEntityAdapter will accept when writing a Tool to the brain store.

These two are independent allow-lists that mirror the same concept. When they
diverge, a Tool can validate at the runtime layer but be rejected at
persistence (or vice-versa) — a silent split-brain. That is exactly what
happened in CH-01KTMA: journey-rigor #207 added `browser` to the runtime
frozenset but not to the vendored schema enum, so a `browser`-kind Tool ran
fine in-memory yet could not be persisted (SF-164c3e5f).

This guard makes the next such divergence fail loudly here, at CI time,
instead of split-braining in production.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_SCRIPTS_DIR = _HERE.parents[2]
_REPO_ROOT = _HERE.parents[5]
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from _scenario_runtime import IMPLEMENTATION_KINDS  # noqa: E402

_SCHEMA_PATH = (
    _REPO_ROOT
    / "plugins"
    / "sulis"
    / "brain"
    / "compiled"
    / "foundation"
    / "tool.schema.json"
)


def _schema_enum() -> set[str]:
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    return set(schema["properties"]["implementation_kind"]["enum"])


def test_runtime_allowlist_matches_schema_enum() -> None:
    """The runtime allow-list and the vendored schema enum must be identical.

    If you add a member to one, add it to the other in the same change — a
    runtime kind that can't be persisted (or a persistable kind the runtime
    can't resolve) is a split-brain bug.
    """
    runtime = set(IMPLEMENTATION_KINDS)
    schema = _schema_enum()

    runtime_only = runtime - schema
    schema_only = schema - runtime
    assert not runtime_only and not schema_only, (
        "implementation_kind split-brain (#258):\n"
        f"  in runtime IMPLEMENTATION_KINDS but NOT in the vendored "
        f"tool.schema.json enum: {sorted(runtime_only) or '—'}\n"
        f"  in the schema enum but NOT in the runtime allow-list: "
        f"{sorted(schema_only) or '—'}\n"
        "Add the missing member(s) to BOTH "
        "(_scenario_runtime.IMPLEMENTATION_KINDS and "
        "plugins/sulis/brain/compiled/foundation/tool.schema.json) so a "
        "Tool that validates at runtime can also be persisted."
    )
