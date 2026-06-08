// WP-008 — <LiveTerminal /> tests (Vitest + jest-axe).
//
// The component is the xterm.js raw-terminal view (the sanctioned terminal
// emulator, CP) mounted as the cockpit's third Terminal tab. It consumes ONLY
// the WP-007 TerminalBridge port (WPF-02 — no raw socket in the component) and
// builds to the signed visual contract (WP-VISUAL): tokenised chrome + the
// three required states (connecting / disconnected / no-terminal-here).
//
// Testing seam: xterm.js needs a real canvas/DOM measurement that jsdom does
// not provide, so the component accepts an injectable `terminalFactory` that
// yields a minimal terminal sink. Tests inject a fake terminal (capturing
// `write` + `onData` + `onResize`) AND a fake TerminalBridge — so the wiring
// (attach→write, onData→feed, onResize→resize, unmount→detach) is asserted
// against the injected doubles, not against xterm pixels (WPF-03 mock-first).
//
// References: WP-008 Contract + Definition of Done (Red); contract §2.12–§2.13;
// WP-VISUAL (states + token chrome); ADR-003.

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import { axe } from "jest-axe";

import { LiveTerminal } from "./LiveTerminal";
import type { TerminalSink, TerminalFactory } from "./LiveTerminal";
import type {
  AttachResult,
  FeedAck,
  TerminalBridge,
  TerminalError,
  TerminalOpenResult,
} from "../../../server/ports/TerminalBridge";

const CHANGE_ID = "chg_01KTGY";

// ── A fake xterm terminal sink ────────────────────────────────────────────
// Captures the bytes written + the registered onData/onResize callbacks so a
// test can simulate the founder typing / resizing without a real terminal.
function makeFakeTerminal() {
  let dataCb: ((data: string) => void) | undefined;
  let resizeCb: ((size: { rows: number; cols: number }) => void) | undefined;
  const writes: Uint8Array[] = [];
  const sink: TerminalSink = {
    open: vi.fn(),
    write: vi.fn((bytes: Uint8Array) => {
      writes.push(bytes);
    }),
    onData: (cb) => {
      dataCb = cb;
    },
    onResize: (cb) => {
      resizeCb = cb;
    },
    dispose: vi.fn(),
  };
  return {
    sink,
    writes,
    typeData: (data: string) => dataCb?.(data),
    emitResize: (rows: number, cols: number) => resizeCb?.({ rows, cols }),
  };
}

// ── A configurable fake TerminalBridge ────────────────────────────────────
// `attachResults` drives what the component renders; `feed`/`detach`/`resize`
// record the two-way feed + lifecycle calls.
interface FakeBridgeOptions {
  /** What attachResults yields. Defaults to one snapshot frame. */
  attachResults?: () => AsyncIterable<AttachResult>;
  /** Make open() reject (e.g. simulate a failed spawn). */
  openError?: TerminalError;
}

function makeFakeBridge(opts: FakeBridgeOptions = {}) {
  const calls = {
    open: [] as string[],
    feed: [] as Uint8Array[],
    resize: [] as { rows: number; cols: number }[],
    detach: [] as string[],
  };

  async function* defaultAttach(): AsyncIterable<AttachResult> {
    yield {
      ok: true,
      bytes: new TextEncoder().encode("$ ls -la\n"),
      phase: "snapshot",
    };
  }

  const bridge: TerminalBridge = {
    open: vi.fn(async (changeId: string): Promise<TerminalOpenResult> => {
      calls.open.push(changeId);
      if (opts.openError) {
        const { TerminalBridgeError } =
          await import("../../../server/ports/TerminalBridge");
        throw new TerminalBridgeError(opts.openError);
      }
      return { key: changeId, ioMode: "pty", viewerCount: 0 };
    }),
    attach: () => {
      throw new Error("component must use attachResults, not attach");
    },
    feed: vi.fn(
      async (_changeId: string, data: Uint8Array): Promise<FeedAck> => {
        calls.feed.push(data);
        return { written: data.length };
      },
    ),
    resize: vi.fn(async (_changeId: string, rows: number, cols: number) => {
      calls.resize.push({ rows, cols });
    }),
    detach: vi.fn(async (changeId: string) => {
      calls.detach.push(changeId);
    }),
    // `attachResults` is the component-facing surface (errors-as-values).
    attachResults: opts.attachResults ?? defaultAttach,
  } as TerminalBridge & {
    attachResults: () => AsyncIterable<AttachResult>;
  };

  return { bridge, calls };
}

function renderTerminal(
  bridge: TerminalBridge,
  fake: ReturnType<typeof makeFakeTerminal>,
) {
  const terminalFactory: TerminalFactory = () => fake.sink;
  return render(
    <LiveTerminal
      changeId={CHANGE_ID}
      bridge={bridge}
      terminalFactory={terminalFactory}
    />,
  );
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("<LiveTerminal />", () => {
  it("renders the scrollback bytes into the terminal (acceptance #1)", async () => {
    const fake = makeFakeTerminal();
    const { bridge } = makeFakeBridge();

    renderTerminal(bridge, fake);

    // The attach snapshot bytes reach Terminal.write — not a blank pane.
    await waitFor(() => expect(fake.writes.length).toBeGreaterThan(0));
    const written = Buffer.from(fake.writes[0]!).toString("utf8");
    expect(written).toContain("ls -la");
  });

  it("emits a feed on xterm input (the two-way feed, acceptance #2)", async () => {
    const fake = makeFakeTerminal();
    const { bridge, calls } = makeFakeBridge();

    renderTerminal(bridge, fake);
    // Wait until attach has begun (so onData is wired).
    await waitFor(() => expect(fake.writes.length).toBeGreaterThan(0));

    await act(async () => {
      fake.typeData("ls\n");
    });

    await waitFor(() => expect(calls.feed.length).toBeGreaterThan(0));
    expect(Buffer.from(calls.feed[0]!).toString("utf8")).toBe("ls\n");
  });

  it("reports size on xterm resize (§2.13.3)", async () => {
    const fake = makeFakeTerminal();
    const { bridge, calls } = makeFakeBridge();

    renderTerminal(bridge, fake);
    await waitFor(() => expect(fake.writes.length).toBeGreaterThan(0));

    await act(async () => {
      fake.emitResize(40, 120);
    });

    await waitFor(() => expect(calls.resize.length).toBeGreaterThan(0));
    expect(calls.resize[0]).toEqual({ rows: 40, cols: 120 });
  });

  it("renders the connecting state before the attach snapshot lands (WPF-05)", async () => {
    const fake = makeFakeTerminal();
    // An attach that never yields — the component stays connecting.
    let release: () => void = () => {};
    const gate = new Promise<void>((r) => {
      release = r;
    });
    const { bridge } = makeFakeBridge({
      attachResults: async function* () {
        await gate;
        return;
      },
    });

    renderTerminal(bridge, fake);

    // Connecting affordance is shown — never a blank pane (acceptance #1).
    expect(await screen.findByTestId("live-terminal-connecting")).toBeVisible();
    release();
  });

  it("renders the disconnected state on SOCKET_CLOSED (session still running)", async () => {
    const fake = makeFakeTerminal();
    const { bridge } = makeFakeBridge({
      attachResults: async function* () {
        yield {
          ok: true,
          bytes: new TextEncoder().encode("hello"),
          phase: "live",
        };
        yield {
          ok: false,
          error: {
            category: "protocol",
            code: "SOCKET_CLOSED",
            message: "attach stream dropped",
          },
        };
      },
    });

    renderTerminal(bridge, fake);

    const panel = await screen.findByTestId("live-terminal-disconnected");
    expect(panel).toBeVisible();
    // The session is still running — a reconnect affordance is offered.
    expect(
      screen.getByRole("button", { name: /reconnect/i }),
    ).toBeInTheDocument();
  });

  it("renders the no-terminal-here state on NOT_PTY_SESSION", async () => {
    const fake = makeFakeTerminal();
    const { bridge } = makeFakeBridge({
      attachResults: async function* () {
        yield {
          ok: false,
          error: {
            category: "expected",
            code: "NOT_PTY_SESSION",
            message: "session is pipe io-mode",
          },
        };
      },
    });

    renderTerminal(bridge, fake);

    const panel = await screen.findByTestId("live-terminal-no-terminal");
    expect(panel).toBeVisible();
    expect(panel.textContent).toMatch(/terminal/i);
  });

  it("detaches on unmount and leaves the session running (acceptance #3)", async () => {
    const fake = makeFakeTerminal();
    const { bridge, calls } = makeFakeBridge();

    const { unmount } = renderTerminal(bridge, fake);
    await waitFor(() => expect(fake.writes.length).toBeGreaterThan(0));

    unmount();

    await waitFor(() => expect(calls.detach).toContain(CHANGE_ID));
    // Disposing the terminal is local cleanup; detach is the session signal.
    expect(fake.sink.dispose).toHaveBeenCalled();
  });

  it("has no WCAG AA violations on the chrome (jest-axe, WPF-06/10)", async () => {
    const fake = makeFakeTerminal();
    const { bridge } = makeFakeBridge();

    const { container } = renderTerminal(bridge, fake);
    await waitFor(() => expect(fake.writes.length).toBeGreaterThan(0));

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("surfaces a generic NO_SESSION error as a recoverable disconnect", async () => {
    const fake = makeFakeTerminal();
    const { bridge } = makeFakeBridge({
      attachResults: async function* () {
        yield {
          ok: false,
          error: {
            category: "expected",
            code: "NO_SESSION",
            message: "no session for key",
          },
        };
      },
    });

    renderTerminal(bridge, fake);
    // NO_SESSION renders the disconnected/reconnectable panel (not a blank pane).
    expect(
      await screen.findByTestId("live-terminal-disconnected"),
    ).toBeVisible();
  });

  it("re-attaches when Reconnect is clicked (the reconnect affordance)", async () => {
    const fake = makeFakeTerminal();
    const { bridge, calls } = makeFakeBridge({
      attachResults: async function* () {
        yield {
          ok: false,
          error: {
            category: "protocol",
            code: "SOCKET_CLOSED",
            message: "dropped",
          },
        };
      },
    });

    renderTerminal(bridge, fake);
    const reconnect = await screen.findByRole("button", { name: /reconnect/i });
    expect(calls.open.length).toBe(1);

    await act(async () => {
      reconnect.click();
    });

    // Reconnect detaches the old viewer and re-opens (a fresh attach attempt).
    await waitFor(() => expect(calls.open.length).toBe(2));
    expect(calls.detach.length).toBeGreaterThan(0);
  });

  it("falls back to the throwing attach() when attachResults is absent", async () => {
    const fake = makeFakeTerminal();
    // A bridge exposing ONLY the throwing byte-stream attach (no attachResults).
    async function* bytes(): AsyncIterable<Uint8Array> {
      yield new TextEncoder().encode("from attach()");
    }
    const bridge: TerminalBridge = {
      open: vi.fn(async () => ({
        key: CHANGE_ID,
        ioMode: "pty" as const,
        viewerCount: 0,
      })),
      attach: () => bytes(),
      feed: vi.fn(async () => ({ written: 0 })),
      resize: vi.fn(async () => {}),
      detach: vi.fn(async () => {}),
    };

    renderTerminal(bridge, fake);
    await waitFor(() => expect(fake.writes.length).toBeGreaterThan(0));
    expect(Buffer.from(fake.writes[0]!).toString("utf8")).toContain(
      "from attach()",
    );
  });

  it("renders the disconnected state when open() rejects (failed spawn)", async () => {
    const fake = makeFakeTerminal();
    const { bridge } = makeFakeBridge({
      openError: {
        category: "internal",
        code: "PTY_OPEN_FAILED",
        message: "os.openpty() failed",
      },
    });

    renderTerminal(bridge, fake);
    // A failed open is a recoverable disconnect, not a blank pane.
    expect(
      await screen.findByTestId("live-terminal-disconnected"),
    ).toBeVisible();
  });

  it("does not throw when a keystroke feed rejects (best-effort, §2.12.2)", async () => {
    const fake = makeFakeTerminal();
    const { bridge } = makeFakeBridge();
    // Make feed reject — a closed PTY swallows the write; the component must
    // not let that escape as an unhandled rejection.
    (bridge.feed as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error("session gone"),
    );

    renderTerminal(bridge, fake);
    await waitFor(() => expect(fake.writes.length).toBeGreaterThan(0));

    let threw = false;
    try {
      await act(async () => {
        fake.typeData("x");
      });
    } catch {
      threw = true;
    }
    expect(threw).toBe(false);
  });
});
