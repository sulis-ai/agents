// WP-014 — <MonacoFile /> tests.
//
// <MonacoFile> wraps @monaco-editor/react's <Editor> in read-only mode.
// Monaco is heavy, so we mock the wrapper and assert the props we pass:
//   - value === the file content
//   - defaultLanguage === the language hint (or "plaintext")
//   - options.readOnly === true  (the load-bearing ADR-001 client guard)
//   - options.minimap.enabled === false, scrollBeyondLastLine === false
// We also assert the component is lazy-loaded (React.lazy) so the Monaco
// bundle never ships on the dashboard route.
//
// References: WP-014 Contract (<MonacoFile> shape), ADR-001 (Monaco
// read-only), TDD §6.

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { Suspense } from "react";

// Capture the props @monaco-editor/react's <Editor> receives.
const editorProps = vi.fn();
vi.mock("@monaco-editor/react", () => ({
  __esModule: true,
  default: (props: Record<string, unknown>) => {
    editorProps(props);
    return <div data-testid="monaco-editor-mock" />;
  },
}));

// Imported after the mock is registered.
import { MonacoFile } from "../components/MonacoFile";

describe("<MonacoFile />", () => {
  beforeEach(() => {
    editorProps.mockClear();
  });

  it("renders the Monaco editor with the file content and language hint", async () => {
    render(
      <Suspense fallback={<div>loading editor</div>}>
        <MonacoFile content={"const x = 1;\n"} language={"typescript"} />
      </Suspense>,
    );

    await waitFor(() =>
      expect(screen.getByTestId("monaco-editor-mock")).toBeInTheDocument(),
    );

    const props = editorProps.mock.calls.at(-1)?.[0] as Record<string, unknown>;
    expect(props.value).toBe("const x = 1;\n");
    expect(props.defaultLanguage).toBe("typescript");
  });

  it("configures the editor as read-only with no minimap (ADR-001)", async () => {
    render(
      <Suspense fallback={<div>loading editor</div>}>
        <MonacoFile content={"x"} language={null} />
      </Suspense>,
    );

    await waitFor(() =>
      expect(screen.getByTestId("monaco-editor-mock")).toBeInTheDocument(),
    );

    const props = editorProps.mock.calls.at(-1)?.[0] as Record<string, unknown>;
    const options = props.options as Record<string, unknown>;
    expect(options.readOnly).toBe(true);
    expect((options.minimap as { enabled: boolean }).enabled).toBe(false);
    expect(options.scrollBeyondLastLine).toBe(false);
  });

  it("falls back to plaintext when no language hint is given", async () => {
    render(
      <Suspense fallback={<div>loading editor</div>}>
        <MonacoFile content={"plain text"} language={null} />
      </Suspense>,
    );

    await waitFor(() =>
      expect(screen.getByTestId("monaco-editor-mock")).toBeInTheDocument(),
    );

    const props = editorProps.mock.calls.at(-1)?.[0] as Record<string, unknown>;
    expect(props.defaultLanguage).toBe("plaintext");
  });

  it("is lazy-loaded so Monaco does not ship on the dashboard route", async () => {
    // The component is exported as a React.lazy() result, which is an
    // object with a $$typeof of React.lazy and a _payload/_init pair.
    // We assert it is NOT a plain function component (which would mean a
    // static import).
    const mod = await import("../components/MonacoFile");
    const Lazy = mod.MonacoFile as unknown as { $$typeof?: symbol };
    expect(typeof Lazy).not.toBe("function");
    expect(String(Lazy.$$typeof)).toContain("lazy");
  });
});
