// Chat-redesign (chat-B2 signed contract) — one card per agent turn.
//
// A 2–3 sentence SUMMARY (the generated Haiku summary, with a first-few-
// sentences fallback) is shown by default. The founder can expand TWO things,
// independently:
//   • "Show the full reply" → the agent's complete prose for the turn.
//   • "N steps"             → the recorded steps the agent took.
// Both collapsed by default (CL-02 progressive disclosure); the summary is the
// scannable thing (AI-01). Heroicons throughout.

import { useState } from "react";
import {
  ChevronRightIcon,
  ChevronDownIcon,
  PencilSquareIcon,
  DocumentMagnifyingGlassIcon,
  CommandLineIcon,
  MagnifyingGlassIcon,
  ListBulletIcon,
  CpuChipIcon,
} from "@heroicons/react/20/solid";
import type { TurnItem, StepKind } from "../lib/groupTurns";
import { firstSentences } from "../lib/groupTurns";
import { renderMarkdown, renderInlineMarkdown } from "../lib/renderMarkdown";
import { formatRelativeTime } from "../utils/relativeTime";
import styles from "../styles/Conversation.module.css";

/** Split a summary into its first sentence (bold) and the remainder. */
function splitFirstSentence(text: string): [string, string] {
  const m = text.match(/^(.*?[.!?])(\s+)([\s\S]*)$/);
  if (m) return [m[1]!.trim(), m[3]!.trim()];
  return [text.trim(), ""];
}

const STEP_ICON: Record<StepKind, typeof PencilSquareIcon> = {
  edit: PencilSquareIcon,
  read: DocumentMagnifyingGlassIcon,
  run: CommandLineIcon,
  search: MagnifyingGlassIcon,
  todo: ListBulletIcon,
  other: CpuChipIcon,
};

interface Props {
  turn: TurnItem;
  /** The generated (Haiku) 2–3 sentence summary; falls back to the first
   *  few sentences of the agent's prose while it isn't ready. */
  summary?: string;
  /** True while a clean summary is being generated for this turn (shows a
   *  live "summarising…" cue on top of the fallback). */
  generating?: boolean;
}

export function TurnCard({ turn, summary, generating }: Props) {
  const [stepsOpen, setStepsOpen] = useState(false);
  const [fullOpen, setFullOpen] = useState(false);

  const summaryText =
    (summary && summary.trim()) ||
    firstSentences(turn.said, 3) ||
    "Worked on the change.";
  const [lead, rest] = splitFirstSentence(summaryText);
  const fullText = turn.said.trim();
  // Offer the full reply only when there's more than the summary already shows.
  const hasMore = fullText.length > 0 && fullText !== summaryText.trim();
  const stepCount = turn.steps.length;

  return (
    <article className={styles.turn} data-testid="turn-card">
      <div className={styles.thead}>
        <span className={styles.av} aria-hidden="true" />
        <div className={styles.hl}>
          <div className={styles.summary} data-testid="turn-summary">
            {/* First sentence bold; the remaining sentences render markdown
                (founder request — fixes literal **asterisks**). */}
            <strong className={styles.summaryLead}>{lead}</strong>
            {rest && (
              <span
                className={styles.summaryRest}
                // Safe: renderInlineMarkdown escapes every byte before emitting
                // any tag (see renderMarkdown.ts safety model).
                dangerouslySetInnerHTML={{ __html: ` ${renderInlineMarkdown(rest)}` }}
              />
            )}
          </div>

          {hasMore && (
            <button
              type="button"
              className={styles.fullToggle}
              aria-expanded={fullOpen}
              data-testid="turn-full-toggle"
              onClick={() => setFullOpen((v) => !v)}
            >
              {fullOpen ? (
                <ChevronDownIcon className={styles.fchev} aria-hidden="true" />
              ) : (
                <ChevronRightIcon className={styles.fchev} aria-hidden="true" />
              )}
              {fullOpen ? "Hide the full reply" : "Show the full reply"}
            </button>
          )}
          {fullOpen && hasMore && (
            <div
              className={styles.fullsaid}
              data-testid="turn-full-text"
              // Safe: renderMarkdown escapes every byte before emitting any tag.
              dangerouslySetInnerHTML={{ __html: renderMarkdown(fullText) }}
            />
          )}

          <div className={styles.turnTime}>
            {formatRelativeTime(turn.timestamp)}
            {generating && (
              <span className={styles.summarising} data-testid="turn-summarising">
                <span className={styles.summarisingDot} aria-hidden="true" />
                summarising…
              </span>
            )}
          </div>
        </div>
      </div>

      {stepCount > 0 && (
        <button
          type="button"
          className={styles.stepsToggle}
          aria-expanded={stepsOpen}
          data-testid="turn-steps-toggle"
          onClick={() => setStepsOpen((v) => !v)}
        >
          <span className={styles.n}>
            {stepCount} step{stepCount === 1 ? "" : "s"}
          </span>
          {stepsOpen ? (
            <ChevronDownIcon className={styles.chev} aria-hidden="true" />
          ) : (
            <ChevronRightIcon className={styles.chev} aria-hidden="true" />
          )}
        </button>
      )}

      {stepsOpen && stepCount > 0 && (
        <div className={styles.steps} data-testid="turn-steps">
          {turn.steps.map((step, i) => {
            const Icon = STEP_ICON[step.kind];
            return (
              <div key={i} className={styles.srow}>
                <Icon className={styles.si} aria-hidden="true" />
                {step.label}
                {step.object && <span className={styles.obj}>{step.object}</span>}
              </div>
            );
          })}
        </div>
      )}
    </article>
  );
}
