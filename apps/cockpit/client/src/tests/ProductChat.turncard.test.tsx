// WP-003 — behaviour test: the UNIVERSAL chat renders agent turns as summary
// cards with markdown (parity with the in-change chat), via groupTurns() +
// <TurnCard> (ADR-001 reuse; ADR-003 first-sentences fallback summary).
//
// The founder-facing surface is the rendered DOM (TDD §4 — no testing internal
// helpers in isolation). We feed a product transcript whose assistant turn
// carries a heading, a bold word, a list, and a fenced code block, and assert:
//   - the turn renders as `turn-card` (not a raw plain-text block);
//   - a working "show the full reply" toggle reveals `turn-full-text`;
//   - the markdown renders as HTML (<h_>, <li>, <pre><code>) with NO raw `**`
//     or backticks leaking through;
//   - a user message still renders verbatim (spec non-goal: user text unchanged).
//
// This FAILS against the pre-WP-003 plain-text path (it renders the markdown
// literally inside `assistant-block-text`, with no `turn-card`).
//
// References: WP-003 Contract + Definition of Done; ADR-001/003; TDD §2.1/§4.

import { describe, it, expect } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { ProductChat } from "../components/ProductChat";
import type { TranscriptMessage } from "../../../shared/api-types";

// The agent's prose for the turn: a lead sentence (the summary fallback), then
// more content than the first 3 sentences — so the "show the full reply" toggle
// appears — including a heading, a bold word, a list, and a fenced code block.
const SAID = [
  "I added the cancel-subscription flow.",
  "It validates the request first.",
  "Then it refunds any remaining balance.",
  "",
  "## What changed",
  "",
  "I touched the **billing** module and added a guard.",
  "",
  "- validates the subscription id",
  "- refunds the prorated balance",
  "",
  "```ts",
  "export function cancel(id: string) {}",
  "```",
].join("\n");

const TRANSCRIPT: TranscriptMessage[] = [
  {
    kind: "user",
    uuid: "u1",
    timestamp: "2026-06-27T10:00:00Z",
    text: "add a cancel flow with **emphasis** please",
  },
  {
    kind: "assistant",
    uuid: "a1",
    timestamp: "2026-06-27T10:00:05Z",
    blocks: [{ kind: "text", text: SAID }],
  },
];

describe("<ProductChat> — universal TurnCard parity + markdown (WP-003)", () => {
  it("renders the agent turn as a summary card with a working 'show the full reply'", () => {
    render(
      <ProductChat
        messages={TRANSCRIPT}
        provider="pty"
        replyText=""
        isStreaming={false}
      />,
    );

    // The agent turn is a summary card — not the old plain-text block.
    const card = screen.getByTestId("turn-card");
    expect(card).toBeInTheDocument();
    expect(screen.queryByTestId("assistant-block-text")).not.toBeInTheDocument();

    // The progressive-disclosure toggle is present and starts collapsed; the
    // full reply is not in the DOM yet.
    const toggle = screen.getByTestId("turn-full-toggle");
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryByTestId("turn-full-text")).not.toBeInTheDocument();

    // Clicking reveals the full reply.
    fireEvent.click(toggle);
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
    const full = screen.getByTestId("turn-full-text");
    expect(full).toBeInTheDocument();
  });

  it("renders the full reply's markdown as formatted HTML (heading, list, code) — no raw ** or backticks", () => {
    render(
      <ProductChat
        messages={TRANSCRIPT}
        provider="pty"
        replyText=""
        isStreaming={false}
      />,
    );

    fireEvent.click(screen.getByTestId("turn-full-toggle"));
    const full = screen.getByTestId("turn-full-text");

    // Heading → an <h_> element.
    const heading = within(full).getByText("What changed");
    expect(heading.tagName.toLowerCase()).toMatch(/^h[1-6]$/);

    // Bold → a <strong> element.
    const bold = within(full).getByText("billing");
    expect(bold.tagName.toLowerCase()).toBe("strong");

    // List → <li> items.
    const items = full.querySelectorAll("li");
    expect(items.length).toBe(2);
    expect(items[0]!.textContent).toContain("validates the subscription id");

    // Fenced code → a <pre><code> with the verbatim code, no surrounding fence.
    const pre = full.querySelector("pre code");
    expect(pre).not.toBeNull();
    expect(pre!.textContent).toContain("export function cancel(id: string) {}");

    // No raw markdown leaks into the rendered text.
    expect(full.textContent).not.toContain("**");
    expect(full.textContent).not.toContain("```");
    expect(full.textContent).not.toContain("## What changed");
  });

  it("keeps user messages verbatim (spec non-goal: user text unchanged)", () => {
    render(
      <ProductChat
        messages={TRANSCRIPT}
        provider="pty"
        replyText=""
        isStreaming={false}
      />,
    );

    // The user's literal text — including the raw ** — is shown exactly as typed,
    // never markdown-rendered.
    const userBubble = screen.getByTestId("chat-message-user");
    expect(userBubble.textContent).toContain("add a cancel flow with **emphasis** please");
    expect(within(userBubble).queryByText("emphasis")?.tagName.toLowerCase()).not.toBe("strong");
  });

  it("still renders the in-flight streamed reply + caret while streaming", () => {
    render(
      <ProductChat
        messages={TRANSCRIPT}
        provider="pty"
        replyText="thinking it through"
        isStreaming={true}
      />,
    );
    const reply = screen.getByTestId("product-chat-reply");
    expect(reply.textContent).toContain("thinking it through");
    expect(screen.getByTestId("stream-caret")).toBeInTheDocument();
  });
});
