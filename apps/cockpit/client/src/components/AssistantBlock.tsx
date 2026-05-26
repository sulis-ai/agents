// WP-013 — <AssistantBlock /> — discriminates by block.kind.
//
//   - "text" → plain text with white-space: pre-wrap (newlines + code
//     fences preserved; no markdown parsing per WP-013 risk note).
//   - "tool-use" → <CollapsedBlock /> with header "Used <toolName>",
//     body = pretty-printed JSON input. Default collapsed.
//   - "tool-result" → <CollapsedBlock /> with header "Result from tool",
//     body = the result content (stringified if non-string). Default
//     collapsed.

import type { AssistantBlock as AssistantBlockShape } from "../../../shared/api-types";
import { CollapsedBlock } from "./CollapsedBlock";
import styles from "../styles/Chat.module.css";

interface Props {
  block: AssistantBlockShape;
}

export function AssistantBlock({ block }: Props) {
  if (block.kind === "text") {
    return (
      <div className={styles.textBlock} data-testid="assistant-block-text">
        {block.text}
      </div>
    );
  }

  if (block.kind === "tool-use") {
    return (
      <CollapsedBlock
        wrapperTestId="assistant-block-tool-use"
        header={
          <span>
            Used <strong>{block.toolName}</strong>
          </span>
        }
      >
        <pre className={styles.collapsedJson}>
          <code>{prettyJson(block.input)}</code>
        </pre>
      </CollapsedBlock>
    );
  }

  // tool-result
  return (
    <CollapsedBlock
      wrapperTestId="assistant-block-tool-result"
      header={<span>Result from tool</span>}
    >
      <pre className={styles.collapsedJson}>
        <code>{stringifyResult(block.content)}</code>
      </pre>
    </CollapsedBlock>
  );
}

function prettyJson(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function stringifyResult(value: unknown): string {
  if (typeof value === "string") return value;
  return prettyJson(value);
}
