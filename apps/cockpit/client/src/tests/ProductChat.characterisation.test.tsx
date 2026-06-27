// WP-003 — characterisation test (Fowler / EP-07), now SUPERSEDED.
//
// Before the WP-003 swap this file pinned today's behaviour: the universal
// chat rendered each TranscriptMessage via <ChatMessage> → <AssistantBlock>,
// and an assistant "text" block rendered as PLAIN TEXT (no summary card, no
// markdown). That characterisation was confirmed green against the pre-swap
// code (the Fowler discipline: prove behaviour before changing it).
//
// The swap is now in place — the durable transcript renders <TurnCard>s
// (ADR-001) — so this file records the SUPERSESSION rather than re-asserting
// the retired plain-text contract. The live behaviour is owned by
// ProductChat.turncard.test.tsx. The single assertion below is the regression
// guard that the old plain-text path is gone (the summary card replaced it).
//
// References: WP-003 Definition of Done > Red ("then it is updated/superseded
// by the behaviour test"); ADR-001; TDD §2.1.

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ProductChat } from "../components/ProductChat";
import type { TranscriptMessage } from "../../../shared/api-types";

const TRANSCRIPT: TranscriptMessage[] = [
  {
    kind: "user",
    uuid: "u1",
    timestamp: "2026-06-27T10:00:00Z",
    text: "what did you change?",
  },
  {
    kind: "assistant",
    uuid: "a1",
    timestamp: "2026-06-27T10:00:05Z",
    blocks: [{ kind: "text", text: "I edited the login handler." }],
  },
];

describe("<ProductChat> — characterisation superseded by the TurnCard swap (WP-003)", () => {
  it("no longer renders the agent turn via the plain-text AssistantBlock path", () => {
    render(
      <ProductChat
        messages={TRANSCRIPT}
        provider="pty"
        replyText=""
        isStreaming={false}
      />,
    );

    // The retired plain-text path is gone: the agent turn is a summary card,
    // never a `chat-message-assistant` / `assistant-block-text` block.
    expect(screen.queryByTestId("chat-message-assistant")).not.toBeInTheDocument();
    expect(screen.queryByTestId("assistant-block-text")).not.toBeInTheDocument();
    expect(screen.getByTestId("turn-card")).toBeInTheDocument();
  });
});
