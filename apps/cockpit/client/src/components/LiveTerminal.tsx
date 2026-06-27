// WP-008 — <LiveTerminal /> — the xterm.js raw-terminal view (the sanctioned
// terminal emulator, CP) mounted as the cockpit's third Terminal tab.
//
// It consumes ONLY the WP-007 TerminalBridge port for transport (WPF-02 — no
// raw socket in the component): it opens a pty-mode session, attaches (rendering
// the scrollback snapshot first, then live bytes — never a blank pane,
// acceptance #1), feeds the founder's keystrokes back (the two-way feed,
// acceptance #2), reports terminal size, and detaches on unmount — LEAVING THE
// SESSION RUNNING (§2.12.3, acceptance #3).
//
// xterm.js internals stay INSIDE this component (Blue): the rest of the cockpit
// sees a React component, never a Terminal instance. The component is decoupled
// from the concrete terminal via the `TerminalSink`/`TerminalFactory` seam so
// it is testable under jsdom (which has no canvas) — the default factory wraps
// the real xterm.js Terminal; tests inject a fake sink.
//
// Builds to the signed visual contract (WP-VISUAL): tokenised chrome
// (connection badge + scrollback meter + reconnect + type-here affordance) and
// the three required states (connecting / disconnected / no-terminal-here,
// WPF-05). The terminal CONTENT area renders its own ANSI palette — the single
// documented token exception (WP-VISUAL §5.1).
//
// References: WP-008 Contract + Definition of Done; contract §2.12–§2.13;
// ADR-003; WP-VISUAL.

import { useEffect, useRef, useState } from "react";

import styles from "./LiveTerminal.module.css";
import { createTerminalBridge } from "../terminal/terminalBridge";
// Type-only import of the port (erased at build — no Node-side socket adapter
// is pulled into the client bundle; the component depends on the INTERFACE).
import type {
  AttachResult,
  TerminalBridge,
  TerminalError,
} from "../../../server/ports/TerminalBridge";

/**
 * The minimal terminal surface the component drives. It abstracts xterm.js's
 * `Terminal` so the component is testable without a real canvas (jsdom) and so
 * xterm.js internals never leak past this module. The default factory wraps
 * the real xterm.js Terminal; tests inject a fake.
 */
export interface TerminalSink {
  /** Mount the terminal into the host element. */
  open(parent: HTMLElement): void;
  /** Write raw PTY bytes (the snapshot, then live) to the screen. */
  write(data: Uint8Array): void;
  /** Register the keystroke callback (the founder typing → bridge.feed). */
  onData(handler: (data: string) => void): void;
  /** Register the resize callback (xterm geometry → bridge.resize). */
  onResize(handler: (size: { rows: number; cols: number }) => void): void;
  /** Tear the terminal down (local cleanup; detach is the session signal). */
  dispose(): void;
}

/** Produces a {@link TerminalSink}. Swappable for testability. */
export type TerminalFactory = () => TerminalSink;

interface Props {
  changeId: string;
  /** The transport port. Defaults to the real client bridge; tests inject a
   *  fake (WPF-03 mock-first). */
  bridge?: TerminalBridge;
  /** The terminal sink factory. Defaults to the real xterm.js Terminal; tests
   *  inject a fake sink (jsdom has no canvas). */
  terminalFactory?: TerminalFactory;
}

/** Which WPF-05 state the surface is in. */
type ViewState =
  | { kind: "connecting" }
  | { kind: "live" }
  | { kind: "disconnected" }
  // CH-R5EE44 Fix 2 — the connection could NOT be reached at all (the WS upgrade
  // was rejected / the cockpit server is down / the socket dropped before a
  // single live byte). Distinct from `disconnected` (a drop AFTER going live,
  // where the session is still running): unreachable means there is no session to
  // catch up to, so the copy names the recovery (start the cockpit server).
  | { kind: "unreachable" }
  | { kind: "no-terminal" }
  | { kind: "error"; error: TerminalError };

/** The default xterm.js-backed sink (the production path). Lazily imports
 *  xterm so the heavy emulator only loads when the Terminal tab mounts.
 *
 *  Exported (not module-private) so the fit-addon wiring — loadAddon(fitAddon),
 *  fit-on-open, the ResizeObserver re-fit, dispose teardown — is unit-tested
 *  against mocked xterm (LiveTerminal.fit.test.ts, CH-01KTMB). That wiring
 *  shipped missing once and is invisible to the component tests, which inject a
 *  fake sink; this export is the seam that makes it regression-testable. */
export async function createXtermSink(): Promise<TerminalSink> {
  const { Terminal } = await import("@xterm/xterm");
  // The fit addon sizes the terminal's cols×rows to its container (and re-sizes
  // on container resize) — without it xterm renders at a fixed default width
  // (~80 cols, about half the panel) and never adapts to the window.
  const { FitAddon } = await import("@xterm/addon-fit");
  // The xterm stylesheet (the terminal content's own palette — the documented
  // token exception, WP-VISUAL §5.1).
  await import("@xterm/xterm/css/xterm.css");
  const term = new Terminal({
    convertEol: false,
    cursorBlink: true,
    fontFamily:
      "'JetBrains Mono', 'SF Mono', Monaco, Inconsolata, 'Fira Mono', monospace",
    fontSize: 13,
  });
  const fitAddon = new FitAddon();
  term.loadAddon(fitAddon);
  let resizeObserver: ResizeObserver | undefined;
  // fit() reads the container's measured size, so it can throw if the container
  // isn't laid out yet — guard it.
  const safeFit = () => {
    try {
      fitAddon.fit();
    } catch {
      /* container not measurable yet — a later resize tick will fit */
    }
  };
  return {
    open: (parent) => {
      term.open(parent);
      // Fit once the browser has laid the container out, then keep it fitted to
      // the container's size. fit() updates cols/rows → term.onResize fires →
      // the geometry is forwarded to the backend (§2.13.3), already wired below.
      requestAnimationFrame(safeFit);
      resizeObserver = new ResizeObserver(() => safeFit());
      resizeObserver.observe(parent);
    },
    write: (data) => term.write(data),
    onData: (handler) => {
      term.onData(handler);
    },
    onResize: (handler) => {
      term.onResize(({ rows, cols }) => handler({ rows, cols }));
    },
    dispose: () => {
      resizeObserver?.disconnect();
      term.dispose();
    },
  };
}

/** The default factory bridges the async xterm import behind the sync sink
 *  surface: it returns a sink that buffers writes until xterm resolves. */
function defaultTerminalFactory(): TerminalSink {
  let real: TerminalSink | undefined;
  let pendingParent: HTMLElement | undefined;
  const pendingWrites: Uint8Array[] = [];
  let dataHandler: ((data: string) => void) | undefined;
  let resizeHandler:
    | ((size: { rows: number; cols: number }) => void)
    | undefined;
  let disposed = false;

  void createXtermSink().then((sink) => {
    if (disposed) {
      sink.dispose();
      return;
    }
    real = sink;
    if (pendingParent) sink.open(pendingParent);
    if (dataHandler) sink.onData(dataHandler);
    if (resizeHandler) sink.onResize(resizeHandler);
    for (const w of pendingWrites) sink.write(w);
    pendingWrites.length = 0;
  });

  return {
    open: (parent) => {
      if (real) real.open(parent);
      else pendingParent = parent;
    },
    write: (data) => {
      if (real) real.write(data);
      else pendingWrites.push(data);
    },
    onData: (handler) => {
      dataHandler = handler;
      if (real) real.onData(handler);
    },
    onResize: (handler) => {
      resizeHandler = handler;
      if (real) real.onResize(handler);
    },
    dispose: () => {
      disposed = true;
      real?.dispose();
    },
  };
}

/** Map a §2.15 error code onto the WPF-05 state it renders.
 *
 *  `wasLive` is whether the attach stream had already delivered a live byte
 *  before this error (CH-R5EE44 Fix 2): a `SOCKET_CLOSED` BEFORE going live is a
 *  connection that could never be reached (origin-rejected / server down) — the
 *  silent-failure root cause — so it renders the actionable `unreachable` state.
 *  The SAME code AFTER going live is a recoverable drop of a still-running
 *  session, which keeps the `disconnected` "reconnect to catch up" copy. */
function stateForError(error: TerminalError, wasLive: boolean): ViewState {
  switch (error.code) {
    case "NOT_PTY_SESSION":
      return { kind: "no-terminal" };
    case "SOCKET_CLOSED":
      return wasLive ? { kind: "disconnected" } : { kind: "unreachable" };
    default:
      // NO_SESSION / PTY_OPEN_FAILED — surface as a recoverable disconnect
      // (the session may be gone or failed to spawn; reconnect re-opens).
      return { kind: "error", error };
  }
}

export function LiveTerminal({ changeId, bridge, terminalFactory }: Props) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const [state, setState] = useState<ViewState>({ kind: "connecting" });
  // Bumping this re-runs the attach effect (the Reconnect affordance).
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const activeBridge = bridge ?? createTerminalBridge();
    const factory = terminalFactory ?? defaultTerminalFactory;
    const host = hostRef.current;
    let cancelled = false;

    const sink = factory();
    if (host) sink.open(host);

    // The two-way feed: founder keystrokes → bridge.feed (verbatim bytes,
    // §2.12.4). Fire-and-forget; the ack is the written count. feed is
    // best-effort and "no-op-safe after detach/close" (§2.12.2), so a
    // rejection (e.g. the session died) is swallowed deliberately rather than
    // surfaced per-keystroke — but we catch it so it never becomes an
    // unhandled promise rejection.
    sink.onData((data) => {
      activeBridge.feed(changeId, new TextEncoder().encode(data)).catch(() => {
        /* best-effort feed; the disconnect is surfaced by the attach stream */
      });
    });
    // Geometry → bridge.resize so TUIs render correctly (§2.13.3). Same
    // best-effort discipline as feed.
    sink.onResize(({ rows, cols }) => {
      activeBridge.resize(changeId, rows, cols).catch(() => {
        /* best-effort resize */
      });
    });

    async function run() {
      // CH-R5EE44 Fix 2 — track whether a live byte has landed, so a drop is
      // classified as `unreachable` (never reached) vs `disconnected` (dropped
      // after going live, session still running).
      let wasLive = false;
      try {
        await activeBridge.open(changeId);
        // The component-facing attach surface yields typed results (errors are
        // values, never thrown). attachResults lives on the concrete client;
        // narrow to it (the interface's `attach` throws — we want values).
        const results = (
          activeBridge as TerminalBridge & {
            attachResults?: (id: string) => AsyncIterable<AttachResult>;
          }
        ).attachResults;
        const stream = results
          ? results.call(activeBridge, changeId)
          : toResults(activeBridge.attach(changeId));

        for await (const result of stream) {
          if (cancelled) return;
          if (result.ok) {
            wasLive = true;
            setState({ kind: "live" });
            sink.write(result.bytes);
          } else {
            setState(stateForError(result.error, wasLive));
            return;
          }
        }
        // The stream ended cleanly. If it never went live, the session could not
        // be reached (unreachable); otherwise the running session simply closed
        // its end (disconnected — reconnect to catch up).
        if (!cancelled) {
          setState(wasLive ? { kind: "disconnected" } : { kind: "unreachable" });
        }
      } catch (e) {
        if (cancelled) return;
        // A throwing transport: `open()`/attach rejected. A typed
        // TerminalBridgeError carries its §2.15 code — route it through the SAME
        // mapping the stream errors use (so a SOCKET_CLOSED-before-live → the
        // `unreachable` WS-connect-failure state; a PTY_OPEN_FAILED stays the
        // recoverable error). An UNtyped throw before going live is a raw
        // connection failure (server down / refused) → unreachable; after going
        // live it is a dropped connection of a still-running session (§2.12.3).
        const terminalError =
          e && typeof e === "object" && "terminalError" in e
            ? (e as { terminalError: TerminalError }).terminalError
            : undefined;
        if (terminalError) {
          setState(stateForError(terminalError, wasLive));
        } else {
          setState(wasLive ? { kind: "disconnected" } : { kind: "unreachable" });
        }
      }
    }

    void run();

    return () => {
      cancelled = true;
      // Detach LEAVES THE SESSION RUNNING (§2.12.3). Local terminal teardown
      // is separate from the session signal. Best-effort + caught so a detach
      // rejection on an already-closed session never escapes as an unhandled
      // rejection during unmount.
      activeBridge.detach(changeId).catch(() => {
        /* best-effort detach; the session lifecycle is server-owned */
      });
      sink.dispose();
    };
    // Deps are deliberately [changeId, attempt]: changeId re-attaches a new
    // session; attempt is the Reconnect trigger. `bridge`/`terminalFactory`
    // are stable injection seams (defaulted once) — re-running on their
    // identity is neither needed nor desired.
  }, [changeId, attempt]);

  const connected = state.kind === "live";
  const badgeClass = connected
    ? styles.badgeConnected
    : state.kind === "connecting"
      ? styles.badgeConnecting
      : styles.badgeDisconnected;
  const badgeLabel = connected
    ? "connected"
    : state.kind === "connecting"
      ? "connecting"
      : "disconnected";

  return (
    <div className={styles.card} data-testid="live-terminal">
      <div className={styles.toolbar}>
        <span className={styles.status}>
          <span
            className={`${styles.badge} ${badgeClass}`}
            aria-label={`connection status: ${badgeLabel}`}
          >
            {badgeLabel}
          </span>
          <span className={styles.meta}>terminal · {changeId}</span>
        </span>
        {state.kind !== "live" && state.kind !== "connecting" ? (
          <button
            type="button"
            className={styles.reconnect}
            onClick={() => {
              setState({ kind: "connecting" });
              setAttempt((n) => n + 1);
            }}
          >
            Reconnect
          </button>
        ) : null}
      </div>

      {/* The xterm host is ALWAYS mounted (so the ref is stable + bytes have a
          home), but state panels overlay it when not live. */}
      <div
        ref={hostRef}
        className={styles.viewport}
        role="region"
        aria-label="Live terminal output"
        tabIndex={0}
        hidden={state.kind !== "live"}
      />

      {state.kind === "connecting" ? (
        <div className={styles.state} data-testid="live-terminal-connecting">
          <div className={styles.spinner} aria-hidden="true" />
          <div className={styles.stateTitle}>
            Attaching to the live session…
          </div>
          <p className={styles.stateNote}>
            Loading the terminal scrollback and live output.
          </p>
        </div>
      ) : null}

      {state.kind === "disconnected" || state.kind === "error" ? (
        <div className={styles.state} data-testid="live-terminal-disconnected">
          <div className={styles.stateTitle}>Lost the live connection.</div>
          <p className={styles.stateNote}>
            The session is still running — reconnect to catch up.
          </p>
        </div>
      ) : null}

      {/* CH-R5EE44 Fix 2 — the WS-connect-failure state. The session could not be
          reached at all (the /terminal socket was rejected or the cockpit server
          is down), so instead of an empty terminal (the silent failure) we name
          what happened and the concrete recovery step. */}
      {state.kind === "unreachable" ? (
        <div className={styles.state} data-testid="live-terminal-unreachable">
          <div className={styles.stateTitle}>Can&rsquo;t reach the session.</div>
          <p className={styles.stateNote}>
            The live terminal connection was refused. Is the cockpit server
            running? Start it with <kbd>npm run dev</kbd>, then reconnect.
          </p>
        </div>
      ) : null}

      {state.kind === "no-terminal" ? (
        <div className={styles.state} data-testid="live-terminal-no-terminal">
          <div className={styles.stateTitle}>No terminal here.</div>
          <p className={styles.stateNote}>
            This change isn&rsquo;t running an interactive terminal — a
            chat-only session has no terminal to attach to.
          </p>
        </div>
      ) : null}

      {state.kind === "live" ? (
        <div className={styles.inputHint}>
          <span>
            This terminal is live — your keystrokes go straight to the session.
          </span>
          <span>
            Try: <kbd>ls</kbd> <kbd>↵</kbd>
          </span>
        </div>
      ) : null}
    </div>
  );
}

/** Adapt the throwing byte-stream `attach` into typed results, for a bridge
 *  that only exposes the throwing variant. Bytes become ok results; a throw
 *  becomes a disconnect-shaped SOCKET_CLOSED result value. */
async function* toResults(
  bytes: AsyncIterable<Uint8Array>,
): AsyncIterable<AttachResult> {
  try {
    for await (const chunk of bytes) {
      yield { ok: true, bytes: chunk, phase: "live" };
    }
  } catch (e) {
    const error =
      e && typeof e === "object" && "terminalError" in e
        ? (e as { terminalError: TerminalError }).terminalError
        : {
            category: "protocol" as const,
            code: "SOCKET_CLOSED" as const,
            message: "attach stream dropped",
          };
    yield { ok: false, error };
  }
}
