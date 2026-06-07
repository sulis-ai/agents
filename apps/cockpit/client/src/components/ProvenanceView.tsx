// WP-P06 — <ProvenanceView /> — "what Sulis did, and why" (signed
// `provenance-prototype.html`).
//
// The dashboard front door (four plain-English digest tiles + two
// door-buttons + a quiet "Browse everything" link), opening into two lenses —
// the run log (runs → steps → step detail) and the coverage map (Why/What/
// How/Tested columns, a filterable requirements list, and a per-requirement
// focused trace). "Browse everything" falls back to the flat grouped
// <BrainView> so nothing is lost.
//
// Presentational: takes a `ProvenanceView` prop plus a `focusFor` resolver for
// the coverage drill-in (the data-fetch lives in <ProvenanceSection>), exactly
// like the rest of the thread's container/presentational split. Progressive
// disclosure (dashboard → lens → detail), always a way back (CL-04/05). Worded
// status never colour-alone. Consumes tokens.css only — no raw hex in rules.

import { useMemo, useState } from "react";
import type {
  CoverageColumn,
  FocusedTrace,
  ProvenanceView as ProvenanceModel,
  RunLogEntry,
  RunStep,
} from "../../../shared/api-types";
import type {
  BrainView as BrainViewModel,
  ChangeOriginView,
} from "../../../shared/api-types";
import { BrainView } from "./BrainView";
import { HowItCameToBeLens } from "./HowItCameToBeLens";
import type { ChangeView } from "./ChangeNav";
import styles from "../styles/ProvenanceView.module.css";
import {
  ArrowLeftIcon,
  ArrowRightIcon,
  BeakerIcon,
  BeakerOutline,
  BoltIcon,
  BoltOutline,
  BulbIcon,
  CheckIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  ClipboardOutline,
  CloseIcon,
  CubeOutline,
  CubeStackOutline,
  DocIcon,
  EyeIcon,
  InfoIcon,
  LightbulbOutline,
  PencilIcon,
  ScaleIcon,
  SearchIcon,
  ShieldCheckIcon,
  SparkleSealIcon,
  StackIcon,
  TriangleExclaimIcon,
} from "./provenanceIcons";

type Lens = "dashboard" | "runlog" | "coverage" | "origin" | "browse";

/** The focused-trace query state for the currently-selected requirement. */
export interface FocusState {
  trace: FocusedTrace | undefined;
  isLoading: boolean;
  isError: boolean;
}

interface Props {
  view: ProvenanceModel;
  /** The currently-selected requirement id (coverage lens B), lifted so the
   *  data container can run the `?focus=` query. null = nothing selected. */
  focusId: string | null;
  /** Notifies the container which requirement to fetch a trace for. */
  onFocus: (requirementId: string | null) => void;
  /** The focused-trace query for `focusId` (resolved by the container). */
  focus: FocusState;
  /** The flat grouped brain — the "Browse everything" fallback. Optional:
   *  when absent the browse link is hidden (still a dashboard front door). */
  brain?: BrainViewModel;
  /** The whole-change origin list — the "How it came to be" lens (WP-P10/P11).
   *  Optional: when absent the lens door is hidden. */
  origin?: ChangeOriginView;
  /** Switch the change view (for the lens's "Open conversation" jump). */
  onSelectView?: (view: ChangeView) => void;
}

/* Is there anything at all to show? (empty-state guard) */
function isEmpty(view: ProvenanceModel): boolean {
  const d = view.digest;
  const noDigest =
    d.did === 0 &&
    d.decided === 0 &&
    d.covered.total === 0 &&
    d.flagged.count === 0;
  return noDigest && view.runLog.length === 0 && view.coverage.length === 0;
}

export function ProvenanceView({
  view,
  focusId,
  onFocus,
  focus,
  brain,
  origin,
  onSelectView,
}: Props) {
  const [lens, setLens] = useState<Lens>("dashboard");

  if (isEmpty(view)) {
    return (
      <div className={styles.root} data-testid="provenance">
        <div className={styles.emptyState} data-testid="provenance-empty">
          <span className={styles.eglyph} aria-hidden="true">
            <SparkleSealIcon />
          </span>
          <div className={styles.et}>No provenance yet</div>
          <div className={styles.es}>
            Sulis hasn&rsquo;t worked this change. When it runs, what it did and
            why will appear here.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.root} data-testid="provenance" data-lens={lens}>
      {lens === "dashboard" && (
        <Dashboard
          view={view}
          hasBrain={brain !== undefined}
          hasOrigin={origin !== undefined}
          onOpenRunLog={() => setLens("runlog")}
          onOpenCoverage={() => setLens("coverage")}
          onOpenOrigin={() => setLens("origin")}
          onBrowse={() => setLens("browse")}
        />
      )}
      {lens === "runlog" && (
        <RunLogLens
          view={view}
          onBack={() => setLens("dashboard")}
          onLens={setLens}
        />
      )}
      {lens === "coverage" && (
        <CoverageLens
          view={view}
          focusId={focusId}
          onFocus={onFocus}
          focus={focus}
          onBack={() => setLens("dashboard")}
          onLens={setLens}
        />
      )}
      {lens === "origin" && (
        <section className={styles.root} aria-label="How it came to be">
          <header className={styles.bhead}>
            <button
              type="button"
              className={styles.backbtn}
              onClick={() => setLens("dashboard")}
              data-testid="provenance-back"
            >
              <ArrowLeftIcon />
              Provenance
            </button>
            <div className={styles.htxt}>
              <div className={styles.ttl}>How it came to be</div>
              <div className={styles.sub}>
                The same changes, grouped by how each one was made.
              </div>
            </div>
          </header>
          <div className={styles.scroll}>
            <div className={styles.wrap}>
              {origin ? (
                <HowItCameToBeLens view={origin} onSelectView={onSelectView} />
              ) : (
                <p className={styles.statusline}>
                  Nothing to trace yet — origins will appear once this change has
                  changes.
                </p>
              )}
            </div>
          </div>
        </section>
      )}
      {lens === "browse" && (
        <section className={styles.root} aria-label="Browse everything">
          <header className={styles.bhead}>
            <button
              type="button"
              className={styles.backbtn}
              onClick={() => setLens("dashboard")}
              data-testid="provenance-back"
            >
              <ArrowLeftIcon />
              Provenance
            </button>
            <div className={styles.htxt}>
              <div className={styles.ttl}>Browse everything</div>
              <div className={styles.sub}>
                Every building block Sulis created on this change, grouped by
                kind.
              </div>
            </div>
          </header>
          <div className={styles.scroll}>
            {brain ? (
              <BrainView view={brain} />
            ) : (
              <p className={styles.statusline}>Nothing else to browse yet.</p>
            )}
          </div>
        </section>
      )}
    </div>
  );
}

/* ───────────────────────── DASHBOARD ───────────────────────── */

function pct(n: number | null | undefined): string | null {
  if (n === null || n === undefined) return null;
  // confidence may arrive 0–1 or 0–100; normalise to a whole percent.
  const v = n <= 1 ? Math.round(n * 100) : Math.round(n);
  return `${v}%`;
}

/** Overall confidence = the newest run that carries one (runLog is newest-first). */
function overallConfidence(runLog: RunLogEntry[]): string | null {
  for (const r of runLog) {
    const p = pct(r.confidence);
    if (p) return p;
  }
  return null;
}

function Dashboard({
  view,
  hasBrain,
  hasOrigin,
  onOpenRunLog,
  onOpenCoverage,
  onOpenOrigin,
  onBrowse,
}: {
  view: ProvenanceModel;
  hasBrain: boolean;
  hasOrigin: boolean;
  onOpenRunLog: () => void;
  onOpenCoverage: () => void;
  onOpenOrigin: () => void;
  onBrowse: () => void;
}) {
  const { digest } = view;
  const [decOpen, setDecOpen] = useState(false);
  const conf = overallConfidence(view.runLog);
  const completed = view.runLog.filter((r) =>
    /complete|done|pass/i.test(r.outcome),
  ).length;
  const browseCount = view.runLog.length + digest.decided + digest.covered.total;

  const flaggedSomething = digest.flagged.count > 0;

  return (
    <div className={styles.scroll} data-testid="provenance-dashboard">
      <div className={styles.wrap}>
        <div className={styles.dhead}>
          <div className={styles.htxt}>
            <div className={styles.ttl}>Provenance — what Sulis did, and why</div>
            <div className={styles.sub}>
              A plain-English read on what the agent has done — start here, go
              deeper when you want.
            </div>
          </div>
          {conf && (
            <span className={styles.conf} data-testid="provenance-confidence">
              <SparkleSealIcon />
              {conf} confident overall
            </span>
          )}
        </div>

        <div className={styles.tiles}>
          {/* What it did */}
          <div className={`${styles.tile} ${styles.did}`} data-testid="tile-did">
            <div className={styles.th}>
              <span className={styles.ti} aria-hidden="true">
                <BoltIcon />
              </span>
              <span className={styles.tl}>What it did</span>
            </div>
            <div className={styles.big}>
              {digest.did === 0
                ? "Nothing run yet"
                : `Ran ${digest.did} ${digest.did === 1 ? "time" : "times"}, end to end`}
            </div>
            <div className={styles.body}>
              {digest.did === 0
                ? "No autonomous runs have completed on this change yet."
                : `${completed === digest.did ? "All completed" : `${completed} of ${digest.did} completed`}${conf ? ` · ${conf} confident` : ""}. Open the run log to walk each one.`}
            </div>
          </div>

          {/* What it covered → coverage map */}
          <button
            type="button"
            className={`${styles.tile} ${styles.cov} ${styles.clickable}`}
            onClick={onOpenCoverage}
            data-testid="tile-covered"
            aria-label="What it covered — open the coverage map"
          >
            <div className={styles.th}>
              <span className={styles.ti} aria-hidden="true">
                <CheckIcon />
              </span>
              <span className={styles.tl}>What it covered</span>
              <span className={styles.chev} aria-hidden="true">
                <ChevronRightIcon />
              </span>
            </div>
            <div className={styles.big}>
              {digest.covered.total} requirements written ·{" "}
              {digest.covered.verified} proven by a test
            </div>
            <div className={styles.body}>
              {digest.covered.total - digest.covered.verified} still awaiting a
              test. Open the coverage map to trace any one.
            </div>
          </button>

          {/* What it decided → expand inline */}
          <button
            type="button"
            className={`${styles.tile} ${styles.dec} ${styles.clickable}`}
            onClick={() => setDecOpen((o) => !o)}
            aria-expanded={decOpen}
            data-testid="tile-decided"
            aria-label="What it decided"
          >
            <div className={styles.th}>
              <span className={styles.ti} aria-hidden="true">
                <ScaleIcon />
              </span>
              <span className={styles.tl}>What it decided</span>
              <span
                className={styles.chev}
                aria-hidden="true"
                style={{
                  transform: decOpen ? "rotate(180deg)" : undefined,
                  transition: "transform .15s ease",
                }}
              >
                <ChevronDownIcon />
              </span>
            </div>
            <div className={styles.big}>
              {digest.decided === 0
                ? "No decisions recorded"
                : `${digest.decided} ${digest.decided === 1 ? "call" : "calls"} along the way`}
            </div>
            <div className={styles.body}>
              {digest.decided === 0
                ? "Sulis hasn't recorded a decision on this change yet."
                : "The choices Sulis made and recorded as it worked."}
            </div>
            {decOpen && digest.decided > 0 && (
              <div className={styles.declist} data-testid="decided-list">
                {decisionEntities(view.coverage).map((d) => (
                  <div className={styles.decrow} key={d.id}>
                    <span className={styles.dn} aria-hidden="true">
                      <ScaleIcon />
                    </span>
                    <div>
                      <b>{d.title}</b>
                    </div>
                  </div>
                ))}
                {decisionEntities(view.coverage).length === 0 && (
                  <div className={styles.decrow}>
                    Recorded {digest.decided} — open the coverage map&rsquo;s
                    &ldquo;How&rdquo; column to read them.
                  </div>
                )}
              </div>
            )}
          </button>

          {/* What it flagged — the trust tile */}
          <div
            className={`${styles.tile} ${styles.flag}`}
            data-testid="tile-flagged"
          >
            <div className={styles.th}>
              <span className={styles.ti} aria-hidden="true">
                <TriangleExclaimIcon />
              </span>
              <span className={styles.tl}>What it flagged</span>
            </div>
            <div className={styles.big}>
              {flaggedSomething
                ? (digest.flagged.topGap ?? "A gap to close before ship")
                : "Nothing flagged"}
            </div>
            <div className={styles.body}>
              {flaggedSomething
                ? `${digest.flagged.count} ${digest.flagged.count === 1 ? "gap" : "gaps"} the agent surfaced for you. Open the run log to see ${digest.flagged.count === 1 ? "it" : "them"} in context.`
                : "Sulis didn't flag any gaps on this change."}
            </div>
            {digest.flagged.selfCritique && (
              <div className={styles.crit}>
                <p>&ldquo;{digest.flagged.selfCritique}&rdquo;</p>
                <div className={styles.by}>The agent&rsquo;s own note</div>
              </div>
            )}
          </div>
        </div>

        <div className={styles.doors}>
          <button
            type="button"
            className={styles.door}
            onClick={onOpenRunLog}
            data-testid="door-runlog"
          >
            <span className={styles.di} aria-hidden="true">
              <BoltOutline strokeWidth={1.7} />
            </span>
            <span className={styles.dt}>
              <span className={styles.dn}>See the run log</span>
              <span className={styles.dd}>
                Walk each run, step by step, with what it produced
              </span>
            </span>
            <span className={styles.arrow} aria-hidden="true">
              <ArrowRightIcon />
            </span>
          </button>
          <button
            type="button"
            className={styles.door}
            onClick={onOpenCoverage}
            data-testid="door-coverage"
          >
            <span className={styles.di} aria-hidden="true">
              <CubeOutline strokeWidth={1.7} />
            </span>
            <span className={styles.dt}>
              <span className={styles.dn}>See the coverage map</span>
              <span className={styles.dd}>
                Trace any requirement to its reason, design and test
              </span>
            </span>
            <span className={styles.arrow} aria-hidden="true">
              <ArrowRightIcon />
            </span>
          </button>
          {hasOrigin && (
            <button
              type="button"
              className={styles.door}
              onClick={onOpenOrigin}
              data-testid="door-origin"
            >
              <span className={styles.di} aria-hidden="true">
                <BoltOutline strokeWidth={1.7} />
              </span>
              <span className={styles.dt}>
                <span className={styles.dn}>How it came to be</span>
                <span className={styles.dd}>
                  See where each changed file came from — autonomous, assisted,
                  or unknown
                </span>
              </span>
              <span className={styles.arrow} aria-hidden="true">
                <ArrowRightIcon />
              </span>
            </button>
          )}
        </div>

        {hasBrain && (
          <button
            type="button"
            className={styles.browse}
            onClick={onBrowse}
            data-testid="link-browse"
          >
            <StackIcon />
            Browse everything <span className={styles.ct}>{browseCount} items</span>
          </button>
        )}
      </div>
    </div>
  );
}

/** Pull the recorded decisions out of the coverage "how" column. */
function decisionEntities(
  coverage: CoverageColumn[],
): { id: string; title: string }[] {
  const how = coverage.find((c) => c.axis === "how");
  if (!how || how.axis !== "how") return [];
  return how.items.filter((i) => i.kind === "decision");
}

/* ───────────────────────── lens header ───────────────────────── */

function LensHeader({
  title,
  sub,
  active,
  onBack,
  onLens,
}: {
  title: string;
  sub: string;
  active: "runlog" | "coverage";
  onBack: () => void;
  onLens: (l: Lens) => void;
}) {
  return (
    <header className={styles.bhead}>
      <button
        type="button"
        className={styles.backbtn}
        onClick={onBack}
        data-testid="provenance-back"
      >
        <ArrowLeftIcon />
        Provenance
      </button>
      <div className={styles.htxt}>
        <div className={styles.ttl}>{title}</div>
        <div className={styles.sub}>{sub}</div>
      </div>
      <div className={styles.lens} role="group" aria-label="Choose a view">
        <button
          type="button"
          aria-pressed={active === "runlog"}
          onClick={() => onLens("runlog")}
          data-testid="lens-runlog"
        >
          <BoltOutline strokeWidth={1.7} />
          Run log
        </button>
        <button
          type="button"
          aria-pressed={active === "coverage"}
          onClick={() => onLens("coverage")}
          data-testid="lens-coverage"
        >
          <CubeOutline strokeWidth={1.7} />
          Coverage map
        </button>
      </div>
    </header>
  );
}

/* ───────────────────────── RUN LOG LENS ───────────────────────── */

function RunLogLens({
  view,
  onBack,
  onLens,
}: {
  view: ProvenanceModel;
  onBack: () => void;
  onLens: (l: Lens) => void;
}) {
  const [openRunId, setOpenRunId] = useState<string | null>(
    view.runLog[0]?.runId ?? null,
  );
  const [selected, setSelected] = useState<{
    runId: string;
    index: number;
  } | null>(null);

  const selectedStep: RunStep | null = useMemo(() => {
    if (!selected) return null;
    const run = view.runLog.find((r) => r.runId === selected.runId);
    return run?.steps[selected.index] ?? null;
  }, [selected, view.runLog]);

  return (
    <section className={styles.root} aria-label="Run log">
      <LensHeader
        title="The run log"
        sub="Everything the agent did on this change — and how it got there."
        active="runlog"
        onBack={onBack}
        onLens={onLens}
      />
      <div className={styles.rlbody}>
        <div className={styles.timeline} aria-label="Run timeline">
          <div className={styles.tlLabel}>The agent&rsquo;s runs · newest first</div>
          {view.runLog.length === 0 ? (
            <p className={styles.statusline} data-testid="runlog-empty">
              No runs recorded yet.
            </p>
          ) : (
            <div className={styles.runline}>
              {view.runLog.map((run) => {
                const isVerify = /verify|review/i.test(
                  run.workflow ?? run.stepName,
                );
                const isOpen = openRunId === run.runId;
                return (
                  <div
                    className={`${styles.run} ${isVerify ? styles.verify : ""}`}
                    key={run.runId}
                    data-testid="run-card"
                  >
                    <span className={styles.node} aria-hidden="true">
                      {isVerify ? <ShieldCheckIcon /> : <BoltIcon />}
                    </span>
                    <div className={`${styles.card} ${isOpen ? styles.open : ""}`}>
                      <button
                        type="button"
                        className={styles.runtop}
                        aria-expanded={isOpen}
                        onClick={() =>
                          setOpenRunId(isOpen ? null : run.runId)
                        }
                        data-testid="run-toggle"
                      >
                        <div className={styles.rt}>
                          <div className={styles.nm}>
                            {run.workflow ?? run.stepName}
                          </div>
                          <div className={styles.meta}>
                            run · {runWhen(run.at)} · {run.steps.length} steps
                          </div>
                          {run.finalVerdict && (
                            <div className={styles.out}>{run.finalVerdict}</div>
                          )}
                          <div className={styles.chips}>
                            <span className={`${styles.chip} ${styles.done}`}>
                              <CheckIcon />
                              {capitalise(run.outcome)}
                            </span>
                            {pct(run.confidence) && (
                              <span className={`${styles.chip} ${styles.conf}`}>
                                {pct(run.confidence)} confident
                              </span>
                            )}
                            <span className={`${styles.chip} ${styles.count}`}>
                              {run.steps.length} steps
                            </span>
                          </div>
                        </div>
                        <span className={styles.exp} aria-hidden="true">
                          <ChevronDownIcon />
                        </span>
                      </button>
                      {isOpen && (
                        <div className={styles.steplist} role="list">
                          {run.steps.map((step, i) => {
                            const isGap = step.gap !== null;
                            const isSel =
                              selected?.runId === run.runId &&
                              selected.index === i;
                            return (
                              <button
                                type="button"
                                role="listitem"
                                className={`${styles.stepitem} ${isSel ? styles.sel : ""}`}
                                key={`${run.runId}-${i}`}
                                aria-current={isSel ? "true" : undefined}
                                onClick={() =>
                                  setSelected({ runId: run.runId, index: i })
                                }
                                data-testid="step-item"
                              >
                                <span className={styles.sn}>{i + 1}</span>
                                <span className={styles.si} aria-hidden="true">
                                  <DocIcon />
                                </span>
                                <span className={styles.stx}>{step.step}</span>
                                <span
                                  className={`${styles.sok} ${isGap ? styles.gap : ""}`}
                                >
                                  {isGap ? (
                                    <TriangleExclaimIcon />
                                  ) : (
                                    <CheckIcon />
                                  )}
                                  {isGap ? "flagged" : "done"}
                                </span>
                              </button>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <aside className={styles.rail} aria-label="Step detail">
          {selectedStep ? (
            <div data-testid="step-detail">
              <div className={styles.rlKicker}>
                <InfoIcon />
                <span>Step detail</span>
              </div>
              <div className={styles.rlTtl}>{selectedStep.step}</div>
              <div className={styles.rlMeta}>outcome: {selectedStep.outcome}</div>
              {selectedStep.detail && (
                <div className={styles.rlSec}>
                  <h4>
                    <PencilIcon />
                    What it produced
                  </h4>
                  <p>{selectedStep.detail}</p>
                </div>
              )}
              {selectedStep.gap && (
                <div className={styles.rlSec}>
                  <h4>
                    <TriangleExclaimIcon />
                    Gap it flagged
                  </h4>
                  <div className={styles.gapbox}>
                    <div className={styles.gh}>
                      <TriangleExclaimIcon />
                      Flagged gap
                    </div>
                    <p>{selectedStep.gap}</p>
                  </div>
                </div>
              )}
              {selectedStep.selfCritique && (
                <div className={styles.rlSec}>
                  <h4>
                    <InfoIcon />
                    Its self-critique
                  </h4>
                  <div className={styles.selfcrit}>
                    <p>&ldquo;{selectedStep.selfCritique}&rdquo;</p>
                    <div className={styles.by}>
                      <InfoIcon />
                      the agent, in its own words
                    </div>
                  </div>
                </div>
              )}
              {!selectedStep.detail &&
                !selectedStep.gap &&
                !selectedStep.selfCritique && (
                  <div className={styles.rlSec}>
                    <p>This step completed with no extra detail recorded.</p>
                  </div>
                )}
            </div>
          ) : (
            <div className={styles.railempty} data-testid="rail-empty">
              <span className={styles.reglyph} aria-hidden="true">
                <BeakerIcon />
              </span>
              <div className={styles.ret}>Pick a step to see its detail</div>
              <div className={styles.res}>
                Expand a run, then click any step — its detail fills here: what
                it produced, any gap, and the agent&rsquo;s own note.
              </div>
            </div>
          )}
        </aside>
      </div>
    </section>
  );
}

function runWhen(at: string): string {
  const t = new Date(at);
  if (Number.isNaN(t.getTime())) return at;
  return t.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}
function capitalise(s: string): string {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
}

/* ───────────────────────── COVERAGE LENS ───────────────────────── */

function CoverageLens({
  view,
  focusId,
  onFocus,
  focus,
  onBack,
  onLens,
}: {
  view: ProvenanceModel;
  focusId: string | null;
  onFocus: (id: string | null) => void;
  focus: FocusState;
  onBack: () => void;
  onLens: (l: Lens) => void;
}) {
  const [filter, setFilter] = useState("");

  const why = view.coverage.find((c) => c.axis === "why");
  const what = view.coverage.find((c) => c.axis === "what");
  const how = view.coverage.find((c) => c.axis === "how");
  const tested = view.coverage.find((c) => c.axis === "tested");

  const focused = focusId ? focus : null;
  const focusedTitle =
    what?.axis === "what"
      ? (what.items.find((i) => i.id === focusId)?.title ?? null)
      : null;

  const whatItems = what?.axis === "what" ? what.items : [];
  const q = filter.trim().toLowerCase();
  const filtered = whatItems.filter(
    (i) => q === "" || i.title.toLowerCase().includes(q),
  );

  return (
    <section className={styles.root} aria-label="Coverage map">
      <LensHeader
        title="The coverage map"
        sub="Is every requirement reasoned, designed and tested? Trace any one."
        active="coverage"
        onBack={onBack}
        onLens={onLens}
      />
      <div className={styles.bbody}>
        <div className={styles.cols}>
          {/* WHY */}
          <section className={`${styles.col} ${styles.why}`} aria-label="Why — opportunities">
            <div className={styles.colHead}>
              <LightbulbOutline className={styles.ci} />
              <div>
                <div className={styles.step}>Why</div>
                <div className={styles.ttl2}>Opportunities</div>
              </div>
              <span className={styles.pill}>
                {why?.axis === "why" ? why.items.length : 0}
              </span>
            </div>
            <div className={styles.collist}>
              {why?.axis === "why" &&
                why.items.map((it) => (
                  <button type="button" className={styles.entity} key={it.id}>
                    <BulbIcon className={styles.ei} />
                    <div className={styles.etx}>
                      <div className={styles.en}>{it.title}</div>
                      <div className={styles.em}>opportunity</div>
                    </div>
                  </button>
                ))}
            </div>
          </section>

          {/* WHAT — the searchable requirements column */}
          <section className={`${styles.col} ${styles.what}`} aria-label="What — requirements">
            <div className={styles.colHead}>
              <ClipboardOutline className={styles.ci} />
              <div>
                <div className={styles.step}>What</div>
                <div className={styles.ttl2}>Requirements</div>
              </div>
              <span className={styles.pill}>{whatItems.length}</span>
            </div>
            <div className={styles.searchwrap}>
              <div className={styles.searchbox}>
                <SearchIcon />
                <input
                  type="search"
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                  placeholder="Filter the requirements…"
                  aria-label="Filter requirements"
                  data-testid="req-filter"
                />
              </div>
            </div>
            <div className={styles.collist} data-testid="req-list">
              {filtered.map((it) => {
                const verified =
                  what?.axis === "what" &&
                  (what.items.find((x) => x.id === it.id)?.verified ?? false);
                const isSel = focusId === it.id;
                return (
                  <button
                    type="button"
                    className={`${styles.entity} ${isSel ? styles.sel : ""}`}
                    key={it.id}
                    aria-current={isSel ? "true" : undefined}
                    onClick={() => onFocus(it.id)}
                    data-testid="req-item"
                  >
                    <DocIcon className={styles.ei} />
                    <div className={styles.etx}>
                      <div className={styles.en}>{it.title}</div>
                      <div className={styles.em}>requirement</div>
                    </div>
                    <span
                      className={`${styles.wstat} ${verified ? styles.ok : styles.wait}`}
                    >
                      {verified ? "Tested" : "Awaiting test"}
                    </span>
                  </button>
                );
              })}
              {filtered.length === 0 && (
                <div className={styles.noresults} data-testid="req-none">
                  {whatItems.length === 0
                    ? "No requirements recorded yet."
                    : "No requirements match that filter."}
                </div>
              )}
            </div>
          </section>

          {/* HOW */}
          <section className={`${styles.col} ${styles.how}`} aria-label="How — designs and decisions">
            <div className={styles.colHead}>
              <CubeStackOutline className={styles.ci} />
              <div>
                <div className={styles.step}>How</div>
                <div className={styles.ttl2}>Designs &amp; decisions</div>
              </div>
              <span className={styles.pill}>
                {how?.axis === "how" ? how.items.length : 0}
              </span>
            </div>
            <div className={styles.collist}>
              {how?.axis === "how" &&
                how.items.map((it) => (
                  <button type="button" className={styles.entity} key={it.id}>
                    {it.kind === "design" ? (
                      <PencilIcon className={`${styles.ei} ${styles.des}`} />
                    ) : (
                      <ScaleIcon className={`${styles.ei} ${styles.dec}`} />
                    )}
                    <div className={styles.etx}>
                      <div className={styles.en}>{it.title}</div>
                      <div className={styles.em}>{it.kind}</div>
                    </div>
                  </button>
                ))}
            </div>
          </section>

          {/* TESTED */}
          <section className={`${styles.col} ${styles.tested}`} aria-label="Tested — scenarios and results">
            <div className={styles.colHead}>
              <BeakerOutline className={styles.ci} />
              <div>
                <div className={styles.step}>Tested</div>
                <div className={styles.ttl2}>Scenarios &amp; results</div>
              </div>
              <span className={styles.pill}>
                {tested?.axis === "tested" ? tested.items.length : 0}
              </span>
            </div>
            <div className={styles.collist}>
              {tested?.axis === "tested" &&
                tested.items.map((it) => (
                  <button type="button" className={styles.entity} key={it.id}>
                    <BeakerIcon className={styles.ei} />
                    <div className={styles.etx}>
                      <div className={styles.en}>{it.title}</div>
                      <div className={styles.em}>
                        {it.kind === "testresult" ? "test result" : "scenario"}
                      </div>
                    </div>
                    <span className={`${styles.wstat} ${outcomeClass(it.outcome, styles)}`}>
                      {outcomeWord(it.outcome)}
                    </span>
                  </button>
                ))}
            </div>
          </section>
        </div>

        {/* FOCUSED TRACE */}
        <div
          className={styles.focus}
          aria-label="Focused trace for the selected requirement"
          data-testid="focus-trace"
        >
          <div className={styles.focusHead}>
            <EyeIcon />
            <span className={styles.fl}>In focus</span>
            <span className={styles.fn}>
              {focusedTitle ?? "Pick a requirement to trace it"}
            </span>
            {focusId && (
              <button
                type="button"
                className={styles.close}
                onClick={() => onFocus(null)}
                aria-label="Clear focus"
                data-testid="focus-close"
              >
                <CloseIcon />
              </button>
            )}
          </div>
          {!focusId && (
            <div className={styles.focushint}>
              Click any requirement in the <b>What</b> column above and its
              trace — reason, design + decision, and test — appears here.
            </div>
          )}
          {focusId && focused?.isLoading && (
            <div className={styles.focusloading} data-testid="focus-loading">
              Tracing this requirement…
            </div>
          )}
          {focusId && focused?.isError && (
            <div className={styles.focusloading} role="alert">
              Couldn&rsquo;t load this requirement&rsquo;s trace.
            </div>
          )}
          {focusId && focused?.trace && (
            <FocusedTraceView title={focusedTitle} trace={focused.trace} />
          )}
        </div>
      </div>
    </section>
  );
}

function outcomeWord(o: "pass" | "skip" | "fail"): string {
  return o === "pass" ? "Passed" : o === "fail" ? "Failed" : "Not run";
}
function outcomeClass(
  o: "pass" | "skip" | "fail",
  s: Record<string, string>,
): string {
  return (o === "pass" ? s.ok : o === "fail" ? s.fail : s.skip) ?? "";
}

function FocusedTraceView({
  title,
  trace,
}: {
  title: string | null;
  trace: FocusedTrace;
}) {
  const why = trace.why[0];
  const design = trace.how.find((h) => h.kind === "design") ?? trace.how[0];
  const test = trace.tested[0];
  const statClass = test
    ? test.outcome === "pass"
      ? styles.ok
      : test.outcome === "fail"
        ? styles.fail
        : styles.skip
    : styles.skip;

  return (
    <div className={styles.trace} data-testid="focus-trace-body">
      <div className={`${styles.tnode} ${styles.why}`}>
        <div className={styles.tk}>
          <BulbIcon />
          Opportunity
        </div>
        <div className={styles.ttxt}>{why?.title ?? "—"}</div>
        <div className={styles.tmeta}>opportunity</div>
      </div>
      <div className={styles.tedge}>
        <div className={styles.eline} />
        <div className={styles.elbl}>derived from</div>
      </div>
      <div className={`${styles.tnode} ${styles.focusnode}`}>
        <div className={styles.tk}>
          <DocIcon />
          Requirement
        </div>
        <div className={styles.ttxt}>{title ?? trace.requirementId}</div>
        <div className={styles.tmeta}>requirement</div>
      </div>
      <div className={styles.tedge}>
        <div className={styles.eline} />
        <div className={styles.elbl}>satisfied by</div>
      </div>
      <div className={styles.stacktest}>
        <div className={`${styles.tnode} ${styles.dec}`}>
          <div className={styles.tk}>
            <PencilIcon />
            Design / decision
          </div>
          <div className={styles.ttxt}>{design?.title ?? "—"}</div>
          <div className={styles.tmeta}>{design?.kind ?? "how"}</div>
        </div>
        <div className={`${styles.tnode} ${styles.test}`}>
          <div className={styles.tk}>
            <BeakerIcon />
            Scenario / test
          </div>
          <div className={styles.ttxt}>{test?.title ?? "No test yet"}</div>
          {test && (
            <div className={`${styles.tstat} ${statClass}`}>
              {test.outcome === "pass" ? <CheckIcon /> : <TriangleExclaimIcon />}
              {test.outcome === "pass"
                ? "Test result: passed"
                : test.outcome === "fail"
                  ? "Test result: failed"
                  : "Test result: not run yet"}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
