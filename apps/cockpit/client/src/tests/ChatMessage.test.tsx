// WP-013 — <ChatMessage /> + <AssistantBlock /> tests.
//
// Discriminates by message.kind:
//   - "user" → renders text in a <pre><code> (fidelity-preserving).
//   - "assistant" → renders one <AssistantBlock /> per block.
//   - "system" → renders a <SystemChip />.
//
// And <AssistantBlock /> for "tool-use" is collapsed by default; clicking
// the header expands the body.
//
// References: WP-013 Contract (<ChatMessage>, <AssistantBlock>), ADR-004
// (message + block shapes).

import { describe, it, expect } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { ChatMessage } from "../components/ChatMessage";
import { AssistantBlock } from "../components/AssistantBlock";
import type {
  TranscriptMessage,
  AssistantBlock as AssistantBlockShape,
} from "../../../shared/api-types";

describe("<ChatMessage />", () => {
  it("renders a user message as a code-block (fidelity)", () => {
    const msg: TranscriptMessage = {
      kind: "user",
      uuid: "u1",
      timestamp: "2026-05-26T10:00:00Z",
      text: "fix the login bug\n\n```js\nconst x = 1;\n```",
    };
    render(<ChatMessage message={msg} />);
    const bubble = screen.getByTestId("chat-message-user");
    expect(bubble).toBeInTheDocument();
    // Code-block for fidelity (no markdown parsing in MVP).
    const code = within(bubble).getByText(/fix the login bug/);
    expect(code.tagName.toLowerCase()).toBe("code");
    // The fenced block's literal backticks are preserved.
    expect(code.textContent).toContain("```js");
  });

  it("renders an assistant message with one AssistantBlock per block", () => {
    const msg: TranscriptMessage = {
      kind: "assistant",
      uuid: "a1",
      timestamp: "2026-05-26T10:01:00Z",
      blocks: [
        { kind: "text", text: "Here is the plan." },
        { kind: "tool-use", toolName: "Read", input: { path: "src/foo.ts" } },
        {
          kind: "tool-result",
          toolUseId: "tu_1",
          content: "file contents...",
        },
      ],
    };
    render(<ChatMessage message={msg} />);
    const bubble = screen.getByTestId("chat-message-assistant");
    expect(bubble).toBeInTheDocument();
    // One AssistantBlock per block.
    expect(within(bubble).getAllByTestId(/^assistant-block-/)).toHaveLength(3);
    // The text block is visible (text blocks are not collapsed).
    expect(within(bubble).getByText("Here is the plan.")).toBeInTheDocument();
  });

  it("renders a system message as a SystemChip with its subtype + text", () => {
    const msg: TranscriptMessage = {
      kind: "system",
      uuid: "s1",
      timestamp: "2026-05-26T10:02:00Z",
      subtype: "info",
      text: "Session resumed.",
    };
    render(<ChatMessage message={msg} />);
    const chip = screen.getByTestId("system-chip");
    expect(chip).toBeInTheDocument();
    expect(chip.textContent).toContain("info");
    expect(chip.textContent).toContain("Session resumed.");
  });
});

describe("<AssistantBlock />", () => {
  it("renders a text block as plain text (preserves newlines)", () => {
    const block: AssistantBlockShape = {
      kind: "text",
      text: "line one\nline two",
    };
    render(<AssistantBlock block={block} />);
    const el = screen.getByTestId("assistant-block-text");
    expect(el).toBeInTheDocument();
    // Newlines preserved (white-space: pre-wrap; the literal \n is in the
    // textContent).
    expect(el.textContent).toBe("line one\nline two");
  });

  it("renders a tool-use block collapsed by default and expands on click", () => {
    const block: AssistantBlockShape = {
      kind: "tool-use",
      toolName: "Read",
      input: { path: "src/foo.ts", lines: 10 },
    };
    render(<AssistantBlock block={block} />);
    const wrapper = screen.getByTestId("assistant-block-tool-use");
    expect(wrapper).toBeInTheDocument();
    // Header advertises the tool name.
    expect(wrapper.textContent).toContain("Read");
    // Body (JSON details) is NOT in the DOM by default — collapsed.
    expect(
      screen.queryByTestId("collapsed-block-body"),
    ).not.toBeInTheDocument();

    // Click the header → body appears with the pretty-printed input.
    const header = within(wrapper).getByRole("button");
    fireEvent.click(header);
    const body = screen.getByTestId("collapsed-block-body");
    expect(body.textContent).toContain("src/foo.ts");
    expect(body.textContent).toContain("\"lines\": 10");
  });

  it("renders a tool-result block collapsed by default", () => {
    const block: AssistantBlockShape = {
      kind: "tool-result",
      toolUseId: "tu_1",
      content: "the file contents",
    };
    render(<AssistantBlock block={block} />);
    const wrapper = screen.getByTestId("assistant-block-tool-result");
    expect(wrapper).toBeInTheDocument();
    // The "Result from X" header — tool-result lacks toolName so the
    // header is generic.
    expect(wrapper.textContent).toContain("Result");
    // Body not in DOM by default.
    expect(
      screen.queryByTestId("collapsed-block-body"),
    ).not.toBeInTheDocument();
  });
});
