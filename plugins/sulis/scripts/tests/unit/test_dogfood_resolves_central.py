"""Dogfood proof: Sulis's OWN captures resolve to the central user-level home.

This is the behavioural proof that gated the in-repo `brain_location` pin
removal. Unlike `test_brain_location.py` — which characterises the *resolver's
capability* against synthetic tmp contracts — this test reads **Sulis's real
`.sulis/repo-contract.yml`** and asserts what its actual configuration produces.
It is the proof that Sulis itself de-branch-scopes its brain: a capture made
anywhere in the repo (including a throwaway change worktree) lands in the shared
user-level settings home (`sulis_state_base()/.brain/instances`) and survives
the worktree being removed at ship — NOT trapped under `repo_root`.

This test was introduced `xfail(strict=True)` while Sulis's repo-contract still
pinned the legacy in-repo location (`brain_location: .brain/instances`): the
resolver honoured the pin and resolved under the repo root, so the assertion
expectedly failed. Removing the pin made the resolver fall through to the
central default — the assertion now holds, and strict-xfail forced the pin
removal to delete the marker (an unexpected XPASS would otherwise have failed
the suite). With the pin gone this asserts as a normal GREEN test.

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
