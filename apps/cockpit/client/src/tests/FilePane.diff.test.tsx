// WP-015 — <FilePane /> diff-mode tests.
//
// When ?diff=1 is set and a file is selected, <FilePane> reads
// useDiff(changeId, path) instead of useFile and renders:
//   - text payload    → <MonacoDiff base current language />
//   - binary/truncated → <DiffUnavailableState>
//   - 422 NO_BASE_SHA  → <NoBaseShaState>
// It must NOT call the /file endpoint in diff mode (asserted by a
// fetch-spy that routes by URL).
//
// Monaco's DiffEditor is mocked (heavy; irrelevant to FilePane's
// branching). The mock records mounts so the binary/no-base tests can
// assert it is NOT mounted.
//
// References: WP-015 Contract (<FilePane> diff behaviour,
// <DiffUnavailableState>, <NoBaseShaState>), ADR-006, TDD §7.

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { FileDiff } from "../../../shared/api-types";

const diffMount = vi.fn();
vi.mock("@monaco-editor/react", () => ({
  __esModule: true,
  // both Editor (file) and DiffEditor (diff) come from this module
  default: () => <div data-testid="monaco-editor-mock" />,
  DiffEditor: (props: Record<string, unknown>) => {
    diffMount(props);
    return <div data-testid="monaco-diff-mock" />;
  },
}));

import { FilePane } from "../components/FilePane";
import { ThemeProvider } from "../theme/ThemeProvider";

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

function renderPaneDiff(filePath: string) {
  const entry = `/c/abc?file=${encodeURIComponent(filePath)}&diff=1`;
  const client = freshClient();
  return render(
    <ThemeProvider>
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={[entry]}>
          <Routes>
            <Route path="/c/:changeId" element={<FilePane changeId="abc" />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    </ThemeProvider>,
  );
}

function makeDiff(overrides: Partial<FileDiff> = {}): FileDiff {
  return {
    path: "src/index.ts",
    absolutePath: "/Users/founder/wt/src/index.ts",
    base: "const x = 1;\n",
    current: "const x = 2;\n",
    binary: false,
    truncated: false,
    language: "typescript",
    ...overrides,
  };
}

describe("<FilePane /> diff mode", () => {
  beforeEach(() => {
    diffMount.mockClear();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders <MonacoDiff> with base/current/language for a text diff", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(200, makeDiff()),
    );
    renderPaneDiff("src/index.ts");

    await waitFor(() =>
      expect(screen.getByTestId("monaco-diff-mock")).toBeInTheDocument(),
    );
    const props = diffMount.mock.calls.at(-1)?.[0] as Record<string, unknown>;
    expect(props.original).toBe("const x = 1;\n");
    expect(props.modified).toBe("const x = 2;\n");
    expect(props.originalLanguage).toBe("typescript");
  });

  it("renders <DiffUnavailableState> (no Monaco) for a binary diff", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(200, makeDiff({ binary: true, base: null, current: null })),
    );
    renderPaneDiff("logo.png");

    await waitFor(() =>
      expect(screen.getByTestId("diff-unavailable-state")).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("monaco-diff-mock")).not.toBeInTheDocument();
  });

  it("renders <DiffUnavailableState> for a truncated diff", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(
        200,
        makeDiff({ truncated: true, base: null, current: null }),
      ),
    );
    renderPaneDiff("huge.log");

    await waitFor(() =>
      expect(screen.getByTestId("diff-unavailable-state")).toBeInTheDocument(),
    );
  });

  it("renders <NoBaseShaState> on a 422 NO_BASE_SHA response", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(422, {
        error: "no base_sha recorded for this change",
        code: "NO_BASE_SHA",
      }),
    );
    renderPaneDiff("src/index.ts");

    await waitFor(() =>
      expect(screen.getByTestId("no-base-sha-state")).toBeInTheDocument(),
    );
  });

  it("does NOT call the /file endpoint in diff mode (only /diff)", async () => {
    const spy = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation((input: RequestInfo | URL) => {
        const url = typeof input === "string" ? input : input.toString();
        if (url.includes("/diff")) {
          return Promise.resolve(jsonResponse(200, makeDiff()));
        }
        return Promise.resolve(jsonResponse(200, { unexpected: true }));
      });
    renderPaneDiff("src/index.ts");

    await waitFor(() =>
      expect(screen.getByTestId("monaco-diff-mock")).toBeInTheDocument(),
    );
    const calledUrls = spy.mock.calls.map((c) =>
      typeof c[0] === "string" ? c[0] : String(c[0]),
    );
    expect(calledUrls.some((u) => u.includes("/diff"))).toBe(true);
    expect(calledUrls.some((u) => u.includes("/file"))).toBe(false);
  });
});
