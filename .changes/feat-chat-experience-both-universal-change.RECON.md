# Recon — feat-chat-experience-both-universal-change

Stage 0 completed at: 2026-06-27T10:20:35Z

This marker indicates `/sulis:recon` has run for this change. Stage-inference
uses its existence to distinguish "post-recon" from "pre-spawn stub only".

## What's already here (key findings)

- The cockpit client already ships ONE safe markdown renderer:
  apps/cockpit/client/src/lib/renderMarkdown.ts — renderMarkdown() +
  renderInlineMarkdown(). Dependency-free, HTML-escape-first, scheme
  allow-listed links. Supports: headings, paragraphs, lists, fenced code
  blocks, inline code, bold, italic, links. (EP-03: reuse, do not add a lib.)
- IN-CHANGE chat (Chat.tsx -> TurnCard.tsx) ALREADY renders agent prose via
  renderMarkdown() / renderInlineMarkdown() (dangerouslySetInnerHTML over the
  audited escape boundary).
- UNIVERSAL / product-wide chat (ProductChat.tsx -> ChatMessage.tsx ->
  AssistantBlock.tsx) renders the assistant text block as PLAIN TEXT
  ({block.text}) — does NOT use the shared renderer. This is the gap.
- USER-typed messages are deliberately rendered verbatim in both surfaces
  (ChatMessage user -> <pre><code>; Chat.tsx user -> plain) per the WP-013
  "founder sees exactly what they typed / XSS" note. Whether user messages
  should now render markdown is an open WHAT question for /sulis:specify.

## Arrival check
- RC-02: main does not require branch-ci (standing free-plan limitation;
  branch protection unavailable). Not specific to this work.
