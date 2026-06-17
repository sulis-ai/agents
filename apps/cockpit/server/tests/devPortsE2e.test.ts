// #377 — the e2e ports MUST be distinct from the dev ports so the Playwright
// harness never reuses a developer's running cockpit (which serves the real
// change store, not the seeded fixture). These tests pin that contract.

import { describe, it, expect } from "vitest";
import {
  getServerPort,
  getClientPort,
  getE2eServerPort,
  getE2eClientPort,
  DEFAULT_PORTS,
} from "../../shared/dev-ports";

describe("dev-ports — dedicated e2e ports (#377)", () => {
  it("defaults the e2e server/client ports and they differ from the dev ports", () => {
    const e2eServer = getE2eServerPort({});
    const e2eClient = getE2eClientPort({});
    expect(e2eServer).toBe(DEFAULT_PORTS.e2eServer);
    expect(e2eClient).toBe(DEFAULT_PORTS.e2eClient);
    // The load-bearing invariant: e2e ports are NOT the dev ports, so a running
    // dev cockpit on 5173/5174 can never be reused by the e2e harness.
    expect(e2eServer).not.toBe(getServerPort({}));
    expect(e2eClient).not.toBe(getClientPort({}));
  });

  it("reads COCKPIT_E2E_SERVER_PORT / COCKPIT_E2E_CLIENT_PORT from env when set", () => {
    expect(getE2eServerPort({ COCKPIT_E2E_SERVER_PORT: "6001" })).toBe(6001);
    expect(getE2eClientPort({ COCKPIT_E2E_CLIENT_PORT: "6002" })).toBe(6002);
  });

  it("falls back to the e2e default on a malformed or empty value", () => {
    expect(getE2eServerPort({ COCKPIT_E2E_SERVER_PORT: "" })).toBe(
      DEFAULT_PORTS.e2eServer,
    );
    expect(getE2eServerPort({ COCKPIT_E2E_SERVER_PORT: "not-a-port" })).toBe(
      DEFAULT_PORTS.e2eServer,
    );
    expect(getE2eClientPort({ COCKPIT_E2E_CLIENT_PORT: "70000" })).toBe(
      DEFAULT_PORTS.e2eClient,
    );
  });

  it("the e2e server/client ports differ from each other", () => {
    expect(getE2eServerPort({})).not.toBe(getE2eClientPort({}));
  });
});
