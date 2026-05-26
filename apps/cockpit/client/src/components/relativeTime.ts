// WP-013 — coarse relative-time helper for bubble timestamps.
//
// Single-source so <ChatMessage /> and any future chat-time consumer
// share one implementation. The cockpit's MVP doesn't need precise
// relative formatting; "long enough ago that the founder can scan
// past" is the bar. The full timestamp is exposed via the wrapping
// <time> element's dateTime/title for hover precision.
//
// WP-012 will ship a sibling helper for dashboard cards; the two
// converge in a follow-up if a second consumer pattern emerges (the
// 2-consumer rule). Today they stay separate to avoid a phantom
// cross-WP import.

export function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const now = Date.now();
  const seconds = Math.max(0, Math.floor((now - then) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
