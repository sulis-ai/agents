// WP-007 — unit tests for the detectBinary helper.
//
// Per TDD §13.6 / ADR-006: "binary" means a NUL byte appears in the
// first 8 KiB of the file. Anything else (including high-bit UTF-8
// bytes, control characters other than NUL) is treated as text.

import { describe, it, expect } from "vitest";

import { detectBinary } from "../lib/detectBinary";

describe("detectBinary", () => {
  it("returns false for an empty buffer", () => {
    expect(detectBinary(Buffer.alloc(0))).toBe(false);
  });

  it("returns true for a buffer of all NUL bytes", () => {
    expect(detectBinary(Buffer.alloc(64, 0))).toBe(true);
  });

  it("returns true when a NUL byte appears anywhere in the first 8 KiB", () => {
    const buf = Buffer.alloc(1024, 0x41); // 1 KiB of 'A'
    buf[512] = 0;
    expect(detectBinary(buf)).toBe(true);
  });

  it("returns false for UTF-8 text including emoji and high-bit bytes", () => {
    const buf = Buffer.from("hello world 👋 résumé café", "utf8");
    expect(detectBinary(buf)).toBe(false);
  });

  it("returns false for ASCII control characters other than NUL (e.g. \\t, \\n, \\r)", () => {
    const buf = Buffer.from("line1\n\tindented\r\nline2\n", "utf8");
    expect(detectBinary(buf)).toBe(false);
  });

  it("ignores NUL bytes that appear after the first 8 KiB", () => {
    // 9 KiB: first 8 KiB are 'A', byte 8192 is NUL. Per the contract,
    // we only inspect the first 8 KiB, so this is "text" by detection.
    const buf = Buffer.alloc(9 * 1024, 0x41);
    buf[8192] = 0;
    expect(detectBinary(buf)).toBe(false);
  });

  it("returns true when a NUL byte appears at exactly byte 0", () => {
    const buf = Buffer.alloc(16, 0x41);
    buf[0] = 0;
    expect(detectBinary(buf)).toBe(true);
  });

  it("returns true when a NUL byte appears at exactly byte 8191 (last byte of the window)", () => {
    const buf = Buffer.alloc(8192, 0x41);
    buf[8191] = 0;
    expect(detectBinary(buf)).toBe(true);
  });
});
