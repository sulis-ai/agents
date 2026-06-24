"""``_session_manager.thread_store_local`` — the durable LOCAL ``ThreadStore``
adapter (CH-GJ9KQR WP-002).

The on-disk, append-only implementation of the ``ThreadStore`` port pinned by
the contract (WP-001, :mod:`_session_manager.thread_contract`). It is the
**local-first** binding (ADR-002 hybrid): a library call against the founder's
filesystem, ``platform_id="local"``, no network. The hosted communication-
service REST adapter is the future second adapter behind the *same* port — only
the binding moves, never the contract.

**What it stores** (under the CF-11 pinned store root
``~/.sulis/changes/{change_id}/threads/``, or an explicit ``root`` for tests):

- ``{thread_id}.thread.json``     — the ``Thread`` record (one JSON object).
- ``{thread_id}.memory.json``     — the latest ``ThreadMemory`` checkpoint.
- ``{thread_id}.messages.jsonl``  — the append-only message log, one
  ``ThreadMessage`` per line, offset-ordered (the log convention, TDD §3.3).

**Invariants** (TDD §4 — the same ones the in-memory stub enforces; this
adapter runs the SAME shared contract test, MEA-09):

- *Append-only*: a duplicate message id (``DUPLICATE_MESSAGE``) or an
  out-of-order append (``OUT_OF_ORDER_WRITE``) is a deterministic refusal
  (:class:`ExpectedError`). The guard validates **before any byte is written**,
  so a rejected append leaves the log file byte-for-byte unchanged.
- *Monotonic memory version*: a stale/equal ``ThreadMemory.version`` is refused
  (``STALE_MEMORY_VERSION``); the stored checkpoint is left intact.

**Redaction-on-write** (TDD §4, security lens): the durable store is a *new*
content-persistence surface, so the outbound-scrub posture applies *before
bytes land*. EVERY persisted string surface is scrubbed through the shared
secret catalogue (:func:`_secret_patterns.find_secrets`, the same seam the
outbound path uses), so a token-shaped secret never reaches disk:

- a ``Thread``'s ``topic`` / ``activity_summary``;
- a ``ThreadMessage``'s ``content`` (both standalone appends and the copies
  embedded in a memory checkpoint);
- an ``ExplorationJournalEntry``'s ``content`` and its ``metadata``;
- the open-ended ``ThreadMemoryContent.participant_context`` (scrubbed
  recursively — the contract notes it carries "provider identity").

Redaction itself is two-pass (span + exact-value sweep) so a secret cannot
survive even when a detector reports an *advisory* (best-effort) offset — see
:func:`_scrub`.

**Dependency direction (MEA-01 / WPB-01).** This module imports only the
provider-neutral contract types + the shared secret catalogue + the stdlib. It
has no provider, subprocess, or web import. It is the *one* place in the change
that touches the filesystem behind the port.
"""

from __future__ import annotations

import builtins
import dataclasses
import json
from pathlib import Path
from typing import Any

from _secret_patterns import find_secrets

from . import thread_contract as tc
from .thread_contract import (
    DUPLICATE_MESSAGE,
    MEMORY_NOT_FOUND,
    OUT_OF_ORDER_WRITE,
    STALE_MEMORY_VERSION,
    THREAD_NOT_FOUND,
    ExpectedError,
    Thread,
    ThreadMemory,
    ThreadMessage,
    memory_record_filename,
    messages_record_filename,
    store_root_for_change,
    thread_record_filename,
    validate_store_id,
)

# The placeholder a scrubbed secret span is replaced with. Stable + obvious in
# a stored record so a human reading the log sees redaction happened (mirrors
# the anonymiser's "[redacted]" posture without coupling to its markers).
_REDACTION = "[redacted-secret]"


def _scrub(text: str) -> str:
    """Replace every detected secret in ``text`` with the redaction
    placeholder, leaving the surrounding content intact.

    Uses the shared outbound-scrub catalogue (:func:`find_secrets`). Redaction
    is done in two complementary passes so the secret can never survive on
    disk, regardless of how a detector reported its location:

    1. **Span pass.** Different detectors may report DIFFERENT, partly-
       overlapping spans for the same secret (e.g. one matches
       ``sk_live_…UVWX`` while another matches the longer
       ``sk_live_…UVWX0123456789``). The spans are merged into maximal
       intervals, then each interval is replaced once — so the redaction
       covers the UNION of every detector's view of the secret.
    2. **Value pass (belt-and-braces).** The detect-secrets layer of
       ``find_secrets`` derives offsets best-effort (its own docstring calls
       them *advisory* — it locates the value with ``str.find`` on the first
       occurrence). A span pass alone therefore trusts an offset that may
       point at the wrong occurrence, leaving the real secret tail on disk.
       So after the span pass, any ``SecretHit.value`` STILL present verbatim
       in the result is replaced by exact string match. This guarantees no
       detected secret value reaches the persisted bytes even when its
       reported offset was wrong.
    """
    if not text:
        return text
    hits = find_secrets(text)
    if not hits:
        return text
    # Pass 1 — merge overlapping/adjacent spans into maximal intervals (hits
    # arrive sorted by (start, end); a later hit that starts at or before the
    # current interval's end extends it to the farther of the two ends).
    merged: list[list[int]] = []
    for hit in hits:
        if merged and hit.start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], hit.end)
        else:
            merged.append([hit.start, hit.end])
    out: list[str] = []
    cursor = 0
    for start, end in merged:
        out.append(text[cursor:start])
        out.append(_REDACTION)
        cursor = end
    out.append(text[cursor:])
    scrubbed = "".join(out)
    # Pass 2 — exact-value sweep for any hit whose advisory offset missed it.
    # Longest values first so a value that is a substring of another does not
    # leave a fragment behind.
    for value in sorted({h.value for h in hits if h.value}, key=len, reverse=True):
        if value in scrubbed:
            scrubbed = scrubbed.replace(value, _REDACTION)
    return scrubbed


def _scrub_value(value: Any) -> Any:
    """Recursively scrub every string inside an arbitrary JSON-shaped value.

    Used for the open-ended ``participant_context`` dict and an exploration-
    journal entry's ``metadata`` — both can carry free-form string content
    (the contract docstring notes ``participant_context`` holds "provider
    identity", exactly the kind of value that carries a token). Walks dicts +
    lists; scrubs str leaves; leaves non-string scalars (int/bool/None)
    untouched. Dict KEYS are scrubbed too (defense-in-depth: an open-ended,
    agent-populated dict could carry a secret-shaped string as a key).
    """
    if isinstance(value, str):
        return _scrub(value)
    if isinstance(value, dict):
        return {_scrub_value(k): _scrub_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub_value(v) for v in value]
    return value


def _scrub_message(message: ThreadMessage) -> ThreadMessage:
    """Return a copy of ``message`` with its content scrubbed (redaction-on-
    write). The message is frozen, so we build a new value."""
    scrubbed = _scrub(message.content)
    if scrubbed == message.content:
        return message
    return dataclasses.replace(message, content=scrubbed)


def _scrub_thread(thread: Thread) -> Thread:
    """Return a copy of ``thread`` with its free-text fields scrubbed.

    ``topic`` and ``activity_summary`` are founder/agent-authored strings
    persisted verbatim to ``{thread_id}.thread.json`` — the same new content-
    persistence surface as the message log, so they inherit the redaction-on-
    write posture (a token pasted into a topic must not land in cleartext)."""
    return dataclasses.replace(
        thread,
        topic=_scrub(thread.topic) if thread.topic is not None else None,
        activity_summary=(
            _scrub(thread.activity_summary)
            if thread.activity_summary is not None
            else None
        ),
    )


def _scrub_memory(memory: ThreadMemory) -> ThreadMemory:
    """Return a copy of ``memory`` with every persisted string scrubbed: the
    embedded message contents, the exploration-journal entry contents (and
    their metadata), and the open-ended ``participant_context`` values."""
    content = memory.content
    scrubbed_messages = [_scrub_message(m) for m in content.messages]
    scrubbed_journal = [
        dataclasses.replace(
            e,
            content=_scrub(e.content),
            metadata=_scrub_value(e.metadata) if e.metadata is not None else None,
        )
        for e in content.exploration_journal
    ]
    new_content = dataclasses.replace(
        content,
        messages=scrubbed_messages,
        exploration_journal=scrubbed_journal,
        participant_context=_scrub_value(content.participant_context),
    )
    return dataclasses.replace(memory, content=new_content)


class LocalThreadStore:
    """Durable, append-only, local ``ThreadStore`` adapter (conforms to the
    runtime-checkable ``ThreadStore`` port structurally)."""

    def __init__(self, change_id: str, root: Path | None = None) -> None:
        # ``change_id`` is validated by the convention helper (CF-11) whether or
        # not an explicit root is supplied — so a traversing id is refused even
        # when a test passes its own root.
        validate_store_id(change_id)
        self.change_id = change_id
        self.root: Path = (
            Path(root) if root is not None else store_root_for_change(change_id)
        )

    # ── path helpers (the only place filenames are composed) ──────────────

    def _thread_path(self, thread_id: str) -> Path:
        return self.root / thread_record_filename(thread_id)

    def _memory_path(self, thread_id: str) -> Path:
        return self.root / memory_record_filename(thread_id)

    def _messages_path(self, thread_id: str) -> Path:
        return self.root / messages_record_filename(thread_id)

    def _ensure_root(self) -> None:
        # Created lazily on first write; loopback single-founder OS file perms
        # are the trust boundary (TDD §4 at-rest scope). ``exist_ok`` so a
        # second instance over the same root is a no-op.
        self.root.mkdir(parents=True, exist_ok=True)

    # ── the single IO seam (read/write JSON + the append-only log) ────────

    def _read_json(self, path: Path) -> dict | None:
        try:
            raw = path.read_text(encoding="utf-8")
        except builtins.FileNotFoundError:
            return None
        return json.loads(raw)

    def _write_json(self, path: Path, payload: dict) -> None:
        self._ensure_root()
        # Atomic-ish replace: write a sibling temp file then rename, so a reader
        # never observes a half-written record (the rename is atomic on POSIX).
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)

    def _read_messages(self, thread_id: str) -> list[ThreadMessage]:
        path = self._messages_path(thread_id)
        try:
            raw = path.read_text(encoding="utf-8")
        except builtins.FileNotFoundError:
            return []
        messages: list[ThreadMessage] = []
        for line in raw.splitlines():
            if not line.strip():
                continue
            messages.append(tc.thread_message_from_dict(json.loads(line)))
        return messages

    def _append_message_line(self, thread_id: str, message: ThreadMessage) -> None:
        self._ensure_root()
        # Append-only: open in append mode, write exactly one JSON line. No
        # rewrite of prior lines ever happens (the invariant guard above
        # guarantees we only reach here for a genuinely new, in-order message).
        line = json.dumps(dataclasses.asdict(message), ensure_ascii=False)
        with self._messages_path(thread_id).open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    # ── write surface (session pump's sink) ───────────────────────────────

    def put_thread(self, thread: Thread) -> None:
        """Upsert a Thread record. (Mirrors the in-memory stub's ``put_thread``;
        the session pump creates the thread before appending.) The free-text
        ``topic``/``activity_summary`` are scrubbed before write (redaction-on-
        write applies to every persisted string surface, TDD §4)."""
        scrubbed = _scrub_thread(thread)
        self._write_json(self._thread_path(thread.id), dataclasses.asdict(scrubbed))

    def append_message(self, thread_id: str, message: ThreadMessage) -> None:
        # Validate the append-only invariant against the PERSISTED log before
        # touching any byte — so a rejected append leaves the file unchanged.
        log = self._read_messages(thread_id)
        if any(m.id == message.id for m in log):
            raise ExpectedError(
                DUPLICATE_MESSAGE,
                f"message {message.id!r} already appended to thread "
                f"{thread_id!r}; the log is append-only (no rewrite)",
            )
        if log and message.order <= log[-1].order:
            raise ExpectedError(
                OUT_OF_ORDER_WRITE,
                f"message order {message.order} is not greater than the last "
                f"order {log[-1].order} on thread {thread_id!r}; the log is "
                f"offset-ordered and monotonic",
            )
        # Redaction-on-write: scrub before the bytes land (TDD §4).
        self._append_message_line(thread_id, _scrub_message(message))

    def put_memory(self, thread_id: str, memory: ThreadMemory) -> None:
        existing = self._read_json(self._memory_path(thread_id))
        if existing is not None and memory.version <= existing["version"]:
            raise ExpectedError(
                STALE_MEMORY_VERSION,
                f"memory version {memory.version} for thread {thread_id!r} is "
                f"not greater than the stored version {existing['version']}; "
                f"memory versions are monotonic",
            )
        # Redaction-on-write across the whole checkpoint (TDD §4).
        scrubbed = _scrub_memory(memory)
        self._write_json(self._memory_path(thread_id), dataclasses.asdict(scrubbed))

    # ── read surface (discovery seam) ─────────────────────────────────────

    def get_thread(self, thread_id: str) -> Thread:
        raw = self._read_json(self._thread_path(thread_id))
        if raw is None:
            raise ExpectedError(THREAD_NOT_FOUND, f"no thread {thread_id!r}")
        return Thread(**raw)

    def get_memory(self, thread_id: str) -> ThreadMemory:
        raw = self._read_json(self._memory_path(thread_id))
        if raw is None:
            raise ExpectedError(MEMORY_NOT_FOUND, f"no memory for thread {thread_id!r}")
        return tc.thread_memory_from_dict(raw)

    def get_messages(
        self, thread_id: str, since: int | None = None, limit: int | None = None
    ) -> list[ThreadMessage]:
        log = self._read_messages(thread_id)
        if since is not None:
            log = [m for m in log if m.order >= since]
        if limit is not None:
            log = log[:limit]
        return log
