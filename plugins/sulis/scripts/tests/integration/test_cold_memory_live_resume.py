"""Integration — the LIVE assemble→inject resume path on a COLD memory
(CH-GJ9KQR WP-011, the headline acceptance; TDD §3.2 the
``◀── assembled payload ──`` arrow, §4 degrade path, §5 Proof, ADR-004/005).

**This is the load-bearing acceptance: a COLD-memory live-path observation.**
WP-009 proved the warm-memory live path (a checkpoint pre-seeded). A consumer
reality check then found the rich path only fires *given a saved memory* — but
in the live flow a memory is never established: the assembler hard-requires
``get_memory`` (``MEMORY_NOT_FOUND`` when absent) and the only thing that writes
one, ``SessionManager.checkpoint``, is a dead hook with zero live callers. So
the COMMON first-resume case (death / login-expiry / fresh attach, before any
checkpoint has run) degraded to the plain brief and the rich context never
landed.

This drive inverts that. It runs the REAL :class:`SessionManager` resume on a
thread that has durable **messages but NO pre-existing ``ThreadMemory``** (no
``put_memory``, no ``checkpoint`` called) with the **provider transcript
unavailable**, and OBSERVES the rich fragment reaching the brief the
(re)spawned agent receives (the ``pre_prompt.txt`` sidecar the adapter's
``spawn_argv`` resolves) — carrying:

  * the **conversation summary regenerated ON DEMAND from the durable
    messages** (the load-bearing move — no checkpoint produced it), AND
  * **REAL Working Set content** (a sentinel from a real
    ``.changes/*.WORKING-SET.md``), AND
  * **REAL brain content** (a real ``.brain/instances/**/*.jsonld`` entity),

within the standard-tier budget, vendor-neutral (no Claude-JSONL structure).

A test that pre-creates the memory (``put_memory``), or calls ``checkpoint``
itself, or constructs ``ContextPayloadAssembler`` / ``seed_payload_for_resume``
directly, does NOT satisfy this WP — the cold-memory live path is the point.
"""

from __future__ import annotations

import sys
from pathlib import Path

from _session_manager import thread_contract as tc
from _session_manager.adapter import SessionSpec
from _session_manager.events import Event
from _session_manager.manager import SessionManager
from _session_manager.thread_store_local import LocalThreadStore

# The bound change's real ULID — the brief seam validates ``brief_change_id`` as
# a real change ULID before joining it into the sidecar path
# (claude_pty._read_pre_prompt defence-in-depth), so a handle like "CH-GJ9KQR"
# would be ignored. thread_id == session.key (one thread per change, ADR-004).
_CHANGE_ID = "01KVX26BDXGJ9KQRJ11HACHMZV"
_KEY = _CHANGE_ID
_THREAD_ID = _CHANGE_ID
_STEM = "create-portable-agent-context"

# Distinctive sentinels asserted in the brief — proving the content is REAL
# (read from the durable messages / on-disk Working Set + brain), not the
# empty-lambda default or a pre-seeded memory.
_MESSAGE_SENTINEL = "COLD-RESUME-MSG-SENTINEL-зон"  # non-latin: vendor-neutral path
_WORKING_SET_SENTINEL = "PORTABLE-CONTEXT-WS-SENTINEL-зон"
_BRAIN_ENTITY_NAME = "Resume recovers rich context from our store"

# A Claude-JSONL structural marker — the payload must be vendor-neutral, so this
# must NOT appear in the assembled brief fragment.
_CLAUDE_JSONL_MARKER = '"type":"assistant"'


class _BriefRecordingPtyAdapter:
    """A minimal real ``ProviderAdapter`` that keeps its child alive and records
    the resolved brief the SAME way ``claude_pty.spawn_argv`` does — by reading
    the change's ``pre_prompt.txt`` sidecar at the spawn boundary.

    Reused from WP-009's harness (the observation surface, not a mocked-out
    collaborator on the assemble path — the store, readers, and assembler
    reached through the manager are all real, MEA-09)."""

    class _Caps:
        supports_resume = True

    def __init__(self) -> None:
        self.capabilities = _BriefRecordingPtyAdapter._Caps()
        self.recorded_brief: str | None = None

    def spawn_argv(self, spec: SessionSpec) -> list[str]:
        change_id = (spec.brief_change_id or "").strip()
        sidecar = Path.home() / ".sulis" / "changes" / change_id / "pre_prompt.txt"
        self.recorded_brief = (
            sidecar.read_text(encoding="utf-8") if sidecar.is_file() else None
        )
        return [sys.executable, "-c", "import sys; sys.stdin.read()"]

    def encode(self, command: str) -> bytes:
        return command.encode() + b"\n"

    def decode(self, line: bytes) -> Event | None:
        return None

    def turn_complete(self, event: Event) -> bool:
        return False


def _seed_cold_store(root: Path, *, message_bodies: list[str]) -> LocalThreadStore:
    """A real durable store with a thread + durable **messages** but **NO memory
    checkpoint** — the cold-memory case. Crucially: NO ``put_memory``, NO
    ``checkpoint`` is called. The rich path must regenerate the summary on demand
    from these messages alone."""
    store = LocalThreadStore(change_id=_CHANGE_ID, root=root)
    now = "2026-06-24T00:00:00Z"
    store.put_thread(
        tc.Thread(
            id=_THREAD_ID,
            platform_id="local",
            topic="portable-agent-context",
            activity_summary=None,
            created_at=now,
            updated_at=now,
            participant_count=1,
            resumed_from=None,
        )
    )
    for i, text in enumerate(message_bodies):
        store.append_message(
            _THREAD_ID,
            tc.ThreadMessage(
                id=f"{_THREAD_ID}-{i}",
                participant_id="studio_agent",
                participant_type="studio_agent",
                content=text,
                role="observation",
                created_at=now,
                order=i,
            ),
        )
    # Deliberately NO put_memory — assemble() must hit MEMORY_NOT_FOUND and
    # regenerate from the messages above.
    return store


def _write_working_set(repo_root: Path, *, body: str | None = None) -> None:
    """A real ``.changes/{stem}.WORKING-SET.md`` carrying a distinctive sentinel
    plus the sibling ``.changes/{stem}.yaml`` binding the reader resolves the
    stem from — exactly as a real change worktree carries both."""
    ws_dir = repo_root / ".changes"
    ws_dir.mkdir(parents=True, exist_ok=True)
    (ws_dir / f"{_STEM}.yaml").write_text(
        f'change_id: "{_CHANGE_ID}"\n'
        'handle: "CH-GJ9KQR"\n'
        'slug: "portable-agent-context"\n'
        'primitive: "create"\n',
        encoding="utf-8",
    )
    text = body or (
        "# Working Set — portable-agent-context\n\n"
        "## 1. Problem\n"
        f"The headline resume must recover rich context. {_WORKING_SET_SENTINEL}\n\n"
        "## 2. Current best solution\nWire the on-demand summary into the cold path.\n"
    )
    (ws_dir / f"{_STEM}.WORKING-SET.md").write_text(text, encoding="utf-8")


def _write_brain_entity(repo_root: Path) -> None:
    """A real ``.brain/instances/**/*.jsonld`` entity for the bound change whose
    ``name`` the live brief must surface (REAL brain content)."""
    ent_dir = repo_root / ".brain" / "instances" / "product-development" / "scenario"
    ent_dir.mkdir(parents=True, exist_ok=True)
    (ent_dir / "RESUMESCENARIO000000000000.jsonld").write_text(
        "{\n"
        '  "id": "dna:scenario:RESUMESCENARIO000000000000",\n'
        f'  "name": "{_BRAIN_ENTITY_NAME}",\n'
        '  "state": "draft",\n'
        '  "sys_status": "active"\n'
        "}\n",
        encoding="utf-8",
    )


def _manager(store: LocalThreadStore) -> SessionManager:
    adapter = _BriefRecordingPtyAdapter()
    mgr = SessionManager(
        {"claude": adapter},
        start_maintenance=False,
        thread_store_factory=lambda change_id: store,
    )
    mgr._test_adapter = adapter  # type: ignore[attr-defined]
    return mgr


def _point_home_at_empty(tmp_path: Path, monkeypatch) -> Path:
    """Provider transcript unavailable: HOME at an empty dir (no
    ``~/.claude/projects``), and ``Path.home()`` pinned to it so the sidecar is
    resolved under the test HOME."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    return home


def test_cold_memory_live_resume_regenerates_rich_brief(
    tmp_path: Path, monkeypatch
) -> None:
    """The REAL ``SessionManager`` resume on a thread with durable messages but
    NO pre-existing memory regenerates the structured summary ON DEMAND and
    composes the rich payload into the brief — carrying the conversation summary
    (from the durable messages, no checkpoint produced it) PLUS REAL Working Set
    + REAL brain content, within the standard-tier budget, vendor-neutral, with
    the provider transcript unavailable.

    This is the headline acceptance the consumer reality check found broken: the
    FIRST resume, before any checkpoint, must land the rich context — not the
    plain brief."""
    _point_home_at_empty(tmp_path, monkeypatch)

    repo_root = tmp_path / "worktree"
    repo_root.mkdir()
    _write_working_set(repo_root)
    _write_brain_entity(repo_root)

    # Durable messages only — NO checkpoint memory. The sentinel must reach the
    # brief via on-demand regeneration from these messages.
    store = _seed_cold_store(
        tmp_path / "threads",
        message_bodies=[
            f"wired the durable sink {_MESSAGE_SENTINEL}",
            "assembled the resume payload",
        ],
    )
    mgr = _manager(store)
    try:
        spec = SessionSpec(
            provider="claude", cwd=str(repo_root), brief_change_id=_CHANGE_ID
        )
        mgr.open(_KEY, spec)

        brief = mgr._test_adapter.recorded_brief  # type: ignore[attr-defined]
        assert brief is not None, "manager composed no brief into the sidecar"

        # The conversation summary regenerated ON DEMAND from the durable
        # messages reached the brief — the load-bearing move (no checkpoint
        # produced this).
        assert _MESSAGE_SENTINEL in brief, (
            "the cold-resume brief is missing the conversation summary "
            "regenerated from the durable messages"
        )
        # REAL Working Set content reached the brief (not empty-lambda output).
        assert _WORKING_SET_SENTINEL in brief, (
            "the cold-resume brief is missing REAL Working Set content"
        )
        # REAL brain content reached the brief.
        assert _BRAIN_ENTITY_NAME in brief, (
            "the cold-resume brief is missing REAL brain content"
        )
        # Vendor-neutral: no Claude-JSONL structure.
        assert _CLAUDE_JSONL_MARKER not in brief, (
            "the assembled brief leaked a Claude-JSONL structural marker"
        )

        # Within the standard-tier budget — measure the assembled fragment
        # precisely (the portion from the shared header), not the whole brief.
        from _session_manager.context_payload import (
            ContextPayloadAssembler,
            estimate_tokens,
        )
        from _session_manager.durable_sink import BRIEF_FRAGMENT_HEADER

        budget = ContextPayloadAssembler.TIER_BUDGETS["standard"]
        assert brief.count(BRIEF_FRAGMENT_HEADER) == 1, (
            "expected exactly one resumed-context fragment in the brief"
        )
        fragment = BRIEF_FRAGMENT_HEADER + brief.split(BRIEF_FRAGMENT_HEADER, 1)[1]
        assert estimate_tokens(fragment) <= budget, (
            "the assembled cold-resume fragment exceeded the standard-tier budget"
        )
    finally:
        mgr.shutdown()


def test_cold_memory_resume_large_working_set_stays_within_budget(
    tmp_path: Path, monkeypatch
) -> None:
    """A LARGE ``.changes/*.WORKING-SET.md`` must still yield a brief fragment
    within the standard-tier budget (WP-009 ADV-1 folded here): today the
    assembler trims messages + journal but copies ``participant_context`` (the
    Working Set + brain text) through VERBATIM — so a large Working Set ships an
    over-budget brief mislabelled standard tier. The budget guarantee must hold
    for a large Working Set, not just a large thread."""
    _point_home_at_empty(tmp_path, monkeypatch)

    repo_root = tmp_path / "worktree"
    repo_root.mkdir()
    # A pathologically large Working Set (~100KB ≈ ~25k tokens at ~4 chars/token,
    # far above the 1500-token standard budget). The fragment must still fit.
    big_body = (
        "# Working Set — portable-agent-context\n\n## 1. Problem\n"
        + (f"Lots of reasoning state. {_WORKING_SET_SENTINEL} " * 4000)
        + "\n"
    )
    _write_working_set(repo_root, body=big_body)
    _write_brain_entity(repo_root)

    store = _seed_cold_store(
        tmp_path / "threads", message_bodies=["a single durable message"]
    )
    mgr = _manager(store)
    try:
        spec = SessionSpec(
            provider="claude", cwd=str(repo_root), brief_change_id=_CHANGE_ID
        )
        mgr.open(_KEY, spec)

        brief = mgr._test_adapter.recorded_brief  # type: ignore[attr-defined]
        assert brief is not None

        from _session_manager.context_payload import (
            ContextPayloadAssembler,
            estimate_tokens,
        )
        from _session_manager.durable_sink import BRIEF_FRAGMENT_HEADER

        budget = ContextPayloadAssembler.TIER_BUDGETS["standard"]
        assert brief.count(BRIEF_FRAGMENT_HEADER) == 1
        fragment = BRIEF_FRAGMENT_HEADER + brief.split(BRIEF_FRAGMENT_HEADER, 1)[1]
        assert estimate_tokens(fragment) <= budget, (
            "a large Working Set shipped an over-budget brief mislabelled standard "
            "tier — participant_context was not trimmed into the tier budget"
        )
    finally:
        mgr.shutdown()


def test_cold_memory_with_no_messages_still_degrades(
    tmp_path: Path, monkeypatch
) -> None:
    """The genuinely-unrecoverable case — a thread with NO messages AND no memory
    — still degrades to the plain brief, isolated and logged, NEVER raised into
    the spawn (WP-004 ADV-1 isolation, pinned). On-demand regeneration has
    nothing to build from, so there is no rich fragment to compose."""
    _point_home_at_empty(tmp_path, monkeypatch)
    home = Path.home()

    repo_root = tmp_path / "worktree"
    repo_root.mkdir()
    _write_working_set(repo_root)

    # A store with a thread but NO messages AND no memory → nothing to
    # regenerate. The live wiring must isolate that and degrade.
    store = LocalThreadStore(change_id=_CHANGE_ID, root=tmp_path / "threads")
    now = "2026-06-24T00:00:00Z"
    store.put_thread(
        tc.Thread(
            id=_THREAD_ID,
            platform_id="local",
            topic=None,
            activity_summary=None,
            created_at=now,
            updated_at=now,
            participant_count=1,
            resumed_from=None,
        )
    )

    change_dir = home / ".sulis" / "changes" / _CHANGE_ID
    change_dir.mkdir(parents=True, exist_ok=True)
    default_marker = "DEFAULT-ONLY-BRIEF"
    (change_dir / "pre_prompt.txt").write_text(
        f"Bound to {_CHANGE_ID}. {default_marker}\n", encoding="utf-8"
    )

    mgr = _manager(store)
    try:
        spec = SessionSpec(
            provider="claude", cwd=str(repo_root), brief_change_id=_CHANGE_ID
        )
        # The spawn must not raise — isolation is the contract.
        session = mgr.open(_KEY, spec)
        assert session is not None
        brief = mgr._test_adapter.recorded_brief  # type: ignore[attr-defined]
        assert brief is not None
        # Degraded to the default brief; no rich Working Set fragment.
        assert default_marker in brief
        assert _WORKING_SET_SENTINEL not in brief
    finally:
        mgr.shutdown()
