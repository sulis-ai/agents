// Chat-redesign (chat-B2 signed contract) — the change-scoped LEFT NAV.
//
// Inside an open change tab the change owns the screen. This nav carries the
// change's identity (slug kicker + intent name + stage badge + liveness), a
// VERTICAL stage track (Recon → Ship), and the view switches (Conversation /
// Files / Brain / Preview) that swap the main area. Replaces the old
// right-hand rail — one navigation model. Heroicons throughout.

import {
  ChatBubbleLeftRightIcon,
  DocumentTextIcon,
  CubeTransparentIcon,
  EyeIcon,
  Cog6ToothIcon,
} from "@heroicons/react/24/outline";
import type { Change, WorkflowStage } from "../../../shared/api-types";
import { stageLabel } from "./StageBadge";
import styles from "../styles/ChangeWorkspace.module.css";

export type ChangeView =
  | "conversation"
  | "files"
  | "brain"
  | "preview"
  | "advanced";

const TRACK_STAGES: Exclude<WorkflowStage, "shipped">[] = [
  "recon",
  "specify",
  "design",
  "implement",
  "review",
  "ship",
];
const STATE_WORD = { done: "Done", now: "Now", pending: "Pending" } as const;

const VIEWS: { id: ChangeView; label: string; Icon: typeof EyeIcon }[] = [
  { id: "conversation", label: "Conversation", Icon: ChatBubbleLeftRightIcon },
  { id: "files", label: "Files", Icon: DocumentTextIcon },
  { id: "brain", label: "Brain", Icon: CubeTransparentIcon },
  { id: "preview", label: "Preview", Icon: EyeIcon },
  { id: "advanced", label: "Advanced", Icon: Cog6ToothIcon },
];

interface Props {
  change: Change;
  activeView: ChangeView;
  onSelectView: (view: ChangeView) => void;
}

export function ChangeNav({ change, activeView, onSelectView }: Props) {
  const running = change.liveness.status === "running";
  const currentIndex =
    change.stage === "shipped"
      ? TRACK_STAGES.length
      : TRACK_STAGES.indexOf(change.stage as Exclude<WorkflowStage, "shipped">);

  return (
    <nav
      className={styles.leftnav}
      data-testid="change-nav"
      aria-label={`${change.slug} — change navigation`}
    >
      <div className={styles.cnHead}>
        <div className={styles.cnKicker}>
          {change.slug} · {change.primitive}
        </div>
        <div className={styles.cnName}>{change.intent}</div>
        <div className={styles.cnMeta}>
          <span className={styles.stagebadge}>{stageLabel(change.stage)}</span>
          {running && (
            <span className={styles.cnLive}>
              <span className={styles.g} aria-hidden="true" />
              Running
            </span>
          )}
        </div>
      </div>

      <div className={styles.sectionLabel}>Stage</div>
      <ol className={styles.vtrack} aria-label="Change progress">
        {TRACK_STAGES.map((s, i) => {
          const state =
            i < currentIndex ? "done" : i === currentIndex ? "now" : "pending";
          return (
            <li
              key={s}
              className={styles.vstep}
              data-state={state}
              data-stage={s}
              aria-current={state === "now" ? "step" : undefined}
            >
              <span className={styles.vd} aria-hidden="true" />
              {stageLabel(s)}
              <span className={styles.vw}>{STATE_WORD[state]}</span>
            </li>
          );
        })}
      </ol>

      <div className={styles.sectionLabel}>Views</div>
      {VIEWS.map(({ id, label, Icon }) => (
        <button
          key={id}
          type="button"
          role="tab"
          aria-selected={activeView === id}
          data-testid={`view-${id}`}
          className={
            activeView === id
              ? `${styles.navitem} ${styles.navitemActive}`
              : styles.navitem
          }
          onClick={() => onSelectView(id)}
        >
          <Icon className={styles.ic} aria-hidden="true" />
          {label}
        </button>
      ))}

      {running && (
        <div className={styles.leftnavFoot}>
          <span className={styles.g} aria-hidden="true" />
          Agent running in this change
        </div>
      )}
    </nav>
  );
}
