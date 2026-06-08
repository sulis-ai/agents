// WP-006 — renderMarkdown(src) tests (FR-08).
//
// A small, dependency-free, SAFE markdown→HTML renderer for the rendered
// preview. No runtime markdown dependency is introduced (CP-01: the
// bespoke approach is justified here only because the alternative — an
// unvetted client-side markdown+sanitiser pair — is the larger risk in a
// provably-read-only app). The renderer escapes ALL source text before
// emitting any markup, so a document can never inject script/HTML — the
// only tags in the output are the ones this function emits for the
// supported markdown subset (headings, paragraphs, lists, fenced/inline
// code, bold/italic, links).

import { describe, it, expect } from "vitest";
import { renderMarkdown } from "../lib/renderMarkdown";

describe("renderMarkdown (FR-08)", () => {
  it("renders ATX headings", () => {
    expect(renderMarkdown("# Title")).toContain("<h1>Title</h1>");
    expect(renderMarkdown("## Sub")).toContain("<h2>Sub</h2>");
    expect(renderMarkdown("### Deep")).toContain("<h3>Deep</h3>");
  });

  it("renders paragraphs", () => {
    const html = renderMarkdown("Hello world.\n\nSecond para.");
    expect(html).toContain("<p>Hello world.</p>");
    expect(html).toContain("<p>Second para.</p>");
  });

  it("renders unordered lists", () => {
    const html = renderMarkdown("- one\n- two\n- three");
    expect(html).toContain("<ul>");
    expect(html).toContain("<li>one</li>");
    expect(html).toContain("<li>two</li>");
    expect(html).toContain("<li>three</li>");
    expect(html).toContain("</ul>");
  });

  it("renders bold and italic inline", () => {
    expect(renderMarkdown("a **bold** word")).toContain(
      "<strong>bold</strong>",
    );
    expect(renderMarkdown("an *italic* word")).toContain("<em>italic</em>");
  });

  it("renders inline code", () => {
    expect(renderMarkdown("call `readBrain()` now")).toContain(
      "<code>readBrain()</code>",
    );
  });

  it("renders fenced code blocks without interpreting their contents", () => {
    const html = renderMarkdown("```\n# not a heading\n**not bold**\n```");
    expect(html).toContain("<pre>");
    expect(html).toContain("# not a heading");
    // Inside a fence, markdown is NOT applied.
    expect(html).not.toContain("<strong>not bold</strong>");
  });

  it("renders links as anchors", () => {
    const html = renderMarkdown("see [the docs](https://example.com/x)");
    expect(html).toContain('href="https://example.com/x"');
    expect(html).toContain(">the docs</a>");
  });

  it("HTML-escapes raw markup so a document cannot inject script (no XSS)", () => {
    const html = renderMarkdown("<script>alert(1)</script>\n\nplain");
    expect(html).not.toContain("<script>");
    expect(html).toContain("&lt;script&gt;");
  });

  it("does NOT allow a javascript: link to survive as an href", () => {
    const html = renderMarkdown("[x](javascript:alert(1))");
    expect(html).not.toContain('href="javascript:');
  });

  it("escapes angle brackets inside inline code", () => {
    const html = renderMarkdown("`<b>raw</b>`");
    expect(html).toContain("<code>&lt;b&gt;raw&lt;/b&gt;</code>");
    expect(html).not.toContain("<code><b>");
  });
});
