// WP-002 (BLUE / EP-03 REFACTOR) — the shared NDJSON line-framing primitive.
//
// Both the production terminal sidecar (server/adapters/TerminalSidecar.ts) and
// the e2e terminal proxy (e2e/terminal-proxy.ts) read a byte STREAM off an
// AF_UNIX socket and must re-frame it into complete `\n`-delimited NDJSON lines
// before forwarding each line to the browser WebSocket. A TCP/AF_UNIX read can
// split a line across two `data` events or batch several lines into one, so a
// naive "one chunk = one line" forward corrupts the wire. Both consumers carried
// the same hand-rolled buffer-and-split loop — the textbook 2-consumer trigger
// for extracting the shared primitive (EP-03).
//
// This is intentionally tiny and dependency-free so it is safe to import from
// BOTH the server tree and the e2e tree (both inside apps/cockpit/, so the
// import-boundary rule in .eslintrc.json is satisfied).

/**
 * A stateful NDJSON line framer. Feed it raw UTF-8 chunks off a byte stream;
 * it returns the complete lines contained in each chunk (trailing-newline
 * stripped) and retains any partial trailing line until the rest arrives.
 *
 * Blank lines (whitespace-only) are dropped — they carry no NDJSON object and
 * both prior consumers skipped them.
 *
 * Usage:
 *   const framer = createNdjsonLineFramer();
 *   sock.on("data", (chunk) => {
 *     for (const line of framer.push(chunk)) forward(line);
 *   });
 */
export interface NdjsonLineFramer {
  /** Absorb one chunk; return the complete NDJSON lines it completed. */
  push(chunk: Buffer | string): string[];
}

export function createNdjsonLineFramer(): NdjsonLineFramer {
  let buf = "";
  return {
    push(chunk: Buffer | string): string[] {
      buf += typeof chunk === "string" ? chunk : chunk.toString("utf8");
      const lines: string[] = [];
      let nl: number;
      while ((nl = buf.indexOf("\n")) !== -1) {
        const line = buf.slice(0, nl);
        buf = buf.slice(nl + 1);
        if (line.trim()) lines.push(line);
      }
      return lines;
    },
  };
}
