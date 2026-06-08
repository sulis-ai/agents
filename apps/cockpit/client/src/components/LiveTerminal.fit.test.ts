// CH-01KTMB — regression guard for the xterm fit-addon wiring inside
// createXtermSink() (the real, xterm-backed terminal sink).
//
// WHY THIS EXISTS
// The fix "terminal fills its panel" (full-width + full-height + responsive)
// depends on createXtermSink() loading the @xterm/addon-fit FitAddon, fitting
// on open, and re-fitting on container resize via a ResizeObserver. That wiring
// shipped MISSING once and was caught only by the founder eyeballing a live run
// — because the existing LiveTerminal.test.tsx injects a FAKE TerminalSink and
// never exercises the real sink at all. This test pins the exact wiring against
// mocked @xterm/* modules so the fit behaviour can't silently regress again.
//
// It is deliberately a sibling to LiveTerminal.test.tsx, not a merge into it:
// that suite asserts the COMPONENT's transport wiring against a fake sink; this
// suite asserts the SINK's xterm wiring against mocked xterm. Different seam,
// different doubles.
//
// References: change CH-01KTMB brief; LiveTerminal.tsx createXtermSink();
// WP-008 (the sink/factory seam); WP-VISUAL §5.1 (xterm content palette).

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// ── Mock the heavy xterm modules ──────────────────────────────────────────
// A Terminal whose open/loadAddon/onData/onResize/write/dispose are spies, and
// a FitAddon whose fit() is a spy. We hold module-level handles so each test can
// read back the most-recently-constructed instance + its spies.

const fitSpy = vi.fn();

let lastFitAddon: FakeFitAddon | undefined;

class FakeFitAddon {
  fit = fitSpy;
  constructor() {
    lastFitAddon = this;
  }
}

interface FakeTerminalInstance {
  open: ReturnType<typeof vi.fn>;
  loadAddon: ReturnType<typeof vi.fn>;
  onData: ReturnType<typeof vi.fn>;
  onResize: ReturnType<typeof vi.fn>;
  write: ReturnType<typeof vi.fn>;
  dispose: ReturnType<typeof vi.fn>;
}

let lastTerminal: FakeTerminalInstance | undefined;

class FakeTerminal implements FakeTerminalInstance {
  open = vi.fn();
  loadAddon = vi.fn();
  onData = vi.fn();
  onResize = vi.fn();
  write = vi.fn();
  dispose = vi.fn();
  constructor() {
    lastTerminal = this;
  }
}

vi.mock("@xterm/xterm", () => ({ Terminal: FakeTerminal }));
vi.mock("@xterm/addon-fit", () => ({ FitAddon: FakeFitAddon }));
// The xterm stylesheet import is a side-effect-only CSS import — stub to empty.
vi.mock("@xterm/xterm/css/xterm.css", () => ({}));

// ── Stub the jsdom-absent browser globals the sink relies on ───────────────
// ResizeObserver: capture the callback so a test can fire a synthetic resize,
// and capture observe()/disconnect() so the wiring + teardown can be asserted.
let resizeObserverCallback: ResizeObserverCallback | undefined;
const observeSpy = vi.fn();
const disconnectSpy = vi.fn();
const unobserveSpy = vi.fn();

class FakeResizeObserver {
  constructor(cb: ResizeObserverCallback) {
    resizeObserverCallback = cb;
  }
  observe = observeSpy;
  disconnect = disconnectSpy;
  unobserve = unobserveSpy;
}

// requestAnimationFrame: the sink fits inside a rAF tick. Invoke synchronously
// so the test doesn't have to await a frame.
beforeEach(() => {
  resizeObserverCallback = undefined;
  lastTerminal = undefined;
  lastFitAddon = undefined;
  fitSpy.mockClear();
  observeSpy.mockClear();
  disconnectSpy.mockClear();
  unobserveSpy.mockClear();

  vi.stubGlobal("ResizeObserver", FakeResizeObserver);
  vi.stubGlobal("requestAnimationFrame", (cb: FrameRequestCallback): number => {
    cb(0);
    return 0;
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// Import AFTER the mocks are registered. createXtermSink is exported from
// LiveTerminal.tsx specifically so this regression test can reach it.
import { createXtermSink } from "./LiveTerminal";

// Build the real sink and mount it into a fresh host element — the common
// arrange step shared by every assertion below (the sink is only interesting
// once open()ed onto a parent it can fit to).
async function mountSink() {
  const sink = await createXtermSink();
  const parent = document.createElement("div");
  sink.open(parent);
  return { sink, parent };
}

describe("createXtermSink — fit-addon wiring (CH-01KTMB regression guard)", () => {
  it("loads the FitAddon into the terminal", async () => {
    await mountSink();

    expect(lastTerminal).toBeDefined();
    expect(lastFitAddon).toBeDefined();
    // The fit addon is loaded so xterm sizes cols×rows to its container.
    expect(lastTerminal!.loadAddon).toHaveBeenCalledWith(lastFitAddon);
  });

  it("fits the terminal on open (inside requestAnimationFrame)", async () => {
    // Create-then-open explicitly so we can pin that fit() is NOT called until
    // open() runs (the rAF stub fires synchronously inside open()).
    const sink = await createXtermSink();
    const parent = document.createElement("div");
    expect(fitSpy).not.toHaveBeenCalled();

    sink.open(parent);

    expect(lastTerminal!.open).toHaveBeenCalledWith(parent);
    expect(fitSpy).toHaveBeenCalledTimes(1);
  });

  it("observes the parent for resize and re-fits on resize", async () => {
    const { parent } = await mountSink();

    // A ResizeObserver was created and watches the host element.
    expect(resizeObserverCallback).toBeDefined();
    expect(observeSpy).toHaveBeenCalledWith(parent);

    // The fit-on-open already fired once; a container resize re-fits.
    expect(fitSpy).toHaveBeenCalledTimes(1);
    resizeObserverCallback!([], {} as ResizeObserver);
    expect(fitSpy).toHaveBeenCalledTimes(2);
  });

  it("disconnects the observer and disposes the terminal on dispose()", async () => {
    const { sink } = await mountSink();

    sink.dispose();

    expect(disconnectSpy).toHaveBeenCalledTimes(1);
    expect(lastTerminal!.dispose).toHaveBeenCalledTimes(1);
  });
});
