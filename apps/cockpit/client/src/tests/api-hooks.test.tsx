// WP-011 — API hooks tests.
//
// One representative test per endpoint hook. Each test:
//   - Mocks globalThis.fetch with a JSON response.
//   - Wraps <Component /> in a fresh QueryClientProvider with retry off.
//   - Asserts the hook hits the correct URL and returns parsed JSON.
//
// The hooks compile against the shared types from WP-001
// (apps/cockpit/shared/api-types.ts) — server endpoints are not yet
// running at this WP's runtime; the integration test in WP-016 ties
// the two sides together.

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { Change, ChangeDetail, TreeNode, FileContents, FileDiff, TranscriptMessage } from "../../../shared/api-types";
import { useChanges } from "../api/useChanges";
import { useChange } from "../api/useChange";
import { useTree } from "../api/useTree";
import { useFile } from "../api/useFile";
import { useDiff } from "../api/useDiff";
import { useTranscript } from "../api/useTranscript";

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

function renderHookInsideClient(ui: React.ReactElement) {
  const client = freshClient();
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("API hooks", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockReset();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("useChanges → GET /api/changes", async () => {
    const payload: Change[] = [];
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse(200, payload));

    function Probe() {
      const q = useChanges();
      return <div data-testid="probe">{q.isSuccess ? "ok" : q.status}</div>;
    }

    const { getByTestId } = renderHookInsideClient(<Probe />);
    await waitFor(() => expect(getByTestId("probe").textContent).toBe("ok"));
    expect(fetchMock.mock.calls[0]![0]).toBe("/api/changes");
  });

  it("useChange → GET /api/changes/:id", async () => {
    const payload = { changeId: "abc" } as unknown as ChangeDetail;
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse(200, payload));

    function Probe() {
      const q = useChange("abc");
      return <div data-testid="probe">{q.isSuccess ? "ok" : q.status}</div>;
    }
    const { getByTestId } = renderHookInsideClient(<Probe />);
    await waitFor(() => expect(getByTestId("probe").textContent).toBe("ok"));
    expect(fetchMock.mock.calls[0]![0]).toBe("/api/changes/abc");
  });

  it("useTree → GET /api/changes/:id/tree", async () => {
    const payload: TreeNode[] = [];
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse(200, payload));

    function Probe() {
      const q = useTree("abc");
      return <div data-testid="probe">{q.isSuccess ? "ok" : q.status}</div>;
    }
    const { getByTestId } = renderHookInsideClient(<Probe />);
    await waitFor(() => expect(getByTestId("probe").textContent).toBe("ok"));
    expect(fetchMock.mock.calls[0]![0]).toBe("/api/changes/abc/tree");
  });

  it("useFile → GET /api/changes/:id/file?path=...", async () => {
    const payload = { path: "src/main.tsx" } as unknown as FileContents;
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse(200, payload));

    function Probe() {
      const q = useFile("abc", "src/main.tsx");
      return <div data-testid="probe">{q.isSuccess ? "ok" : q.status}</div>;
    }
    const { getByTestId } = renderHookInsideClient(<Probe />);
    await waitFor(() => expect(getByTestId("probe").textContent).toBe("ok"));
    expect(fetchMock.mock.calls[0]![0]).toBe(
      "/api/changes/abc/file?path=src%2Fmain.tsx",
    );
  });

  it("useDiff → GET /api/changes/:id/diff?path=...", async () => {
    const payload = { path: "src/main.tsx" } as unknown as FileDiff;
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse(200, payload));

    function Probe() {
      const q = useDiff("abc", "src/main.tsx");
      return <div data-testid="probe">{q.isSuccess ? "ok" : q.status}</div>;
    }
    const { getByTestId } = renderHookInsideClient(<Probe />);
    await waitFor(() => expect(getByTestId("probe").textContent).toBe("ok"));
    expect(fetchMock.mock.calls[0]![0]).toBe(
      "/api/changes/abc/diff?path=src%2Fmain.tsx",
    );
  });

  it("useTranscript → GET /api/changes/:id/transcript", async () => {
    const payload: TranscriptMessage[] = [];
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse(200, payload));

    function Probe() {
      const q = useTranscript("abc");
      return <div data-testid="probe">{q.isSuccess ? "ok" : q.status}</div>;
    }
    const { getByTestId } = renderHookInsideClient(<Probe />);
    await waitFor(() => expect(getByTestId("probe").textContent).toBe("ok"));
    expect(fetchMock.mock.calls[0]![0]).toBe("/api/changes/abc/transcript");
  });

  it("useFile is disabled when path is empty (no fetch)", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse(200, {}));

    function Probe() {
      const q = useFile("abc", "");
      return <div data-testid="probe">{q.fetchStatus}</div>;
    }
    const { getByTestId } = renderHookInsideClient(<Probe />);
    await waitFor(() =>
      expect(getByTestId("probe").textContent).toBe("idle"),
    );
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
