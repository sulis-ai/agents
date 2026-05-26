// WP-001 — skeleton test for the placeholder server bootstrap.
//
// Per the WP Contract's Red checklist: this test asserts that importing
// the server bootstrap resolves cleanly and that it logs an expected
// banner. The bootstrap deliberately does NOT bind a port (that arrives
// at WP-010); it just proves the module loads and the dev experience
// has a heartbeat.

import { describe, it, expect, vi } from "vitest";

describe("server bootstrap (placeholder)", () => {
  it("imports cleanly and logs the expected banner", async () => {
    const logSpy = vi.spyOn(console, "log").mockImplementation(() => {});
    try {
      const mod = await import("../index");
      expect(mod).toBeDefined();
      expect(logSpy).toHaveBeenCalled();
      const banner = logSpy.mock.calls.map((c) => String(c[0])).join("\n");
      expect(banner).toMatch(/cockpit server up/i);
    } finally {
      logSpy.mockRestore();
    }
  });
});
