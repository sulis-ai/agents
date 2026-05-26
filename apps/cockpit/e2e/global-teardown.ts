// WP-016 — Playwright global teardown. Removes the seeded temp dirs.
// Default-exports the teardown fn so the config can point `globalTeardown`
// at this file directly.

import { globalTeardown } from "./global-setup";

export default globalTeardown;
