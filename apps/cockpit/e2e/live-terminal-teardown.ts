// WP-010 — live-terminal e2e global teardown. Default-exports the teardown fn so
// the config can point `globalTeardown` at this file directly (Playwright runs
// the DEFAULT export of the globalTeardown module — pointing it at
// live-terminal-setup.ts would re-run globalSetup, double-binding the proxy
// port; this dedicated file avoids that).

import { globalTeardown } from "./live-terminal-setup";

export default globalTeardown;
