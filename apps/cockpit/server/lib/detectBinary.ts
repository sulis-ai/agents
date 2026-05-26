// WP-007 — binary detection.
//
// "Binary" for the cockpit's purposes means: a NUL byte (0x00) appears
// somewhere in the first 8 KiB of the file. This is the same heuristic
// `git diff` and most text-editor "is this a binary file?" detectors
// use. It is intentionally crude — it will misclassify some valid
// text-with-embedded-NULs files (rare in source code) and will pass
// some binary formats that happen to have no NULs in their first
// 8 KiB (rare; nearly every binary format has NUL-padded headers).
//
// The 8 KiB window matters: a 100 MiB binary file gets classified
// without ever being fully read into memory (callers pair this with a
// streaming or capped read). For readFileContents, the caller has
// already stat'd the file and either read it whole (under the 1 MiB
// cap) or refused the read (over the cap), so this function sees a
// buffer that is at most 1 MiB anyway.
//
// References:
// - TDD §13.6 ("binary detection: NUL byte in first 8 KiB").
// - ADR-006 ("server detects binary content").
// - WP-008 (diff reader) will import this same helper, per the
//   WP-007 Blue spec on reuse.

const BINARY_DETECTION_WINDOW_BYTES = 8 * 1024;

/**
 * Returns `true` iff the buffer contains a NUL byte (0x00) within its
 * first 8 KiB. Buffers shorter than 8 KiB are scanned in full.
 *
 * Pure function: deterministic, no I/O, no allocations beyond a single
 * `subarray` view (which is a zero-copy window over the same memory).
 */
export function detectBinary(buf: Buffer): boolean {
  const window = buf.subarray(0, BINARY_DETECTION_WINDOW_BYTES);
  return window.includes(0);
}
