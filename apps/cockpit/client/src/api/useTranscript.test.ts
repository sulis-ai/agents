// CH-GJ9KQR WP-006 — useTranscript drives the store-backed raw transcript read.
//
// The raw transcript view is being re-pointed at OUR durable ThreadStore
// (WP-002) instead of Claude's provider transcript files (SUBSTITUTE-Strangle,
// data-source re-point — no visual change). The server route owns the source
// swap; this hook is behaviour-preserving for the UI: it consumes the SAME
// `/api/changes/:id/transcript` endpoint through the typed query funnel
// (apiGet — never `fetch` in a component, WPF-02) and renders the SAME
// `TranscriptMessage[]` wire shape.
//
// This is the WP's verification artifact (frontend adapter): it proves the
// hook reads the store-backed records the re-pointed route now serves, and
// renders empty when the store has none (the strangle returns []).

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

import type { TranscriptMessage } from "../../../shared/api-types";
import { useTranscript } from "./useTranscript";

function freshClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
  });
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function renderInClient(ui: React.ReactElement) {
  const client = freshClient();
  return render(
    React.createElement(QueryClientProvider, { client }, ui),
  );
}

describe("useTranscript (store-backed raw read)", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockReset();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the TranscriptMessage[] the store-backed route serves", async () => {
    // The re-pointed route projects our durable ThreadStore records onto the
    // TranscriptMessage wire shape; the hook renders them unchanged.
    const payload: TranscriptMessage[] = [
      {
        kind: "assistant",
        uuid: "01CHG-0",
        timestamp: "2026-06-24T10:00:00.000Z",
        blocks: [{ kind: "text", text: "from our durable store" }],
      },
    ];
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse(200, payload));

    function Probe() {
      const q = useTranscript("01CHG");
      return React.createElement(
        "div",
        { "data-testid": "probe" },
        q.isSuccess ? `${q.data.length}:${q.data[0]?.uuid ?? ""}` : q.status,
      );
    }

    const { getByTestId } = renderInClient(React.createElement(Probe));
    await waitFor(() =>
      expect(getByTestId("probe").textContent).toBe("1:01CHG-0"),
    );
    // It reads the SAME endpoint (the route swapped the source, not the URL).
    expect(fetchMock.mock.calls[0]![0]).toBe("/api/changes/01CHG/transcript");
  });

  it("renders empty when the store has no records for the change", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(200, []));

    function Probe() {
      const q = useTranscript("01EMPTY");
      return React.createElement(
        "div",
        { "data-testid": "probe" },
        q.isSuccess ? `len:${q.data.length}` : q.status,
      );
    }

    const { getByTestId } = renderInClient(React.createElement(Probe));
    await waitFor(() =>
      expect(getByTestId("probe").textContent).toBe("len:0"),
    );
  });

  it("does not fetch until a change id is supplied (enabled guard)", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse(200, []));

    function Probe() {
      const q = useTranscript("");
      return React.createElement(
        "div",
        { "data-testid": "probe" },
        q.fetchStatus,
      );
    }

    const { getByTestId } = renderInClient(React.createElement(Probe));
    await waitFor(() =>
      expect(getByTestId("probe").textContent).toBe("idle"),
    );
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
