// WP-P10/P11 — <HowItCameToBeLens /> — the Provenance "How it came to be" lens.
//
// Calls useOrigin(changeId) for the whole change and groups its files by how
// each was made: "⚡ Autonomous (N)" / "💬 Assisted · likely (N)" / "Origin
// unknown (N)". A one-line honesty banner sits at the top ("Origins are
// inferred from timing until changes are stamped"). Light by design
// (progressive disclosure — group + count at the glance, expand a row to see
// its trace): each row is a button that toggles its OriginTrace inline.
//
// The assisted "· likely" group title carries the hedge only while the group's
// rows are inferred (driven by the backend's attribution — never guessed). The
// run-log / conversation jumps are wired via `onSelectView`.
//
// Presentational over the resolved ChangeOriginView; the data-fetch + loading /
// error live in the container that mounts it (the thread's container/
// presentational split).

import { useMemo, useState } from "react";
import type {
  ChangeOriginView,
  FileOrigin,
  Origin,
} from "../../../shared/api-types";
import type { ChangeView } from "./ChangeNav";
import { OriginTrace } from "./OriginTrace";
import {
  BoltIcon,
  ChatBubbleIcon,
  QuestionMarkCircleIcon,
  InfoIcon,
  ChevronDownIcon,
} from "./originIcons";
import styles from "../styles/Origin.module.css";

interface Props {
  view: ChangeOriginView;
  /** Switch the change view for a row's trace jumps. */
  onSelectView?: (view: ChangeView) => void;
}

type Kind = Origin["kind"];

const GROUP_ORDER: Kind[] = ["autonomous", "assisted", "unknown"];

/** A one-line summary for a lens row (kept light — the trace is one click). */
function rowSummary(origin: Origin): string {
  switch (origin.kind) {
    case "autonomous":
      return `${origin.run.workflow ?? "Autonomous run"} · ${origin.run.outcome}`;
    case "assisted":
      return (
        origin.conversation.summary ??
        `Shaped with you in conversation (turn ${origin.conversation.turn}).`
      );
    case "unknown":
      return origin.reason;
  }
}

function lastName(path: string): string {
  const segs = path.split("/").filter((s) => s.length > 0);
  return segs[segs.length - 1] ?? path;
}

function LensRow({
  file,
  onSelectView,
}: {
  file: FileOrigin;
  onSelectView?: (view: ChangeView) => void;
}) {
  const [open, setOpen] = useState(false);
  const { origin } = file;
  return (
    <div className={styles.lensrowwrap}>
      <button
        type="button"
        className={styles.lensrow}
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        data-testid="lens-row"
      >
        <span className={styles.lfn} title={file.path}>
          {lastName(file.path)}
        </span>
        <span className={styles.lsum}>{rowSummary(origin)}</span>
        <ChevronDownIcon className={styles.caret} aria-hidden="true" />
      </button>
      {open && (
        <div className={styles.lensdetail} data-testid="lens-detail">
          <div
            className={`${styles.inner} ${origin.kind === "autonomous" ? styles.autoD : ""}`}
          >
            <OriginTrace
              origin={origin}
              onOpenConversation={
                onSelectView ? () => onSelectView("conversation") : undefined
              }
              onOpenRunLog={
                onSelectView ? () => onSelectView("provenance") : undefined
              }
            />
          </div>
        </div>
      )}
    </div>
  );
}

function Group({
  kind,
  files,
  onSelectView,
}: {
  kind: Kind;
  files: FileOrigin[];
  onSelectView?: (view: ChangeView) => void;
}) {
  if (files.length === 0) return null;

  // The hedge is per-attribution: show "· likely" only while these assisted
  // rows are inferred (driven by the backend flag, never guessed).
  const allInferred = files.every((f) => f.origin.attribution === "inferred");

  const meta = {
    autonomous: {
      cls: styles.auto,
      icon: <BoltIcon />,
      title: "Autonomous",
      sub: "made by runs, no human in the loop",
    },
    assisted: {
      cls: styles.assist,
      icon: <ChatBubbleIcon />,
      title: allInferred ? "Assisted · likely" : "Assisted",
      sub: "shaped with you in a chat session",
    },
    unknown: {
      cls: "",
      icon: <QuestionMarkCircleIcon />,
      title: "Origin unknown",
      sub: "we couldn’t match these to a run or conversation",
    },
  }[kind];

  return (
    <div className={styles.lensgroup} data-testid={`lens-group-${kind}`}>
      <div className={`${styles.grouphead} ${meta.cls}`}>
        <span className={styles.gi} aria-hidden="true">
          {meta.icon}
        </span>
        <div>
          <div className={styles.gt}>{meta.title}</div>
          <div className={styles.gsub}>{meta.sub}</div>
        </div>
        <span className={styles.pill} data-testid={`lens-count-${kind}`}>
          {files.length}
        </span>
      </div>
      {files.map((f) => (
        <LensRow key={f.path} file={f} onSelectView={onSelectView} />
      ))}
    </div>
  );
}

export function HowItCameToBeLens({ view, onSelectView }: Props) {
  const grouped = useMemo(() => {
    const m: Record<Kind, FileOrigin[]> = {
      autonomous: [],
      assisted: [],
      unknown: [],
    };
    for (const f of view.files) m[f.origin.kind].push(f);
    return m;
  }, [view.files]);

  if (view.files.length === 0) {
    return (
      <div className={`${styles.root} ${styles.lens}`} data-testid="origin-lens">
        <div className={styles.empty}>
          No changed files to trace yet — when this change has changes, where
          each came from will appear here.
        </div>
      </div>
    );
  }

  return (
    <div className={`${styles.root} ${styles.lens}`} data-testid="origin-lens">
      <div className={styles.honesty}>
        <InfoIcon aria-hidden="true" />
        <span>
          <b>Origins are inferred from timing</b> until changes are stamped at
          their source. We mark inferred ones “likely”.
        </span>
      </div>
      {GROUP_ORDER.map((kind) => (
        <Group
          key={kind}
          kind={kind}
          files={grouped[kind]}
          onSelectView={onSelectView}
        />
      ))}
    </div>
  );
}
