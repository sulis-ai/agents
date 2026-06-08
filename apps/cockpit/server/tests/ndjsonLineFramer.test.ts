// WP-002 (BLUE) — the shared NDJSON line-framing primitive (the extracted
// duplicate from terminal-proxy.ts + TerminalSidecar.ts). Lives in server/tests/
// because that is the node-env vitest project (shared/ modules are exercised
// from whichever side runs them — groupTurns is tested from the client side).

import { describe, it, expect } from "vitest";

import { createNdjsonLineFramer } from "../../shared/ndjsonLineFramer";

describe("createNdjsonLineFramer", () => {
  it("returns each complete line with the trailing newline stripped", () => {
    const f = createNdjsonLineFramer();
    expect(f.push('{"a":1}\n{"b":2}\n')).toEqual(['{"a":1}', '{"b":2}']);
  });

  it("retains a partial trailing line until the rest arrives across chunks", () => {
    const f = createNdjsonLineFramer();
    // A line split across two reads — the boundary the framer exists to handle.
    expect(f.push('{"hel')).toEqual([]);
    expect(f.push('lo":1}\n')).toEqual(['{"hello":1}']);
  });

  it("splits a single batched frame into multiple lines", () => {
    const f = createNdjsonLineFramer();
    expect(f.push('a\nb\nc\n')).toEqual(["a", "b", "c"]);
  });

  it("drops blank / whitespace-only lines", () => {
    const f = createNdjsonLineFramer();
    expect(f.push('x\n\n  \ny\n')).toEqual(["x", "y"]);
  });

  it("accepts Buffer chunks (the socket `data` shape) the same as strings", () => {
    const f = createNdjsonLineFramer();
    expect(f.push(Buffer.from('{"k":"v"}\n', "utf8"))).toEqual(['{"k":"v"}']);
  });

  it("preserves a non-terminated final line until its newline arrives", () => {
    const f = createNdjsonLineFramer();
    expect(f.push('done')).toEqual([]); // no newline yet → buffered, not emitted
    expect(f.push('\n')).toEqual(["done"]);
  });
});
