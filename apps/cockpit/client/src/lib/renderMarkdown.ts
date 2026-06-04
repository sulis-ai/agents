// WP-006 — renderMarkdown(src) (FR-08).
//
// A small, dependency-free, SAFE markdown→HTML renderer for the rendered
// preview. No runtime markdown library is added: in a provably-read-only
// app, pulling in an unvetted markdown+sanitiser pair is the larger risk
// (CP-01 — the bespoke approach is the position that must be defended, and
// here it is: a bounded, tested subset over an audited escape boundary).
//
// SAFETY MODEL (the load-bearing invariant):
//   1. EVERY character of source text is HTML-escaped BEFORE any markup is
//      produced. The only `<…>` tags in the output are the ones THIS module
//      emits for the supported subset — never anything the document carried.
//   2. Link hrefs pass a scheme allow-list (http/https/mailto/relative).
//      A `javascript:` (or any other) scheme is dropped, so a link can
//      never become a script vector.
//
// SUPPORTED SUBSET: ATX headings (#..######), paragraphs, unordered +
// ordered lists, fenced code blocks (``` … ```), inline code, bold
// (**…**), italic (*…*), and links ([text](href)). Anything else renders
// as escaped text — legible, never executable.

/** HTML-escape the five significant characters. The audited boundary. */
function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/** Allow only safe link schemes; everything else is dropped (returns ""). */
function safeHref(rawHref: string): string {
  const href = rawHref.trim();
  // Relative / anchor / root-relative links are safe.
  if (/^(#|\/|\.\/|\.\.\/)/.test(href)) return href;
  // Absolute links must use an allow-listed scheme.
  if (/^(https?:|mailto:)/i.test(href)) return href;
  return "";
}

/**
 * Inline markdown → HTML, applied to ALREADY-ESCAPED text. Order matters:
 * inline code first (its contents are taken verbatim, not re-processed),
 * then links, then bold, then italic.
 */
function renderInline(escaped: string): string {
  let out = escaped;

  // Inline code: `…`. The contents are already escaped (the whole line was
  // escaped before this ran), so `<b>` inside backticks shows as text.
  out = out.replace(/`([^`]+)`/g, (_m, code: string) => `<code>${code}</code>`);

  // Links: [text](href). `href` is un-escaped back to test the scheme, then
  // re-escaped for the attribute. A rejected scheme renders the text only.
  out = out.replace(
    /\[([^\]]+)\]\(([^)]+)\)/g,
    (_m, text: string, hrefEscaped: string) => {
      const rawHref = unescapeForSchemeCheck(hrefEscaped);
      const href = safeHref(rawHref);
      if (href === "") return text;
      return `<a href="${escapeHtml(href)}" rel="noopener noreferrer">${text}</a>`;
    },
  );

  // Bold then italic. Bold first so `**x**` is not eaten by the italic rule.
  out = out.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  out = out.replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>");

  return out;
}

/** Reverse the escape just enough to test a link scheme. */
function unescapeForSchemeCheck(s: string): string {
  return s
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'");
}

type ListKind = "ul" | "ol";

/**
 * Render a markdown string to a safe HTML fragment. The output is suitable
 * for assignment as innerHTML because every byte of input passed through
 * escapeHtml() before any tag was produced.
 */
export function renderMarkdown(src: string): string {
  const lines = src.replace(/\r\n/g, "\n").split("\n");
  const html: string[] = [];

  let i = 0;
  let listKind: ListKind | null = null;
  let paragraph: string[] = [];

  const closeList = () => {
    if (listKind) {
      html.push(`</${listKind}>`);
      listKind = null;
    }
  };
  const flushParagraph = () => {
    if (paragraph.length > 0) {
      const text = renderInline(escapeHtml(paragraph.join(" ")));
      html.push(`<p>${text}</p>`);
      paragraph = [];
    }
  };

  while (i < lines.length) {
    // The while-guard keeps `i` in bounds; the `?? ""` satisfies
    // noUncheckedIndexedAccess without changing behaviour.
    const line = lines[i] ?? "";

    // Fenced code block: ``` … ```. Contents are escaped + emitted verbatim
    // (NO inline markdown applied inside a fence).
    const fence = line.match(/^```(.*)$/);
    if (fence) {
      flushParagraph();
      closeList();
      const body: string[] = [];
      i++;
      while (i < lines.length && !/^```/.test(lines[i] ?? "")) {
        body.push(lines[i] ?? "");
        i++;
      }
      i++; // consume the closing fence (if present)
      html.push(`<pre><code>${escapeHtml(body.join("\n"))}</code></pre>`);
      continue;
    }

    // ATX heading: #..###### text
    const heading = line.match(/^(#{1,6})\s+(.*)$/);
    if (heading) {
      flushParagraph();
      closeList();
      const level = heading[1]!.length;
      const text = renderInline(escapeHtml(heading[2]!.trim()));
      html.push(`<h${level}>${text}</h${level}>`);
      i++;
      continue;
    }

    // Unordered list item: -, * or +
    const ul = line.match(/^[-*+]\s+(.*)$/);
    if (ul) {
      flushParagraph();
      if (listKind !== "ul") {
        closeList();
        html.push("<ul>");
        listKind = "ul";
      }
      html.push(`<li>${renderInline(escapeHtml(ul[1]!.trim()))}</li>`);
      i++;
      continue;
    }

    // Ordered list item: 1. text
    const ol = line.match(/^\d+\.\s+(.*)$/);
    if (ol) {
      flushParagraph();
      if (listKind !== "ol") {
        closeList();
        html.push("<ol>");
        listKind = "ol";
      }
      html.push(`<li>${renderInline(escapeHtml(ol[1]!.trim()))}</li>`);
      i++;
      continue;
    }

    // Blank line: paragraph / list separator.
    if (line.trim() === "") {
      flushParagraph();
      closeList();
      i++;
      continue;
    }

    // Otherwise: accumulate into the current paragraph.
    closeList();
    paragraph.push(line.trim());
    i++;
  }

  flushParagraph();
  closeList();
  return html.join("\n");
}
