// WP-010 — <OnboardingChat /> — the cold-start conversational setup (UC-07;
// ADR-007/008; the SIGNED visual contract, sulis-app.html panels 13–16).
//
// A form can't pick from an empty graph, so onboarding is a CONVERSATION that
// creates the graph. It REUSES the chat composer idiom + the SSE client (EP-03)
// — pointed at /api/onboarding/session — not a parallel UI.
//
// The flow + the three founder-locked decisions baked in:
//   1. choose an area → answer → see a plain-English PROPOSAL → CONFIRM;
//   2. the proposal (Tenant/Product/Project + repo plan) is shown BEFORE any
//      mint (the confirm gate, FR-N6); a declined flow creates nothing;
//   3. the repo branch is explicit FIND vs CREATE with LOCAL-ONLY PRE-SELECTED
//      (hosted-remote a clearly-labelled separate opt-in — founder-locked);
//   4. the Product icon is a NEUTRAL TWO-LETTER TILE (no logo upload control —
//      founder-locked), reusing ProductSwitcher's `monogram` (EP-03);
//   5. on success the "your product is set up" end state appears → the board.
//
// Tokens only — no raw hex (WPF-07 / UXD-04). `streamOnboarding` is injectable
// for tests (defaults to the real funnel).

import { useState, type KeyboardEvent } from "react";

import { useOnboarding } from "../api/useOnboarding";
import type { StreamOnboardingFn } from "../api/client";
import type { OnboardingRequest } from "../../../shared/api-types";
import { monogram } from "./ProductSwitcher";
import styles from "../styles/OnboardingChat.module.css";

interface Props {
  /** Injectable for tests; defaults to the real funnel. */
  streamOnboarding?: StreamOnboardingFn;
  /** Called once the product is set up (host navigates to the board). */
  onDone?: () => void;
}

/** The create-location choice — local-only is the founder-locked default. */
type CreateTarget = "local" | "hosted-remote";

export function OnboardingChat({ streamOnboarding, onDone }: Props) {
  const onboarding = useOnboarding(
    streamOnboarding ? { streamOnboarding } : {},
  );
  const [areaDraft, setAreaDraft] = useState("");
  // The repo branch: default FIND, but the CREATE branch's location is
  // pre-selected LOCAL-ONLY (founder-locked, ADR-008).
  const [repoMode, setRepoMode] = useState<"find" | "create">("find");
  const [createTarget, setCreateTarget] = useState<CreateTarget>("local");

  const busy = onboarding.isStreaming;

  const submitArea = () => {
    const area = areaDraft.trim();
    if (area === "" || busy) return;
    void onboarding.search(area);
  };

  const onAreaKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submitArea();
    }
  };

  const confirm = () => {
    if (busy) return;
    const repoChoice: OnboardingRequest["repoChoice"] =
      repoMode === "create"
        ? { mode: "create", createTarget }
        : { mode: "find" };
    void onboarding.confirm(repoChoice);
  };

  const productName = onboarding.proposal?.product ?? "Your product";
  const isDone = onboarding.state === "done" && onboarding.minted !== null;

  // ── The "your product is set up" end state (panel 16) ──
  if (isDone) {
    const mintedName = onboarding.minted?.product?.name ?? productName;
    return (
      <div className={styles.frontdoor} data-testid="onboarding">
        <div className={styles.setupdone} data-testid="setup-done">
          <span className={styles.tile} aria-hidden="true" data-testid="product-tile">
            {monogram(mintedName)}
          </span>
          <h3>{mintedName} is set up</h3>
          <p>
            Your product and its code are saved — I won't have to ask again. Your
            board is ready; just tell me what you'd like to work on and I'll start
            it for you.
          </p>
          <button
            type="button"
            className={styles.primary}
            data-testid="go-to-board"
            onClick={() => onDone?.()}
          >
            Go to the board
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.frontdoor} data-testid="onboarding">
      <div className={styles.scroll}>
        <div className={styles.hero}>
          <h2>Let's get you set up</h2>
          <p>
            There's nothing here yet, so I'll set things up with you — a couple of
            quick questions, then your board is ready. Nothing is created until
            you say so.
          </p>
        </div>

        {/* The streamed agent text for the current turn. */}
        {onboarding.replyText.length > 0 && (
          <div className={styles.agent} data-testid="onboarding-reply">
            {onboarding.replyText}
          </div>
        )}

        {/* The PROPOSAL — shown BEFORE any mint (the confirm gate, FR-N6). */}
        {onboarding.proposal !== null && onboarding.state !== "minting" && (
          <div className={styles.proposalCard} data-testid="onboarding-proposal">
            <div className={styles.proposalHead}>
              <span className={styles.tile} aria-hidden="true" data-testid="product-tile">
                {monogram(productName)}
              </span>
              <div>
                <div className={styles.proposalTitle}>Here's what I'll set up</div>
                {onboarding.proposal.alreadyMinted && (
                  <div className={styles.alreadyNote} data-testid="already-minted">
                    You already have this — I'll connect it, not create a duplicate.
                  </div>
                )}
              </div>
            </div>
            <dl className={styles.proposalList}>
              <dt>Product</dt>
              <dd>{productName}</dd>
              {onboarding.proposal.projects?.[0]?.name && (
                <>
                  <dt>Project</dt>
                  <dd>{onboarding.proposal.projects[0].name}</dd>
                </>
              )}
              <dt>Repo</dt>
              <dd>{repoPlanLabel(repoMode, createTarget)}</dd>
            </dl>

            {/* The find-or-create branch. */}
            <div
              className={styles.branch}
              role="group"
              aria-label="Where your code lives"
            >
              <button
                type="button"
                className={repoMode === "find" ? `${styles.branchOpt} ${styles.sel}` : styles.branchOpt}
                aria-pressed={repoMode === "find"}
                data-testid="repo-mode-find"
                onClick={() => setRepoMode("find")}
              >
                Connect an existing repo
              </button>
              <button
                type="button"
                className={repoMode === "create" ? `${styles.branchOpt} ${styles.sel}` : styles.branchOpt}
                aria-pressed={repoMode === "create"}
                data-testid="repo-mode-create"
                onClick={() => setRepoMode("create")}
              >
                Create a new repo
              </button>
            </div>

            {/* The create-location control — LOCAL-ONLY pre-selected
                (founder-locked, ADR-008); hosted-remote a clearly-labelled
                separate opt-in, never the default. Shown whenever the founder
                might create (the "create a new repo" branch); it only takes
                effect when that branch is chosen, but the safe local default is
                always visible so it is never silently a hosted publish. */}
            {repoMode === "create" && (
              <p className={styles.gateBody} data-testid="create-location-hint">
                Where should I create it? Local-only is the safe default —
                nothing leaves your machine until you choose otherwise.
              </p>
            )}
            <div
              className={styles.seg}
              role="group"
              aria-label="Where to create the repo"
              hidden={repoMode !== "create"}
            >
              <button
                type="button"
                className={createTarget === "local" ? `${styles.segOpt} ${styles.on}` : styles.segOpt}
                aria-pressed={createTarget === "local"}
                data-testid="repo-target-local"
                onClick={() => setCreateTarget("local")}
              >
                Local only
              </button>
              <button
                type="button"
                className={createTarget === "hosted-remote" ? `${styles.segOpt} ${styles.on}` : styles.segOpt}
                aria-pressed={createTarget === "hosted-remote"}
                data-testid="repo-target-hosted-remote"
                onClick={() => setCreateTarget("hosted-remote")}
              >
                On GitHub (separate sign-in)
              </button>
            </div>

            {/* The confirm gate (panel 15): nothing happens until you say go. */}
            <div className={styles.gate}>
              <div className={styles.gateBody}>
                Nothing is created until you say go.
              </div>
              <div className={styles.gateActions}>
                <button
                  type="button"
                  className={styles.primary}
                  data-testid="onboarding-confirm"
                  disabled={busy}
                  onClick={confirm}
                >
                  Go ahead
                </button>
                <button
                  type="button"
                  className={styles.outline}
                  data-testid="onboarding-decline"
                  disabled={busy}
                  onClick={() => onboarding.decline()}
                >
                  Not yet
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Honest failure (FR-N7/N10) — surfaced plainly, creates nothing. */}
        {onboarding.state === "failed" && (
          <div
            className={styles.error}
            data-testid="onboarding-error"
            role="alert"
          >
            {onboarding.errorMessage ?? "Something went wrong — nothing was saved."}
          </div>
        )}
      </div>

      {/* The composer — reused chat idiom: choose your area in plain English. */}
      <div className={styles.composerWrap}>
        {busy && (
          <div className={styles.statusLine} data-testid="onboarding-status">
            {statusLabel(onboarding.state)}
          </div>
        )}
        <div className={styles.composer}>
          <div className={styles.field}>
            <textarea
              className={styles.textarea}
              aria-label="Which folder is your code in?"
              placeholder="Tell me which folder your code is in…"
              value={areaDraft}
              disabled={busy}
              onChange={(e) => setAreaDraft(e.target.value)}
              onKeyDown={onAreaKeyDown}
            />
          </div>
          <button
            type="button"
            className={styles.send}
            data-testid="onboarding-send"
            disabled={busy || areaDraft.trim() === ""}
            onClick={submitArea}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

/** Plain-English label for the in-flight lifecycle. */
function statusLabel(state: ReturnType<typeof useOnboarding>["state"]): string {
  switch (state) {
    case "searching":
      return "Looking in your folder…";
    case "asking":
      return "Thinking…";
    case "minting":
      return "Setting things up…";
    default:
      return "Working…";
  }
}

/** The repo-plan recap line the proposal shows. */
function repoPlanLabel(mode: "find" | "create", target: CreateTarget): string {
  if (mode === "find") return "Connect your existing repo";
  return target === "hosted-remote"
    ? "Create a new repo on GitHub"
    : "Create a new local repo (on your machine)";
}
