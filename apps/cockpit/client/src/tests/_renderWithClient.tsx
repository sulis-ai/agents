// Shared test harness: wrap a UI tree (or hook) in a fresh QueryClient.
//
// Several components/hooks call `useQueryClient` (e.g. useChatStream invalidates
// the transcript/summaries queries on a reply). Rendering them without a
// provider throws "No QueryClient set". This is the ONE place that builds the
// provider so the three+ test files don't each duplicate the wrapper (EP-03).
//
// - `freshQueryClient()` — a client with retries off (tests must fail fast, not
//   re-poll a mocked network).
// - `withQueryClient(children)` — the JSX wrapper, for `renderHook`'s `wrapper`
//   option or manual composition with other providers (Router etc.).
// - `renderWithClient(ui)` — render `ui` already wrapped, returning RTL's result.

import type { ReactElement, ReactNode } from "react";
import { render } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

/** A QueryClient with retries disabled — tests fail fast, never re-poll. */
export function freshQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
}

/** Wrap `children` in a fresh QueryClientProvider (composable with other providers). */
export function withQueryClient(children: ReactNode): ReactElement {
  return <QueryClientProvider client={freshQueryClient()}>{children}</QueryClientProvider>;
}

/** Render `ui` wrapped in a fresh QueryClientProvider; returns RTL's result. */
export function renderWithClient(ui: ReactElement) {
  return render(withQueryClient(ui));
}
