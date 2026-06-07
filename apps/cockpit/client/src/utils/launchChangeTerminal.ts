// WP-009 — launchChangeTerminal: the cockpit-side "open this change's terminal"
// action — the new DEFAULT, replacing the OS-window launcher path
// (_terminal_launcher.py, now a deprecated fallback; see WP-009 removal_plan).
//
// SUBSTITUTE-Strangle (contract §2.13.5; TDD §1.6): "open this change's
// terminal" no longer spawns a separate OS Terminal.app/gnome-terminal window
// running `claude` directly. It opens the change's in-cockpit Terminal view —
// the WP-008 <LiveTerminal/> rendered in the browser — backed by the session
// manager's pty-mode session.
//
// What it does (two steps, navigation is the load-bearing one):
//   1. Navigate to the change's Terminal view: /c/:changeId?view=terminal. That
//      route mounts ThreadView, which seeds its initial ChangeNav view from
//      `?view=` → "terminal", rendering <LiveTerminal/> (WP-008), which on
//      mount calls bridge.open({io_mode:"pty"}) + attach (snapshot→live).
//   2. Warm the pty session via the WP-007 TerminalBridge port's idempotent
//      get-or-spawn open() (contract §2.13.5) so the session is spawning while
//      the route transition + xterm.js lazy-import happen — the terminal is
//      ready (not a cold spawn) by the time the tab mounts. This open() is
//      idempotent with the component's own mount-open: get-or-spawn, not a
//      second spawn.
//
// It consumes ONLY the typed bridge PORT (WPF-02 — no raw socket here) and an
// injected navigate function (WPF-03 — mock-first; the caller passes
// react-router's navigate or useNavigate's result), so it is unit-testable
// with no router and no live socket. The warm-open is best-effort: a failure
// MUST NOT block the navigation — the component's mount-open get-or-spawns the
// session regardless, and surfaces its own connecting/disconnected/no-terminal
// states (WP-008 WPF-05). Warming is an optimisation, not a precondition.
//
// References: WP-009 Contract + DoD; contract §2.13.5; WP-007 TerminalBridge;
// WP-008 <LiveTerminal/> + ThreadView/ChangeNav (?view=terminal).

import { createTerminalBridge } from "../terminal/terminalBridge";
import type { TerminalBridge } from "../../../server/ports/TerminalBridge";

/** The route + query the change's in-cockpit Terminal view lives at. App routes
 *  /c/:changeId → ThreadView; ThreadView seeds its initial view from the
 *  optional `?view=` param, so `?view=terminal` lands directly on the WP-008
 *  <LiveTerminal/> view inside the change's ChangeNav workspace. */
export function changeTerminalPath(changeId: string): string {
  return `/c/${changeId}?view=terminal`;
}

/** Dependencies for {@link launchChangeTerminal}. Injected for testability
 *  (WPF-03 mock-first) — no router or live socket required to unit-test. */
export interface LaunchChangeTerminalDeps {
  /** Navigate the SPA to a path (react-router's navigate / useNavigate result). */
  navigate: (to: string) => void;
  /** The terminal transport port. Defaults to the real client bridge; tests
   *  inject a fake (WPF-03). Omit to use the production bridge. */
  bridge?: TerminalBridge;
}

/**
 * Open a change's terminal in the cockpit: navigate to its Terminal view (which
 * mounts <LiveTerminal/>) and warm its pty session via the bridge's idempotent
 * get-or-spawn open(). The new default "open this change's terminal" — the
 * cockpit-rendered path that strangles the OS-window launcher (WP-009).
 *
 * Resolves once navigation has been issued and the warm-open has settled
 * (success OR swallowed failure). Never rejects on a warm-open failure: the
 * navigation is the load-bearing step and the tab mount get-or-spawns the
 * session regardless (the component owns the connection states).
 */
export async function launchChangeTerminal(
  changeId: string,
  deps: LaunchChangeTerminalDeps,
): Promise<void> {
  // 1. Navigation is the load-bearing step — mounting <LiveTerminal/> is what
  //    actually opens the terminal the founder sees. Do it first so a slow
  //    warm-open never delays the founder reaching the tab.
  deps.navigate(changeTerminalPath(changeId));

  // 2. Best-effort warm: get-or-spawn the pty session (contract §2.13.5,
  //    io_mode:"pty" is encoded by the port's open()) so it is spawning during
  //    the route transition. Idempotent with the component's mount-open. A
  //    failure here is swallowed — the component's own mount-open + WPF-05
  //    states are the source of truth for connection status.
  const bridge = deps.bridge ?? createTerminalBridge();
  try {
    await bridge.open(changeId);
  } catch {
    /* best-effort warm-open; the tab mount get-or-spawns + surfaces state */
  }
}
