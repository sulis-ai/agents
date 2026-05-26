// WP-001 — skeleton test for the placeholder client root.
//
// Per the WP Contract's Red checklist: <App /> must render without
// throwing. We don't assert any visible content beyond a single anchor
// string ("cockpit booting") because pages + components are the work of
// later WPs (WP-011 onwards).

import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { App } from "../App";

describe("client App (placeholder)", () => {
  it("renders without throwing", () => {
    const { container } = render(<App />);
    expect(container.textContent ?? "").toMatch(/cockpit booting/i);
  });
});
