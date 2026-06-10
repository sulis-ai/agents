"""Characterisation lock — the `--intent` value is stored VERBATIM, end to end.

The intent-contamination lesson: at interactive change-creation, the founder's
`intent` brief got the assistant's own turn-state (a greeting / plan / reply)
spliced into the middle. Root cause was the INTERACTIVE skill path (the agent
authoring `--intent` from its own turn-state) — fixed as a behavioural contract
in `skills/change/SKILL.md`. The PIPELINE itself (what `sulis-change start`
stores, and the brief the spawned session opens on) was already faithful.

These tests PIN that pipeline faithfulness so it cannot silently regress:

  1. `sulis-change start --intent "<sentinel>"` writes `change.json` whose
     `intent` field equals the sentinel EXACTLY (no truncation, no rewrite).
  2. The change pre-prompt brief built from that intent (the `pre_prompt.txt`
     the spawned session reads) CONTAINS the sentinel and contains NO
     assistant-turn text — i.e. the brief is a faithful carrier of the
     founder's words, never a place the agent's reply can leak into.
  3. The sidecar write (`launch_change_terminal`) writes that brief to
     `~/.sulis/changes/{id}/pre_prompt.txt` BYTE-FOR-BYTE — so the sentinel
     survives the disk round-trip the spawned `claude` actually `cat`s.

This is a lock, not a RED→GREEN: the pipeline is already clean. If a future
change re-introduces a paraphrase / rewrite / contamination in the storage or
brief-assembly layer, one of these assertions fails.
"""

from __future__ import annotations

import importlib.util
import json
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest import mock

import _change_state
import _terminal_launcher

_SCRIPTS = Path(__file__).resolve().parents[2]
_SC_PATH = _SCRIPTS / "sulis-change"


def _load_sulis_change():
    loader = SourceFileLoader("sulis_change_mod_verbatim", str(_SC_PATH))
    spec = importlib.util.spec_from_loader("sulis_change_mod_verbatim", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


sc = _load_sulis_change()

# A sentinel that is unmistakably the founder's own words — no assistant could
# produce this string by paraphrase, so any rewrite/truncation is caught.
SENTINEL = "FOUNDER_VERBATIM_SENTINEL_5PG04R5MMJE4 fix the wobbly login redirect"

# Phrases an assistant turn-state would contain if it leaked into the brief.
ASSISTANT_TURN_MARKERS = [
    "I'm ready to help",
    "I can see you're on the",
    "Here goes",
    "Let me",
    "I'll start a new piece of work",
]


def test_start_stores_intent_verbatim_in_change_json(local_git_repo, run_tool):
    """`sulis-change start --intent "<sentinel>"` stores it EXACTLY in change.json.

    Real subprocess start against a temp git repo; the autouse fixture points
    SULIS_STATE_DIR at a per-test tmp dir, so `change.json` lands there and the
    real ~/.sulis stays clean (the SulisChangeStarter.ts:18-20 seam).
    """
    result = run_tool(
        "sulis-change", "start",
        "--repo-root", str(local_git_repo),
        "--slug", "fix-login-redirect",
        "--primitive", "fix",
        "--intent", SENTINEL,
    )
    assert result.ok, f"start failed: stderr={result.stderr}"

    change_id = result.data["change_id"]
    # change.json under {SULIS_STATE_DIR}/changes/{id}/ — read it back from disk.
    record_path = _change_state.change_dir(change_id) / "change.json"
    assert record_path.exists(), f"no change.json at {record_path}"
    record = json.loads(record_path.read_text())

    # The intent is the founder's words, byte-for-byte — not a paraphrase, not
    # truncated, not concatenated with anything.
    assert record["intent"] == SENTINEL


def test_pre_prompt_brief_carries_intent_verbatim_and_no_assistant_text():
    """The change brief CONTAINS the sentinel and NO assistant-turn text.

    `_build_change_pre_prompt` assembles the brief the spawned session opens on
    (and that lands in `pre_prompt.txt`). It is a faithful carrier of the
    founder's intent — the sentinel appears verbatim, and nothing the agent
    would say in its own turn (greeting / plan / "let me") is present.
    """
    body = sc._build_change_pre_prompt(
        change_id="01HYQC71000000000000000000",
        handle="CH-01HYQC",
        slug="fix-login-redirect",
        intent=SENTINEL,
        primitive="fix",
        context_md_path=Path("/home/x/.sulis/changes/abc/CONTEXT.md"),
    )
    assert SENTINEL in body, "the founder's verbatim intent must appear in the brief"
    for marker in ASSISTANT_TURN_MARKERS:
        assert marker not in body, (
            f"assistant-turn text leaked into the change brief: {marker!r}"
        )


def test_pre_prompt_sidecar_is_written_byte_for_byte(tmp_path, monkeypatch):
    """`launch_change_terminal` writes the brief to pre_prompt.txt UNCHANGED.

    The spawned `claude` reads the brief by `cat`-ing this sidecar (#86), so the
    sentinel must survive the disk round-trip exactly. We redirect Path.home()
    to a tmp dir (the sidecar lives under ~/.sulis/changes/{id}/) and stub the
    platform dispatcher so NO real terminal/process is launched — the test
    exercises only the sidecar write.
    """
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))

    worktree = tmp_path / "wt"
    worktree.mkdir()
    change_id = "01HYQC71000000000000000000"

    brief = sc._build_change_pre_prompt(
        change_id=change_id, handle="CH-01HYQC", slug="fix-login-redirect",
        intent=SENTINEL, primitive="fix",
        context_md_path=Path("/home/x/.sulis/changes/abc/CONTEXT.md"),
    )

    # Stub the dispatcher: the launch must NOT spawn anything; we only want the
    # sidecar write (which happens before dispatch) to run.
    spawned = {
        "status": "spawned", "pid": 1, "pid_kind": "session", "tty": "ttys000",
        "terminal_app_used": "stub", "script_path": "/x", "session_json_path": "",
        "error": None,
    }
    with mock.patch.object(
        _terminal_launcher, "_dispatch_for_platform",
        return_value=lambda *a, **k: spawned,
    ):
        _terminal_launcher.launch_change_terminal(
            change_id=change_id, worktree_path=worktree, pre_prompt=brief,
        )

    sidecar = fake_home / ".sulis" / "changes" / change_id / "pre_prompt.txt"
    assert sidecar.exists(), f"no pre_prompt.txt at {sidecar}"
    written = sidecar.read_text()
    # Byte-for-byte: the brief the spawned session reads is exactly what we built.
    assert written == brief
    # And the founder's verbatim words survived, with no assistant text spliced in.
    assert SENTINEL in written
    for marker in ASSISTANT_TURN_MARKERS:
        assert marker not in written
