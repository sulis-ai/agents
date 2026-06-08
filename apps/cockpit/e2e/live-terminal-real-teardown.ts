// WP-007 — REAL-server live-terminal e2e global teardown. Default-exports the
// teardown fn so the config can point `globalTeardown` here directly without
// re-running globalSetup (pointing globalTeardown at live-terminal-real-setup.ts
// would re-run its default export — the pre-seed — on teardown). Mirrors
// live-terminal-teardown.ts.

import { globalTeardown } from "./live-terminal-real-setup";

export default globalTeardown;
