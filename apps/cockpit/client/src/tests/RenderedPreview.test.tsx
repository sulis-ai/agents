// WP-006 — <RenderedPreview> tests (FR-08/09).
//
// The rendered-preview wrapper for the Files section. For a RENDERABLE
// document (.md / .html) it shows a RENDERED view with a one-click
// Rendered ↔ Raw toggle (FR-08/09); it REUSES the app's renderer rather
// than forking one (EP-03): markdown via the shared renderMarkdown(), and
// raw markdown as the contract's `.raw` <pre>. An .html document renders
// inside a sandboxed iframe (no scripts) — the same "show it the way it's
// meant to look" intent as the contract-preview renderer. A CODE file is
// not renderable: it stays read-only source (delegated to <MonacoFile>),
// with no toggle.
//
// Matches the SIGNED visual contract panel 6 (`.previewbar` + `.toggle`
// with Rendered/Raw, `.rendered`, `.raw`).

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

// Monaco is heavy + jsdom-hostile; mock the wrapper (the raw view of a CODE
// file delegates to it).
const editorProps = vi.fn();
vi.mock("@monaco-editor/react", () => ({
  __esModule: true,
  default: (props: Record<string, unknown>) => {
    editorProps(props);
    return <div data-testid="monaco-editor-mock" />;
  },
}));

import { RenderedPreview } from "../components/RenderedPreview";

const MD = "# Heading\n\nA paragraph with **bold**.\n\n- one\n- two";

describe("<RenderedPreview /> (FR-08/09)", () => {
  beforeEach(() => editorProps.mockClear());

  it("renders a .md document as HTML by default", () => {
    render(
      <RenderedPreview path="docs/SRD.md" content={MD} language="markdown" />,
    );
    const rendered = screen.getByTestId("preview-rendered");
    expect(rendered.querySelector("h1")?.textContent).toBe("Heading");
    expect(rendered.querySelector("strong")?.textContent).toBe("bold");
    expect(rendered.querySelectorAll("li")).toHaveLength(2);
  });

  it("offers a Rendered ↔ Raw toggle and flips to raw source and back", async () => {
    render(
      <RenderedPreview path="docs/SRD.md" content={MD} language="markdown" />,
    );
    // Starts rendered.
    expect(screen.getByTestId("preview-rendered")).toBeInTheDocument();
    expect(screen.queryByTestId("preview-raw")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /raw/i }));
    const raw = screen.getByTestId("preview-raw");
    // Raw shows the EXACT source text, unrendered.
    expect(raw.textContent).toContain("# Heading");
    expect(raw.textContent).toContain("**bold**");
    expect(screen.queryByTestId("preview-rendered")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /rendered/i }));
    expect(screen.getByTestId("preview-rendered")).toBeInTheDocument();
  });

  it("marks the active toggle for assistive tech (aria-pressed)", () => {
    render(<RenderedPreview path="x.md" content={MD} language="markdown" />);
    const renderedBtn = screen.getByRole("button", { name: /rendered/i });
    const rawBtn = screen.getByRole("button", { name: /raw/i });
    expect(renderedBtn).toHaveAttribute("aria-pressed", "true");
    expect(rawBtn).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(rawBtn);
    expect(rawBtn).toHaveAttribute("aria-pressed", "true");
    expect(renderedBtn).toHaveAttribute("aria-pressed", "false");
  });

  it("renders a .html document inside a sandboxed iframe (no scripts)", () => {
    render(
      <RenderedPreview
        path="report.html"
        content="<h1>Report</h1>"
        language="html"
      />,
    );
    const frame = screen.getByTestId("preview-html-frame") as HTMLIFrameElement;
    expect(frame.tagName).toBe("IFRAME");
    // Sandboxed and script-free (read-only safety).
    expect(frame.getAttribute("sandbox")).toBe("");
    expect(frame.getAttribute("srcdoc")).toContain("<h1>Report</h1>");
  });

  it("does not offer a toggle for a non-renderable code file (stays source)", async () => {
    render(
      <RenderedPreview
        path="server/app.ts"
        content="const x = 1;"
        language="typescript"
      />,
    );
    await waitFor(() =>
      expect(screen.getByTestId("monaco-editor-mock")).toBeInTheDocument(),
    );
    expect(
      screen.queryByRole("button", { name: /rendered/i }),
    ).not.toBeInTheDocument();
    expect(screen.queryByTestId("preview-rendered")).not.toBeInTheDocument();
  });

  it("treats a .md file as renderable even when the language hint is absent", () => {
    render(<RenderedPreview path="NOTES.md" content={MD} language={null} />);
    expect(screen.getByTestId("preview-rendered")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /raw/i })).toBeInTheDocument();
  });
});
