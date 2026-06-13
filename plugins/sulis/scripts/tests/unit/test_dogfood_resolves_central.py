"""Dogfood proof: Sulis's OWN captures resolve to the central user-level home.

This is the test-first RED that gates the in-repo `brain_location` pin removal.
Unlike `test_brain_location.py` — which characterises the *resolver's capability*
against synthetic tmp contracts — this test reads **Sulis's real
`.sulis/repo-contract.yml`** and asserts what its actual configuration produces.
It is the behavioural proof that Sulis itself de-branch-scopes its brain: a
capture made anywhere in the repo (including a throwaway change worktree) lands
in the shared user-level settings home (`sulis_state_base()/.brain/instances`)
and survives the worktree being removed at ship — NOT trapped under `repo_root`.

WHY xfail (strict) RIGHT NOW
----------------------------
Sulis's repo-contract still pins the legacy in-repo location
(`brain_location: .brain/instances`), so the resolver correctly honours that
pin and resolves *under the repo root* today. The pin is removed in the next
piece of work, after which this assertion holds. We mark the test
`xfail(strict=True)` so:

  * the suite stays GREEN now (the failure is the *expected* outcome while the
    pin is present), and
  * once the pin is removed the test PASSES — and strict-xfail then turns a
    now-passing xfail into a FAILURE ("XPASS"), forcing the pin-removal work to
    delete this marker. That is the built-in safety that keeps the two pieces of
    work in lockstep: this test cannot silently rot.

The kept resolver-capability tests in `test_brain_location.py` (the precedence
chain + the relative-pin escape hatch) are deliberately untouched — they test
what the resolver *can* do, independent of Sulis's own config.
"""

from __future__ import annotations

from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2]
import sys  # noqa: E402

if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import pytest  # noqa: E402

from _brain_location import brain_base_dir  # noqa: E402
from _change_state import sulis_state_base  # noqa: E402


def _sulis_repo_root() -> Path:
    """Sulis's own repo root: the nearest ancestor holding the real
    `.sulis/repo-contract.yml`. Reading Sulis's *actual* contract (not a
    synthetic tmp one) is what makes this a dogfood proof rather than a resolver
    capability test."""
    for ancestor in (
        Path(__file__).resolve().parent,
        *Path(__file__).resolve().parents,
    ):
        if (ancestor / ".sulis" / "repo-contract.yml").is_file():
            return ancestor
    raise AssertionError(
        "could not locate Sulis's .sulis/repo-contract.yml from the test file"
    )


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Sulis's in-repo brain_location pin is still present; it is removed in "
        "the pin-removal work, after which Sulis's captures resolve to the "
        "central user-level home and this test passes. strict=True forces the "
        "pin-removal work to delete this marker (XPASS would otherwise fail)."
    ),
)
def test_sulis_captures_resolve_central(tmp_path, monkeypatch):
    # Isolate the settings home so the test never touches the real ~/.sulis
    # (tmp_path is pytest's per-test, auto-cleaned dir — matching the isolation
    # convention in test_brain_location.py), and clear the transient env
    # override so the contract field (or its absence) is what decides — exactly
    # as it does in production.
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path / "home-sulis"))
    monkeypatch.delenv("SULIS_BRAIN_BASE_DIR", raising=False)

    repo_root = _sulis_repo_root()
    central = sulis_state_base() / ".brain" / "instances"

    resolved = brain_base_dir(repo_root)

    # The behavioural assertion: Sulis's captures land in the central
    # user-level home, NOT under the repo/worktree root.
    assert resolved == central
    assert repo_root not in resolved.parents
