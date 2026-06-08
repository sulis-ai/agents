// WP-015 — <MonacoDiff /> tests.
//
// <MonacoDiff> wraps @monaco-editor/react's <DiffEditor> in read-only
// mode (both panes). Monaco is heavy, so we mock the wrapper and assert
// the props we pass:
//   - original === base ?? ""        (null base → empty original pane)
//   - modified === current ?? ""     (null current → empty modified pane)
//   - originalLanguage / modifiedLanguage === the hint (or "plaintext")
//   - options.readOnly === true      (the load-bearing ADR-006 guard)
// We also assert the component is lazy-loaded (React.lazy) so Monaco
// never ships on the dashboard route — same as <MonacoFile> (WP-014).
//
// References: WP-015 Contract (<MonacoDiff>), ADR-006 (DiffEditor
// displays, both panes read-only), TDD §7.

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Suspense } from "react";

// Capture the props @monaco-editor/react's <DiffEditor> receives.
const diffEditorProps = vi.fn();
vi.mock("@monaco-editor/react", () => ({
  __esModule: true,
  DiffEditor: (props: Record<string, unknown>) => {
    diffEditorProps(props);
    return <div data-testid="monaco-diff-mock" />;
  },
}));

// Imported after the mock is registered.
import { MonacoDiff } from "../components/MonacoDiff";
import { ThemeProvider, useTheme } from "../theme/ThemeProvider";
import { THEME_STORAGE_KEY } from "../theme/resolveInitialTheme";

/** Minimal harness exposing a toggle so a test can flip the provider theme. */
function ThemeToggleProbe() {
  const { toggle } = useTheme();
  return (
    <button type="button" data-testid="flip-theme" onClick={toggle}>
      flip
    </button>
  );
}

/** Read the Monaco theme id from the last props the mocked DiffEditor got. */
function lastTheme(): unknown {
  const props = diffEditorProps.mock.calls.at(-1)?.[0] as Record<
    string,
    unknown
  >;
  return props.theme;
}

async function renderDiff(props: {
  base: string | null;
  current: string | null;
  language: string | null;
}) {
  render(
    <ThemeProvider>
      <Suspense fallback={<div>loading diff</div>}>
        <MonacoDiff {...props} />
      </Suspense>
    </ThemeProvider>,
  );
  await waitFor(() =>
    expect(screen.getByTestId("monaco-diff-mock")).toBeInTheDocument(),
  );
  return diffEditorProps.mock.calls.at(-1)?.[0] as Record<string, unknown>;
}

describe("<MonacoDiff />", () => {
  beforeEach(() => {
    diffEditorProps.mockClear();
  });

  it("passes base/current to original/modified and the language hint", async () => {
    const props = await renderDiff({
      base: "const x = 1;\n",
      current: "const x = 2;\n",
      language: "typescript",
    });
    expect(props.original).toBe("const x = 1;\n");
    expect(props.modified).toBe("const x = 2;\n");
    expect(props.originalLanguage).toBe("typescript");
    expect(props.modifiedLanguage).toBe("typescript");
  });

  it("configures both panes as read-only (ADR-006)", async () => {
    const props = await renderDiff({
      base: "a",
      current: "b",
      language: null,
    });
    const options = props.options as Record<string, unknown>;
    expect(options.readOnly).toBe(true);
  });

  it("falls back to plaintext when no language hint is given", async () => {
    const props = await renderDiff({ base: "a", current: "b", language: null });
    expect(props.originalLanguage).toBe("plaintext");
    expect(props.modifiedLanguage).toBe("plaintext");
  });

  it("renders an empty original pane when base is null (file added at base)", async () => {
    const props = await renderDiff({
      base: null,
      current: "hello",
      language: null,
    });
    expect(props.original).toBe("");
    expect(props.modified).toBe("hello");
  });

  it("renders an empty modified pane when current is null (file removed)", async () => {
    const props = await renderDiff({
      base: "hello",
      current: null,
      language: null,
    });
    expect(props.original).toBe("hello");
    expect(props.modified).toBe("");
  });

  it("is lazy-loaded so Monaco does not ship on the dashboard route", async () => {
    const mod = await import("../components/MonacoDiff");
    const Lazy = mod.MonacoDiff as unknown as { $$typeof?: symbol };
    expect(typeof Lazy).not.toBe("function");
    expect(String(Lazy.$$typeof)).toContain("lazy");
  });
});

describe("<MonacoDiff /> follows the app theme (WP-005, ADR-002)", () => {
  beforeEach(() => {
    diffEditorProps.mockClear();
    window.localStorage.clear();
  });

  afterEach(() => {
    window.localStorage.clear();
  });

  async function renderWithSavedTheme(saved: "light" | "dark") {
    // A saved choice wins outright (ADR-001), so the provider resolves to it
    // deterministically without touching matchMedia.
    window.localStorage.setItem(THEME_STORAGE_KEY, saved);
    render(
      <ThemeProvider>
        <ThemeToggleProbe />
        <Suspense fallback={<div>loading diff</div>}>
          <MonacoDiff base={"a"} current={"b"} language={null} />
        </Suspense>
      </ThemeProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("monaco-diff-mock")).toBeInTheDocument(),
    );
  }

  it("passes the light Monaco theme when the app theme is light", async () => {
    await renderWithSavedTheme("light");
    expect(lastTheme()).toBe("vs");
  });

  it("passes the dark Monaco theme when the app theme is dark", async () => {
    await renderWithSavedTheme("dark");
    expect(lastTheme()).toBe("vs-dark");
  });

  it("restyles live when the provider theme flips (no remount)", async () => {
    await renderWithSavedTheme("light");
    expect(lastTheme()).toBe("vs");

    fireEvent.click(screen.getByTestId("flip-theme"));

    await waitFor(() => expect(lastTheme()).toBe("vs-dark"));
  });
});
