// WP-014 — <FilePane /> tests.
//
// <FilePane> reads useFile(changeId, selectedPath) and renders:
//   - no selection → friendly "pick a file" prompt
//   - loading → "Loading file..."
//   - error → "Could not load file: <message>"
//   - binary → <FileBinaryState> (no Monaco mount)
//   - truncated → <FileTruncatedState>
//   - otherwise → <FileToolbar> + <MonacoFile content language />
//
// Monaco is mocked (the wrapper is heavy and irrelevant to FilePane's
// branching logic). The mock records mounts so the binary/truncated
// tests can assert Monaco is NOT mounted.
//
// References: WP-014 Contract (<FilePane>, <FileBinaryState>,
// <FileTruncatedState>), ADR-001.

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { FileContents } from "../../../shared/api-types";

const monacoMount = vi.fn();
vi.mock("@monaco-editor/react", () => ({
  __esModule: true,
  default: (props: Record<string, unknown>) => {
    monacoMount(props);
    return <div data-testid="monaco-editor-mock" />;
  },
}));

import { FilePane } from "../components/FilePane";

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

function renderPane(filePath: string | null) {
  const entry = filePath
    ? `/c/abc?file=${encodeURIComponent(filePath)}`
    : "/c/abc";
  const client = freshClient();
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[entry]}>
        <Routes>
          <Route path="/c/:changeId" element={<FilePane changeId="abc" />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function makeFile(overrides: Partial<FileContents> = {}): FileContents {
  return {
    path: "src/index.ts",
    absolutePath: "/Users/founder/wt/src/index.ts",
    content: "const x = 1;\n",
    binary: false,
    truncated: false,
    sizeBytes: 13,
    language: "typescript",
    ...overrides,
  };
}

describe("<FilePane />", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockReset();
    monacoMount.mockClear();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows a 'pick a file' prompt when nothing is selected", () => {
    renderPane(null);
    expect(screen.getByText(/pick a file/i)).toBeInTheDocument();
  });

  it("shows a loading state while the file is fetching", () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(
      () => new Promise(() => {}),
    );
    renderPane("src/index.ts");
    expect(screen.getByText(/loading file/i)).toBeInTheDocument();
  });

  it("shows the error state on a fetch failure", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(500, { error: "boom" }),
    );
    renderPane("src/index.ts");
    await waitFor(() =>
      expect(screen.getByText(/could not load file/i)).toBeInTheDocument(),
    );
  });

  it("renders <MonacoFile> with the content and language for a text file", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(200, makeFile()),
    );
    renderPane("src/index.ts");

    await waitFor(() =>
      expect(screen.getByTestId("monaco-editor-mock")).toBeInTheDocument(),
    );
    const props = monacoMount.mock.calls.at(-1)?.[0] as Record<string, unknown>;
    expect(props.value).toBe("const x = 1;\n");
    expect(props.defaultLanguage).toBe("typescript");
  });

  it("renders <FileBinaryState> (no Monaco) for a binary file", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(200, makeFile({ binary: true, content: null })),
    );
    renderPane("logo.png");

    await waitFor(() =>
      expect(screen.getByTestId("file-binary-state")).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("monaco-editor-mock")).not.toBeInTheDocument();
  });

  it("renders <FileTruncatedState> for a truncated file", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(200, makeFile({ truncated: true, content: null })),
    );
    renderPane("huge.log");

    await waitFor(() =>
      expect(screen.getByTestId("file-truncated-state")).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("monaco-editor-mock")).not.toBeInTheDocument();
  });

  it("renders the toolbar with a disabled diff toggle stub", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(200, makeFile()),
    );
    renderPane("src/index.ts");

    await waitFor(() =>
      expect(screen.getByTestId("monaco-editor-mock")).toBeInTheDocument(),
    );
    const diffButton = screen.getByRole("button", { name: /show diff/i });
    expect(diffButton).toBeDisabled();
  });
});
