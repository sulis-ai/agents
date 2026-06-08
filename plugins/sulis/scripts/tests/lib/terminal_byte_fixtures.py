"""WP-001 (CH-01KTGY) — the recorded terminal byte-stub fixtures: the cross-kind
shared contract artifact for the interactive-terminal-sessions change.

This module is BOTH the fixture loader (consumed by every backend + frontend WP)
AND the contract-conformance test that pins the fixture set's shape. It is the
executable form of the terminal contract extension §2.14 (CF-04: error + empty
cases, not happy-path only) — the prose stays the source of truth; these
fixtures are the recorded reality both kinds bind to (mirrors the base
contract's §2.10 recorded NDJSON for chat).

Test (RED first, per the WP Definition of Done):
    terminal_byte_fixtures.py::test_fixture_set_covers_cf04_cases
"""

from __future__ import annotations

import base64
import binascii
import json
from pathlib import Path

# ─── Shared fixture identity (CF-11 / rubric 6.06) — the canonical constant ───
#
# This is the single source of fixture identity. Downstream WPs (backend
# integration replays, frontend mock-first <LiveTerminal/>) reference these
# names VERBATIM — no WP re-chooses a path. The string value of FIXTURE_DIR is
# the repo-relative location (under plugins/sulis/scripts/) pinned by the
# WP-001 Contract; resolve a usable filesystem path via `fixture_path()`.

#: Repo-relative (under the scripts root) location of the recorded `.ndjson`
#: sequences — the shared artifact both kinds read. Pinned by the WP-001
#: Contract; do not re-derive it elsewhere.
FIXTURE_DIR = "tests/lib/fixtures/terminal"

#: The recorded terminal byte-stub set. Key = canonical case id (referenced
#: downstream); value = the `.ndjson` filename under FIXTURE_DIR. Each maps to a
#: §2.14 case and an acceptance criterion (CF-04: error + empty, not happy-only).
FIXTURES = {
    "attach_renders_scrollback": "attach_renders_scrollback.ndjson",   # §2.14 #1, acceptance #1
    "two_way_roundtrip":         "two_way_roundtrip.ndjson",           # §2.14 #2, acceptance #2
    "detach_leaves_running":     "detach_leaves_running.ndjson",       # §2.14 #3, acceptance #3
    "headless_pipe_regression":  "headless_pipe_regression.ndjson",   # §2.14 #4, acceptance #4
    "visible_lifecycle":         "visible_lifecycle.ndjson",          # §2.14 #5, acceptance #5
    "error_not_pty_session":     "error_not_pty_session.ndjson",      # §2.14 #6
    "error_no_session":          "error_no_session.ndjson",           # §2.14 #6
    "error_socket_closed_mid":   "error_socket_closed_mid.ndjson",    # §2.14 #6
}

#: One-line docstring per fixture: which acceptance criterion it proves (Blue).
#: A consumer reads this to know *why* a fixture exists, without re-reading the
#: contract prose. Keyed identically to FIXTURES.
FIXTURE_DOCS = {
    "attach_renders_scrollback": "acceptance #1 — attach renders existing scrollback (a snapshot phase), not a blank pane.",
    "two_way_roundtrip":         "acceptance #2 — feed('ls\\n') and the command's output appears in the live feed.",
    "detach_leaves_running":     "acceptance #3 — detach leaves the session alive (viewer_count 0); re-attach catches up.",
    "headless_pipe_regression":  "acceptance #4 — a pipe session runs the base chat turn unchanged; attach → NOT_PTY_SESSION.",
    "visible_lifecycle":         "acceptance #5 — pty child dies → restart re-creates the pty; idle pty (0 viewers) is evicted.",
    "error_not_pty_session":     "§2.14 #6 error stub — attach on a pipe session returns Expected NOT_PTY_SESSION.",
    "error_no_session":          "§2.14 #6 error stub — attach on a never-opened key returns Expected NO_SESSION.",
    "error_socket_closed_mid":   "§2.14 #6 error stub — the attach stream drops mid-feed (Protocol SOCKET_CLOSED).",
}

#: The scripts root (plugins/sulis/scripts) — FIXTURE_DIR is relative to it.
_SCRIPTS_ROOT = Path(__file__).resolve().parents[2]


def fixture_path(key: str) -> Path:
    """Resolve the absolute filesystem path of the recorded fixture for `key`.

    `key` is a canonical id from :data:`FIXTURES`. The single resolution point
    both kinds use, so no consumer re-implements FIXTURE_DIR joining.
    """
    return _SCRIPTS_ROOT / FIXTURE_DIR / FIXTURES[key]


#: The six §2.14 cases the CF-04 fixture set MUST cover (the three error stubs
#: are part of case #6). Pinned here so the test asserts coverage by name, not
#: by count — a renamed/dropped case fails loudly.
_REQUIRED_FIXTURE_KEYS = {
    "attach_renders_scrollback",  # §2.14 #1 — acceptance #1 (not-a-blank-pane)
    "two_way_roundtrip",          # §2.14 #2 — acceptance #2 (type → output)
    "detach_leaves_running",      # §2.14 #3 — acceptance #3
    "headless_pipe_regression",   # §2.14 #4 — acceptance #4 (regression gate)
    "visible_lifecycle",          # §2.14 #5 — acceptance #5
    "error_not_pty_session",      # §2.14 #6 — error stub (NOT_PTY_SESSION)
    "error_no_session",           # §2.14 #6 — error stub (NO_SESSION)
    "error_socket_closed_mid",    # §2.14 #6 — error stub (SOCKET_CLOSED mid-stream)
}


def test_fixture_set_covers_cf04_cases() -> None:
    """The CF-04 contract for the terminal byte-stub fixture set (§2.14).

    Asserts, against the module's exported identity (FIXTURE_DIR + FIXTURES):

    1. FIXTURES names every required §2.14 case (incl. the three error stubs).
    2. Every referenced `.ndjson` file exists under FIXTURE_DIR.
    3. Each file is valid NDJSON (one JSON object per non-blank line).
    4. Every streaming `term.data` line is base64-decodable (the §2.13.1 binary
       -in-JSON encoding) — the fixtures are honest recorded bytes, not stubs
       that would corrupt a consumer's base64 decode.
    5. Every fixture carries a one-line doc (FIXTURE_DOCS) naming its criterion.
    6. The snapshot-then-live join holds: within an attach stream a `snapshot`
       phase never follows a `live` one — the "render existing scrollback first,
       then live" guarantee (§2.12 / acceptance #1).
    """
    # (1) coverage by name — every required case present, no required case dropped
    missing = _REQUIRED_FIXTURE_KEYS - set(FIXTURES)
    assert not missing, f"FIXTURES is missing required §2.14 cases: {sorted(missing)}"

    # (5) every required fixture is documented (which acceptance it proves)
    undocumented = _REQUIRED_FIXTURE_KEYS - set(FIXTURE_DOCS)
    assert not undocumented, f"FIXTURE_DOCS is missing a doc for: {sorted(undocumented)}"

    for key in _REQUIRED_FIXTURE_KEYS:
        filename = FIXTURES[key]
        path = fixture_path(key)

        # (2) the recorded file exists
        assert path.is_file(), f"fixture {key!r} → {filename!r} does not exist at {path}"

        lines = [ln for ln in path.read_text().splitlines() if ln.strip()]
        assert lines, f"fixture {key!r} ({filename!r}) is empty — a stub must record something"

        seen_live = False  # for the snapshot-then-live ordering invariant
        for lineno, line in enumerate(lines, start=1):
            # (3) valid NDJSON
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:  # pragma: no cover - asserted below
                raise AssertionError(
                    f"fixture {key!r} ({filename!r}) line {lineno} is not valid JSON: {exc}"
                ) from exc
            assert isinstance(obj, dict), (
                f"fixture {key!r} ({filename!r}) line {lineno} is not a JSON object"
            )

            # (4) every streaming term line carries base64-decodable data
            term = obj.get("term")
            if isinstance(term, dict) and "data" in term:
                assert term.get("encoding") == "base64", (
                    f"fixture {key!r} ({filename!r}) line {lineno}: term.encoding "
                    f"must be 'base64' (§2.13.1)"
                )
                try:
                    base64.b64decode(term["data"], validate=True)
                except (binascii.Error, ValueError) as exc:
                    raise AssertionError(
                        f"fixture {key!r} ({filename!r}) line {lineno}: term.data "
                        f"is not valid base64: {exc}"
                    ) from exc

                # (6) snapshot-then-live: a snapshot phase must not follow a live one
                phase = term.get("phase")
                if phase == "live":
                    seen_live = True
                elif phase == "snapshot":
                    assert not seen_live, (
                        f"fixture {key!r} ({filename!r}) line {lineno}: a 'snapshot' "
                        f"term follows a 'live' one — violates the snapshot-then-live "
                        f"join (§2.12)"
                    )
