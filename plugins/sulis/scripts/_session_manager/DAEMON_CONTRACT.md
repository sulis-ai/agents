# The shared session-manager daemon — presence contract

> **CONTRACT_FIRST seam** (TDD §5, ADR-001). The wire *below* this contract is
> the frozen §2.13 NDJSON protocol (`socket_server.py`). What this document
> defines is the **daemon-presence** contract: where the daemon lives, how a
> caller decides it is alive, how it is started on demand, and the singleton
> rule that guarantees exactly one daemon per user. One contract, two language
> bindings: the Python `daemon_client.py` (this WP, the desktop launcher's
> caller) and the Node `ensureDaemon` (WP-006, the cockpit's caller).

This is a **schema/behaviour contract**, transport-agnostic over the existing
AF_UNIX NDJSON binding. It is the producer/consumer agreement both views build
against in parallel.

## Location

| Resource | Path | Override |
|---|---|---|
| **Socket** (stable, `0o600`, one per user) | `~/.sulis/session-manager.sock` | env `SULIS_SESSION_MANAGER_SOCKET` |
| **Lock** (singleton arbiter) | `~/.sulis/session-manager.lock` | the daemon's `--lock` flag (CI/test isolation) |
| **Pidfile** (identity record) | `~/.sulis/session-manager.pid` | the daemon's `--pidfile` flag (CI/test isolation) |

The **pidfile** is the daemon's durable on-disk identity (HD-001): once it holds
the flock and binds the socket, it writes `{"pid", "start_token",
"cmdline_marker"}` — where `start_token` is the OS process start-time (via `ps
-o lstart=`, portable across macOS + Linux), the value a recycled PID cannot
reproduce. It is removed on a clean shutdown, so the file's presence names a
*live* daemon. This is the identity a later PID-reuse-safe reclaim verifies a
kill target against (both `start_token` **and** `cmdline_marker` must match).
Writing/removing it is **best-effort**: a failed write degrades the reclaim to
the fail-closed path, it never crashes the daemon's boot.

The parent directory (`~/.sulis/`) is created `0o700` if absent. The socket is
chmod `0o600` by the engine's `SocketServer.start` (the established local-IPC
gate; CP-01, matches §2.8.1). The override mirrors the existing
`SULIS_SESSION_MANAGER_HOST` injection seam used by the cockpit + CI.

## Liveness

A daemon is **live** iff **both** hold:

1. an AF_UNIX `connect` to the socket succeeds, **and**
2. a `status` request returns a framed line with `ok: true`.

`connect`-alone is insufficient: a stale socket file can accept a connect and
then hang or error. The `status` round-trip is the definitive probe. The probe
uses a **short connect+read timeout** so a dead or wedged socket fails fast
rather than blocking the caller.

Liveness request (one NDJSON line):

```json
{"id": "live", "method": "status", "params": {}}
```

Liveness response (the daemon's framed reply; `result` is the session snapshot
array — empty when no sessions are open):

```json
{"id": "live", "ok": true, "result": []}
```

**Not-live** observations (all map to "dead", caller spawns):

- the socket file does not exist;
- `connect` raises `ConnectionRefusedError` / `FileNotFoundError`;
- the connect or the `status` read exceeds the timeout;
- the reply is not parseable JSON, or carries `ok: false`.

## Start handshake

The daemon prints exactly one line on stdout once the socket is serving:

```
READY <socket_path>
```

`<socket_path>` is the absolute path the daemon bound. A caller that spawned the
daemon blocks on this line (bounded by `ready_timeout`) before treating the
daemon as available; it then confirms liveness via the `status` probe. (The
engine's host already prints this line — `session_manager_host.py`; the daemon
reuses it.)

## Singleton rule

Exactly **one** process holds an `fcntl.flock(LOCK_EX | LOCK_NB)` on the lock
file for its lifetime, and **the lock-holder is the sole binder** of the socket.
A process that fails to take the lock must **not** unlink or bind the socket; it
confirms the existing socket answers a `status` ping and exits `0`. Losing the
race is **normal, not an error** — the winner is already serving.

`fcntl.flock` is POSIX-stdlib, auto-released on process death (no stale-lock
reconciliation), and is the boring local-singleton convention (ADR-001). It
gates the engine's unconditional `os.unlink(socket)` in `SocketServer.start`, so
only the holder reaches `bind` — closing the clobber race the unguarded engine
would otherwise open.

> The flock is taken by the **daemon** process (WP-003), not by `ensure_daemon`.
> What the *caller* contract (this WP) guarantees is the matching half:
> probe-first, spawn-at-most-once-per-caller, and poll-until-live when another
> caller's daemon wins the race.

### Mid-boot vs wedged (grace-window self-heal, HD-003)

A process that loses the lock race does **not** give up the instant the socket
is dark. It polls up to a **grace window** (`SULIS_DAEMON_WEDGE_GRACE_SECS`,
default `10s` — deliberately longer than the legacy 5s mid-boot poll so a slow-
but-legitimate boot is never mistaken for a wedge) for the holder's socket to
come live:

- **Mid-boot holder** — the socket comes live *within* the window: reuse it,
  print `READY`, exit `0` (the normal race-loser path, just generously
  windowed). The holder is **never** touched.
- **Wedged holder** — the window elapses with the lock still held and no live
  socket: the holder is declared **wedged** and escalated to the PID-reuse-safe
  reclaim. The reclaim reads the holder's identity pidfile, verifies it is
  *still our daemon* (cmdline marker **and** start-token match — fail-closed),
  and only then `SIGTERM`→bounded-wait→`SIGKILL`s it, clears the stale
  pidfile + socket, re-acquires the flock, and boots a fresh daemon through the
  same composition root. A recycled PID whose identity cannot be proven is
  **never** killed — verification failing closed degrades to today's exact
  behaviour: the *"singleton lock held but no live socket … ensure-daemon will
  retry"* line and `exit 1`.

This makes a wedged daemon **self-recover** on the spawn that hits it, rather
than blocking every spawn until the wedged process happens to die. The reclaim
lives entirely in the daemon-presence layer; the frozen engine is unmodified
(ADR-001), and the daemon stays stdlib-only / terminal-only (ADR-003).

## Lifecycle: idle-empty auto-exit

The daemon persists across views and across sessions — it is **not** tied to any
one cockpit or terminal window. Two distinct idle policies apply, and they are
not the same thing:

- **Per-session idle eviction** (the engine's existing maintenance loop, always
  ON) reaps a single *idle session* the daemon still owns.
- **Daemon-level idle-empty auto-exit** (WP-003, ADR-001): when the daemon has
  owned **zero sessions** continuously for `SULIS_DAEMON_IDLE_EXIT_SECS`
  (default `1800`), it self-shuts-down — the same clean teardown a `SIGTERM`
  drives: stop the server, shut the manager down, unlink the socket, release the
  flock, exit `0`. A session appearing resets the empty window (it must be
  *continuous* emptiness).

This bounds a forgotten daemon without coupling its lifetime to any window. It is
**transparent to callers**: a caller that finds the daemon gone simply
`ensure_daemon`s it back — the cold-start path restarts it. No caller-side change
is needed; this note exists so a caller's mental model of "is it still there?"
accounts for a daemon that has self-exited after a long idle-empty stretch.

## Idempotent ensure

`ensure_daemon` is safe to call concurrently from N callers. The guarantees:

- if a live daemon already answers → return the socket, spawn nothing;
- otherwise spawn the daemon **detached** (`start_new_session=True`, so it
  survives the caller's exit), wait for `READY`, confirm liveness, return;
- if N callers race a cold socket, **at most one daemon ends up serving**; a
  caller whose spawn lost the singleton race **polls the socket until it
  answers**, then returns the same path. No caller returns until the socket is
  live, and all callers return the **same** socket path.

### Python binding signature (`daemon_client.py`)

```python
DEFAULT_SOCKET: str   # resolve_default_socket() snapshot at import

def resolve_default_socket() -> str:
    """~/.sulis/session-manager.sock, overridable by SULIS_SESSION_MANAGER_SOCKET."""

def daemon_is_live(socket_path: str = DEFAULT_SOCKET, timeout: float = 1.0) -> bool:
    """True iff connect succeeds AND a `status` request returns ok:true."""

def ensure_daemon(socket_path: str = DEFAULT_SOCKET, *, python: str = "python3",
                  ready_timeout: float = 30.0,
                  spawn_command: list[str] | None = None) -> str:
    """Return socket_path with a live daemon serving it. If none is live, spawn
    the daemon DETACHED (start_new_session=True) and wait for READY. Idempotent
    + race-tolerant: concurrent callers yield at most one daemon; a caller that
    loses the race polls until the winner answers.

    spawn_command is the argv to launch; the literal token "{socket}" in it is
    replaced with socket_path. Default (when None): the real daemon entrypoint
    `python session_manager_daemon.py --socket <path>` (WP-003). Injecting
    spawn_command keeps this binding testable against a fake daemon and keeps
    WP-002 independent of WP-003's entrypoint."""
```

The Node binding (WP-006) implements the same contract over the same wire; the
two bindings are byte-for-byte interchangeable from the daemon's perspective.

## Error categories (CONTRACT_FIRST CF-03)

| Category | This seam's instances | Caller recovery |
|---|---|---|
| **Protocol** | connect refused / socket missing / probe timeout | treat as "dead" → spawn (or poll if a peer is spawning) |
| **Expected** | `status` returns `ok:false` | treat as "dead" → spawn |
| **Internal** | spawn fails to print `READY` within `ready_timeout` | raise `DaemonStartError` — the daemon is broken, not absent |

## Independence (founder directive, MUST)

This contract and its bindings have **zero** dependency on the cockpit chat
relay (`routes/chat.ts`), the chat `SessionBridge`, or the `platform`
communication service. The daemon owns the engine for the **terminal** over the
socket directly. `daemon_client.py` imports only the Python stdlib — no chat, no
`platform`, no engine internals beyond the socket wire it speaks as a client.
