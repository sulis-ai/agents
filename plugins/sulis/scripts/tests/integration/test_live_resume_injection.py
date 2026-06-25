"""Integration — the LIVE assemble→inject resume path (CH-GJ9KQR WP-009, the
load-bearing acceptance; TDD §3.2 the ``◀── assembled payload ──`` arrow,
ADR-004/005).

**This is a LIVE-PATH observation, not a component call.** WP-007's drive
constructs the :class:`ContextPayloadAssembler` / calls
``seed_payload_for_resume`` itself — it proved the COMPONENT. This drive goes
through the real :class:`SessionManager` spawn/resume path and OBSERVES the
rich payload reaching the brief the (re)spawned agent actually receives (the
``pre_prompt.txt`` sidecar the adapter's ``spawn_argv`` resolves, ADR-004/005),
carrying **REAL Working Set content** (a string from a real
``.changes/*.WORKING-SET.md``) AND **REAL brain content** (a real
``.brain/instances/**/*.jsonld`` entity) — not the empty-lambda default — with
the **provider transcript unavailable** (``HOME`` pointed at an empty dir so
``~/.claude/projects`` carries nothing).

The headline gap GAP-1 + GAP-2 this pins:

  * GAP-1 — ``ContextPayloadAssembler`` + ``seed_payload_for_resume`` are
    referenced ONLY in tests; the live ``manager`` spawn/resume seam never
    assembles+injects the payload. This drive asserts the live manager DOES.
  * GAP-2 — the assembler's ``working_set_reader`` / ``brain_reader`` default
    to empty lambdas. This drive asserts the live wiring injects REAL readers,
    so the brief carries real Working Set + real brain content.
"""

from __future__ import annotations

import sys
from pathlib import Path

from _session_manager import thread_contract as tc
from _session_manager.adapter import SessionSpec
from _session_manager.events import Event
from _session_manager.manager import SessionManager
from _session_manager.thread_store_local import LocalThreadStore

# A real change ULID — the brief seam validates ``brief_change_id`` as a real
# change ULID before joining it into the sidecar path (claude_pty._read_pre_prompt
# defence-in-depth), so a handle like "CH-GJ9KQR" would be ignored. This is the
# bound change's real ULID; thread_id == session.key (one thread per change,
# ADR-004).
_CHANGE_ID = "01KVX26BDXGJ9KQRJ11HACHMZV"
_KEY = _CHANGE_ID
_THREAD_ID = _CHANGE_ID
_STEM = "create-portable-agent-context"

# Distinctive sentinels we assert reach the brief — proving the content is REAL
# (read from the on-disk Working Set + brain entity), not empty-lambda output.
_WORKING_SET_SENTINEL = (
    "PORTABLE-CONTEXT-WS-SENTINEL-зон"  # non-latin: vendor-neutral text path
)
_BRAIN_ENTITY_NAME = "Resume recovers rich context from our store"

# A Claude-JSONL structural marker — the payload must be vendor-neutral, so this
# must NOT appear in the assembled brief fragment.
_CLAUDE_JSONL_MARKER = '"type":"assistant"'


class _BriefRecordingPtyAdapter:
    """A minimal real ``ProviderAdapter`` that (a) keeps its child alive so the
    manager's spawn/liveness assertions hold and (b) records the resolved brief
    the SAME way ``claude_pty.spawn_argv`` does — by reading the change's
    ``pre_prompt.txt`` sidecar.

    The observation surface (WP-009 acceptance note): the test asserts on what
    the MANAGER composed into the brief seam, observed at the spawn boundary —
    the stub is the recorder, not a mocked-out collaborator on the assemble
    path (the store, readers, and assembler reached through the manager are all
    real)."""

    class _Caps:
        supports_resume = True

    def __init__(self) -> None:
        self.capabilities = _BriefRecordingPtyAdapter._Caps()
        self.recorded_brief: str | None = None

    def spawn_argv(self, spec: SessionSpec) -> list[str]:
        # Resolve the SAME sidecar the real interactive adapter reads
        # (~/.sulis/changes/{change_id}/pre_prompt.txt under the test HOME) and
        # record its bytes — this is the brief the (re)spawned agent receives.
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


def _seed_store(root: Path) -> LocalThreadStore:
    """A real durable store with a thread + messages + a checkpoint memory, so
    the assembler has a real memory to read on the resume path."""
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
    msgs = [
        tc.ThreadMessage(
            id=f"{_THREAD_ID}-{i}",
            participant_id="studio_agent",
            participant_type="studio_agent",
            content=text,
            role="observation",
            created_at=now,
            order=i,
        )
        for i, text in enumerate(
            ["wired the durable sink", "assembled the resume payload"]
        )
    ]
    for m in msgs:
        store.append_message(_THREAD_ID, m)
    # A checkpoint so ``assemble`` finds a memory (else MEMORY_NOT_FOUND).
    store.put_memory(
        _THREAD_ID,
        tc.ThreadMemory(
            thread_id=_THREAD_ID,
            version=1,
            content=tc.ThreadMemoryContent(
                messages=msgs,
                exploration_journal=[
                    tc.ExplorationJournalEntry(
                        type="decision_captured",
                        content="resume seeds from OUR store, never the provider transcript",
                        created_at=now,
                    )
                ],
                participant_context={"change_id": _CHANGE_ID},
            ),
            created_at=now,
            updated_at=now,
        ),
    )
    return store


def _write_working_set(repo_root: Path) -> None:
    """A real ``.changes/{stem}.WORKING-SET.md`` carrying a distinctive sentinel
    string the live brief must surface (REAL Working Set content), plus the
    sibling ``.changes/{stem}.yaml`` binding (``change_id`` + ``primitive`` +
    ``slug``) the reader resolves the stem from — exactly as a real change
    worktree carries both."""
    ws_dir = repo_root / ".changes"
    ws_dir.mkdir(parents=True, exist_ok=True)
    (ws_dir / f"{_STEM}.yaml").write_text(
        f'change_id: "{_CHANGE_ID}"\n'
        'handle: "CH-GJ9KQR"\n'
        'slug: "portable-agent-context"\n'
        'primitive: "create"\n',
        encoding="utf-8",
    )
    (ws_dir / f"{_STEM}.WORKING-SET.md").write_text(
        "# Working Set — portable-agent-context\n\n"
        "## 1. Problem\n"
        f"The headline resume must recover rich context. {_WORKING_SET_SENTINEL}\n\n"
        "## 2. Current best solution\nWire the assembler into the live spawn seam.\n",
        encoding="utf-8",
    )


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


def _manager(store: LocalThreadStore, repo_root: str) -> SessionManager:
    adapter = _BriefRecordingPtyAdapter()
    mgr = SessionManager(
        {"claude": adapter},
        start_maintenance=False,
        thread_store_factory=lambda change_id: store,
    )
    # Expose the adapter so the test can read the recorded brief.
    mgr._test_adapter = adapter  # type: ignore[attr-defined]
    return mgr


def test_live_spawn_injects_rich_payload_into_brief(
    tmp_path: Path, monkeypatch
) -> None:
    """The REAL ``SessionManager`` spawn path assembles the resume payload over
    OUR store with REAL readers and composes it into the brief the spawned agent
    receives — carrying REAL Working Set + REAL brain content, within the
    standard-tier budget, vendor-neutral, with the provider transcript
    unavailable."""
    # Provider transcript unavailable: HOME at an empty dir (no ~/.claude/projects).
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))

    # The spawn cwd IS the change worktree — the readers read its on-disk
    # Working Set + brain.
    repo_root = tmp_path / "worktree"
    repo_root.mkdir()
    _write_working_set(repo_root)
    _write_brain_entity(repo_root)

    store = _seed_store(tmp_path / "threads")
    mgr = _manager(store, str(repo_root))
    try:
        spec = SessionSpec(
            provider="claude",
            cwd=str(repo_root),
            brief_change_id=_CHANGE_ID,
        )
        mgr.open(_KEY, spec)

        brief = mgr._test_adapter.recorded_brief  # type: ignore[attr-defined]
        assert brief is not None, "manager composed no brief into the sidecar"

        # REAL Working Set content reached the brief (not empty-lambda output).
        assert _WORKING_SET_SENTINEL in brief, (
            "the live brief is missing REAL Working Set content"
        )
        # REAL brain content reached the brief.
        assert _BRAIN_ENTITY_NAME in brief, (
            "the live brief is missing REAL brain content"
        )
        # Vendor-neutral: no Claude-JSONL structure.
        assert _CLAUDE_JSONL_MARKER not in brief, (
            "the assembled brief leaked a Claude-JSONL structural marker"
        )
        # Within the standard-tier budget (the assembler's hard cap). Measure
        # the ASSEMBLED FRAGMENT precisely (the portion below the shared header),
        # not the whole brief — so the assertion is tight (a raw dump or a
        # duplicate-stacked fragment would blow past it; a generous *2 ceiling on
        # the whole brief would mask both).
        from _session_manager.context_payload import (
            ContextPayloadAssembler,
            estimate_tokens,
        )
        from _session_manager.durable_sink import BRIEF_FRAGMENT_HEADER

        budget = ContextPayloadAssembler.TIER_BUDGETS["standard"]
        # Exactly ONE assembled fragment (idempotency: no stacked duplicates).
        assert brief.count(BRIEF_FRAGMENT_HEADER) == 1, (
            "expected exactly one resumed-context fragment in the brief"
        )
        fragment = BRIEF_FRAGMENT_HEADER + brief.split(BRIEF_FRAGMENT_HEADER, 1)[1]
        assert estimate_tokens(fragment) <= budget, (
            "the assembled fragment exceeded the standard-tier budget — likely a "
            "raw dump, not the structured summary"
        )
    finally:
        mgr.shutdown()


def test_live_spawn_composes_additively_over_default_brief(
    tmp_path: Path, monkeypatch
) -> None:
    """The assembled payload AUGMENTS the change's default brief — it does not
    clobber the change-binding / recon pointer the default carries (WP Contract:
    additive over ``_default_change_pre_prompt``)."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))

    repo_root = tmp_path / "worktree"
    repo_root.mkdir()
    _write_working_set(repo_root)
    _write_brain_entity(repo_root)

    # Pre-write a default change brief into the sidecar (as the launcher does).
    change_dir = home / ".sulis" / "changes" / _CHANGE_ID
    change_dir.mkdir(parents=True, exist_ok=True)
    default_marker = "DEFAULT-CHANGE-BRIEF-BINDING-MARKER"
    (change_dir / "pre_prompt.txt").write_text(
        f"You are Sulis bound to {_CHANGE_ID}. {default_marker}\n",
        encoding="utf-8",
    )

    store = _seed_store(tmp_path / "threads")
    mgr = _manager(store, str(repo_root))
    try:
        spec = SessionSpec(
            provider="claude", cwd=str(repo_root), brief_change_id=_CHANGE_ID
        )
        mgr.open(_KEY, spec)
        brief = mgr._test_adapter.recorded_brief  # type: ignore[attr-defined]
        assert brief is not None
        # The default binding survives AND the rich payload was composed in.
        assert default_marker in brief, "the default change brief was clobbered"
        assert _WORKING_SET_SENTINEL in brief, "the rich payload was not composed in"
    finally:
        mgr.shutdown()


def test_live_spawn_degrades_to_default_when_genuinely_unrecoverable(
    tmp_path: Path, monkeypatch
) -> None:
    """The genuinely-unrecoverable case must degrade to the default brief without
    EVER crashing the spawn (WP-004 isolation).

    Converted in WP-011: previously this seeded "no memory" alone and relied on
    ``assemble`` raising ``MEMORY_NOT_FOUND`` to force the degrade. WP-011 makes
    the cold-memory path regenerate the summary ON DEMAND from the durable
    messages — so a thread with messages but no memory now yields the RICH brief
    (covered by ``test_cold_memory_live_resume.py``). The remaining
    unrecoverable case is a thread with **NO messages AND no memory**: there is
    nothing to regenerate from, so the rich fragment is correctly absent and the
    brief degrades to the default — never an exception into the spawn. This store
    seeds only ``put_thread`` (no ``append_message``, no ``put_memory``), so it
    is exactly that case."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))

    repo_root = tmp_path / "worktree"
    repo_root.mkdir()
    _write_working_set(repo_root)

    # A store with a thread but NO messages AND no memory → nothing to
    # regenerate on demand. The live wiring must isolate that and degrade.
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

    mgr = _manager(store, str(repo_root))
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


def test_live_spawn_isolates_sidecar_write_failure(tmp_path: Path, monkeypatch) -> None:
    """A sidecar WRITE failure during composition must NEVER crash the spawn
    (isolation): the assembled payload is ready but writing it into the brief
    fails — the spawn still proceeds (the rich fragment simply does not land)."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))

    repo_root = tmp_path / "worktree"
    repo_root.mkdir()
    _write_working_set(repo_root)
    _write_brain_entity(repo_root)

    # Make the change dir a FILE so the sidecar parent.mkdir / write_text fails.
    change_parent = home / ".sulis" / "changes"
    change_parent.mkdir(parents=True)
    (change_parent / _CHANGE_ID).write_text("not a dir", encoding="utf-8")

    store = _seed_store(tmp_path / "threads")
    mgr = _manager(store, str(repo_root))
    try:
        spec = SessionSpec(
            provider="claude", cwd=str(repo_root), brief_change_id=_CHANGE_ID
        )
        # The spawn must not raise even though the brief write fails.
        session = mgr.open(_KEY, spec)
        assert session is not None
    finally:
        mgr.shutdown()


def test_live_respawn_keeps_exactly_one_fragment(tmp_path: Path, monkeypatch) -> None:
    """A re-spawn (restart-on-death / login-expiry resume — the path this WP
    serves) re-composes the brief IDEMPOTENTLY: the resumed-context fragment
    appears exactly ONCE, not stacked N times. Drives the real ``_respawn``
    seam, the one a first-``open``-only test never exercises."""
    from _session_manager.durable_sink import BRIEF_FRAGMENT_HEADER

    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))

    repo_root = tmp_path / "worktree"
    repo_root.mkdir()
    _write_working_set(repo_root)
    _write_brain_entity(repo_root)

    store = _seed_store(tmp_path / "threads")
    mgr = _manager(store, str(repo_root))
    try:
        spec = SessionSpec(
            provider="claude", cwd=str(repo_root), brief_change_id=_CHANGE_ID
        )
        session = mgr.open(_KEY, spec)

        # Re-spawn twice (the recovery/resume path re-runs _compose_resume_brief).
        mgr._respawn(session)  # noqa: SLF001 — drive the restart seam directly
        mgr._respawn(session)  # noqa: SLF001

        brief = mgr._test_adapter.recorded_brief  # type: ignore[attr-defined]
        assert brief is not None
        # Idempotent: exactly ONE resumed-context block, no matter how many
        # respawns — the fragment is replaced, never stacked.
        assert brief.count(BRIEF_FRAGMENT_HEADER) == 1, (
            f"expected exactly one resumed-context fragment after respawns, got "
            f"{brief.count(BRIEF_FRAGMENT_HEADER)}"
        )
        # The rich content + the default binding both survive the re-compose.
        assert _WORKING_SET_SENTINEL in brief
        assert "Your working directory is the change worktree" in brief
    finally:
        mgr.shutdown()


def test_compose_skips_and_writes_nothing_for_non_ulid_change_id(
    tmp_path: Path, monkeypatch
) -> None:
    """The manager's compose path must NOT join a non-ULID ``brief_change_id``
    into the sidecar filesystem path (defence-in-depth, path-traversal): the
    compose is skipped (fails closed), writing NOTHING, and never raises.
    Mirrors the pty adapter's read-path ULID gate on the manager's write path.

    Drives ``_compose_resume_brief`` directly (the seam this WP added), not full
    ``open`` — a non-ULID id is also refused downstream by the durable store's
    own ``INVALID_ID`` guard, so driving ``open`` would exercise that unrelated
    layer rather than the compose gate under test."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))

    repo_root = tmp_path / "worktree"
    repo_root.mkdir()
    _write_working_set(repo_root)

    store = _seed_store(tmp_path / "threads")
    mgr = SessionManager(
        {"claude": _BriefRecordingPtyAdapter()},
        start_maintenance=False,
        thread_store_factory=lambda change_id: store,
    )
    try:
        # A traversal-shaped change id that passes SessionSpec.__post_init__ (no
        # leading '-', no control chars) but is not a valid ULID.
        bad_change_id = "a-..-..-escape"
        spec = SessionSpec(
            provider="claude", cwd=str(repo_root), brief_change_id=bad_change_id
        )
        # Drive the compose seam directly — it must skip (fail closed), not raise.
        mgr._compose_resume_brief(spec)  # noqa: SLF001
        # No sidecar dir/file was created anywhere under ~/.sulis/changes for the
        # bad id — the gate fired before any path join + mkdir/write.
        changes_dir = home / ".sulis" / "changes"
        assert not changes_dir.exists() or not any(changes_dir.iterdir()), (
            "the compose wrote a sidecar for a non-ULID change id"
        )
    finally:
        mgr.shutdown()
