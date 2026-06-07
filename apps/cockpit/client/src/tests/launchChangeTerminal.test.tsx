// WP-009 — launchChangeTerminal: the cockpit-side "open this change's terminal"
// action (the SUBSTITUTE-Strangle of the OS-window launcher by the
// cockpit-rendered <LiveTerminal/> path).
//
// Per WP-009 Contract + contract §2.13.5: from a change, opening its terminal
// navigates to the change's Terminal tab (/c/:changeId?tab=terminal) — which
// mounts <LiveTerminal/> (WP-008) — and warms the pty session via the WP-007
// TerminalBridge port's idempotent get-or-spawn open({io_mode:"pty"}). The
// launcher consumes ONLY the typed bridge port (WPF-02 — no raw socket) and a
// navigate function (WPF-03 — injected, mock-first), so it is unit-testable
// against a fake bridge with no live socket and no router.
//
// References: WP-009 DoD Red (opens_pty_terminal_tab); contract §2.13.5;
// WP-007 TerminalBridge; WP-008 <LiveTerminal/> + ThreadTabs ?tab=terminal.

import { describe, it, expect, vi } from "vitest";

import { launchChangeTerminal } from "../utils/launchChangeTerminal";
import type {
  TerminalBridge,
  TerminalOpenResult,
} from "../../../server/ports/TerminalBridge";

/** A fake bridge that records the open() it receives (WPF-03 mock-first). The
 *  launcher only needs `open` (the idempotent pty get-or-spawn); the other
 *  port methods are the component's concern once the tab mounts. */
function fakeBridge(): {
  bridge: TerminalBridge;
  openCalls: string[];
} {
  const openCalls: string[] = [];
  const bridge: TerminalBridge = {
    open: vi.fn(async (changeId: string): Promise<TerminalOpenResult> => {
      openCalls.push(changeId);
      return { key: changeId, ioMode: "pty", viewerCount: 0 };
    }),
    // eslint-disable-next-line require-yield -- unused in the launcher path
    attach: vi.fn(async function* () {
      /* not exercised by the launcher */
    }),
    feed: vi.fn(async () => ({ written: 0 })),
    resize: vi.fn(async () => {}),
    detach: vi.fn(async () => {}),
  };
  return { bridge, openCalls };
}

describe("launchChangeTerminal (WP-009)", () => {
  it("opens_pty_terminal_tab: navigates to the change's Terminal tab and warms the pty session via the bridge", async () => {
    const { bridge, openCalls } = fakeBridge();
    const navigate = vi.fn();

    await launchChangeTerminal("CH-01KTGY", { navigate, bridge });

    // Navigates to the existing change route's Terminal tab (?tab=terminal) —
    // mounting <LiveTerminal/> (WP-008).
    expect(navigate).toHaveBeenCalledWith("/c/CH-01KTGY?tab=terminal");
    // Warms the pty session (idempotent get-or-spawn, contract §2.13.5) so the
    // terminal is ready when the tab mounts — open({io_mode:"pty"}) via the
    // port (the bridge.open() encodes io_mode:"pty", WP-007).
    expect(openCalls).toEqual(["CH-01KTGY"]);
    expect(bridge.open).toHaveBeenCalledWith("CH-01KTGY");
  });

  it("navigates even when the bridge is not supplied (navigation is the load-bearing step; the tab mount warms the session)", async () => {
    const navigate = vi.fn();

    await launchChangeTerminal("CH-01KZZZ", { navigate });

    expect(navigate).toHaveBeenCalledWith("/c/CH-01KZZZ?tab=terminal");
  });

  it("does not let a warm-open failure block the navigation (the session is get-or-spawned on tab mount regardless)", async () => {
    const navigate = vi.fn();
    const bridge = {
      open: vi.fn(async () => {
        throw new Error("socket not wired yet");
      }),
    } as unknown as TerminalBridge;

    await expect(
      launchChangeTerminal("CH-01KFAIL", { navigate, bridge }),
    ).resolves.toBeUndefined();
    expect(navigate).toHaveBeenCalledWith("/c/CH-01KFAIL?tab=terminal");
  });
});
