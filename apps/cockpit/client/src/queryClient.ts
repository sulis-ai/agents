// WP-011 — TanStack Query client + defaults (ADR-007).
//
// One QueryClient for the whole app. The defaults below match ADR-007:
//
//   - staleTime: 5_000 — server data is considered fresh for a few
//     seconds; refresh button + window-focus opt-out.
//   - refetchOnWindowFocus: false — the cockpit is an internal tool;
//     focus refetches would interrupt the founder mid-read.
//   - retry: 1 — one polite retry for transient flake; surface errors
//     fast otherwise so the user sees them.
//
// Liveness polling (TDD §2.2 + §6.1) overrides refetchInterval on a
// per-hook basis in WP-012; the defaults intentionally don't poll.

import { QueryClient } from "@tanstack/react-query";

export const QUERY_DEFAULTS = {
  staleTime: 5_000,
  refetchOnWindowFocus: false,
  retry: 1,
} as const;

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: QUERY_DEFAULTS,
  },
});
