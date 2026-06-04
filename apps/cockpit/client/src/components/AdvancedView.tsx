// Advanced (operator) view — the operational substrate of a change.
//
// Working directory (reveal in Finder / copy), branch (copy / open on GitHub),
// and the live list of processes linked to this change (reveal folder / stop).
// This is the technical layer the app's meant to have — out of the way for
// non-technical use, one click for an operator. Doubles as the answer to
// "what's actually running, and where?"

import { useState } from "react";
import {
  FolderOpenIcon,
  ClipboardDocumentIcon,
  ArrowTopRightOnSquareIcon,
  CpuChipIcon,
  StopIcon,
} from "@heroicons/react/20/solid";
import type { Change } from "../../../shared/api-types";
import {
  useAdvanced,
  revealPath,
  stopLinkedProcess,
  type LinkedProcess,
} from "../api/useAdvanced";
import styles from "../styles/AdvancedView.module.css";

interface Props {
  change: Change;
}

function copy(text: string) {
  void navigator.clipboard?.writeText(text);
}

const HEALTH_WORD: Record<LinkedProcess["health"], string> = {
  running: "active",
  orphaned: "orphaned",
  defunct: "defunct",
};

export function AdvancedView({ change }: Props) {
  const query = useAdvanced(change.changeId);
  const [stopping, setStopping] = useState<number | null>(null);
  const branchUrl = query.data?.branchUrl ?? null;
  const processes = query.data?.processes ?? [];

  async function onStop(p: LinkedProcess) {
    if (
      !window.confirm(
        `Stop "${p.label}" (process ${p.pid})? This ends that running process.`,
      )
    )
      return;
    setStopping(p.pid);
    await stopLinkedProcess(change.changeId, p.pid);
    setStopping(null);
    void query.refetch();
  }

  return (
    <div className={styles.wrap} data-testid="advanced-view">
      {/* Working directory */}
      <section className={styles.section}>
        <div className={styles.sectionHead}>
          <FolderOpenIcon className={styles.ic} aria-hidden="true" />
          Working directory
        </div>
        <div className={styles.body}>
          <div className={styles.row}>
            <span className={styles.value} title={change.worktreePath}>
              {change.worktreePath}
            </span>
            <div className={styles.actions}>
              <button
                type="button"
                className={`${styles.btn} ${styles.btnPrimary}`}
                data-testid="reveal-worktree"
                onClick={() => void revealPath(change.changeId)}
              >
                <FolderOpenIcon className={styles.ic} aria-hidden="true" />
                Reveal in Finder
              </button>
              <button
                type="button"
                className={styles.btn}
                onClick={() => copy(change.worktreePath)}
              >
                <ClipboardDocumentIcon className={styles.ic} aria-hidden="true" />
                Copy
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Branch */}
      <section className={styles.section}>
        <div className={styles.sectionHead}>Branch</div>
        <div className={styles.body}>
          <div className={styles.row}>
            <span className={styles.value} title={change.branch}>
              {change.branch}
            </span>
            <div className={styles.actions}>
              {branchUrl && (
                <a
                  className={`${styles.btn} ${styles.btnPrimary}`}
                  href={branchUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  data-testid="open-branch-github"
                >
                  <ArrowTopRightOnSquareIcon
                    className={styles.ic}
                    aria-hidden="true"
                  />
                  Open on GitHub
                </a>
              )}
              <button
                type="button"
                className={styles.btn}
                onClick={() => copy(change.branch)}
              >
                <ClipboardDocumentIcon className={styles.ic} aria-hidden="true" />
                Copy
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Linked processes */}
      <section className={styles.section}>
        <div className={styles.sectionHead}>
          <CpuChipIcon className={styles.ic} aria-hidden="true" />
          Linked processes
        </div>
        <div className={styles.body}>
          {processes.length === 0 ? (
            <div className={styles.empty}>
              No running processes are linked to this change right now.
            </div>
          ) : (
            processes.map((p) => (
              <div
                className={styles.proc}
                key={p.pid}
                data-testid="linked-process"
                data-health={p.health}
              >
                <div className={styles.procMain}>
                  <div className={styles.procTop}>
                    <span className={styles.procLabel}>{p.label}</span>
                    <span
                      className={`${styles.badge} ${
                        p.health === "orphaned"
                          ? styles.badgeOrphaned
                          : p.health === "defunct"
                            ? styles.badgeDefunct
                            : styles.badgeRunning
                      }`}
                    >
                      {HEALTH_WORD[p.health]}
                    </span>
                  </div>
                  <div className={styles.procMeta}>
                    PID {p.pid}
                    {p.cwd ? ` · ${p.cwd}` : ""}
                  </div>
                  {p.hint && <div className={styles.procHint}>{p.hint}</div>}
                </div>
                <div className={styles.actions}>
                  {p.cwd && (
                    <button
                      type="button"
                      className={styles.btn}
                      onClick={() => void revealPath(change.changeId, p.cwd!)}
                    >
                      <FolderOpenIcon className={styles.ic} aria-hidden="true" />
                      Reveal folder
                    </button>
                  )}
                  {p.health === "defunct" ? (
                    <span className={styles.clears}>clears itself</span>
                  ) : (
                    <button
                      type="button"
                      className={`${styles.btn} ${styles.btnDanger}`}
                      disabled={stopping === p.pid}
                      onClick={() => void onStop(p)}
                    >
                      <StopIcon className={styles.ic} aria-hidden="true" />
                      {stopping === p.pid ? "Stopping…" : "Stop"}
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
          <p className={styles.note}>
            These are the processes the app can see running for this change — the
            agent session, the preview server, and any background work.
            <strong> Orphaned</strong> means the launcher is gone (likely a
            leftover, safe to stop); <strong>defunct</strong> is a finished
            process that clears itself. Reveal a folder or stop a stray one.
            (Bringing a terminal window to the front isn't something a browser
            can do.)
          </p>
        </div>
      </section>
    </div>
  );
}
