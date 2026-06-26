// WP-003 — <ProductChatDock>: the right-docked, collapsible per-product chat
// (ADR-001/002/003/004; the SIGNED visual contract).
//
// The dock is the shell that ties everything together:
//   - it reads the SAME useActiveProduct() store the board reads, so ONE switch
//     moves board + chat together (no second active-product store — ADR-001);
//   - its header echoes the active product's tile via the ONE menu primitive
//     (ProductControl), so "whose chat" is always legible (the founder's ask);
//   - it loads + relays the scope's thread via useProductChat (per-scope
//     histories, never blended — ADR-002);
//   - the agent picker (AgentPicker) at the composer foot names the running
//     provider (AI-07) and guards a mid-run switch (AI-03);
//   - chat→card reuses start-from-intent (ADR-004): the per-product chat passes
//     the known productId; the overview chat (product:__all__) asks WHICH
//     product first, then proposes;
//   - the three honest states (loading skeleton / empty / error) render per the
//     visual contract, with a reduced-motion fallback.

import { useEffect, useMemo, useState } from "react";
import type { ChatProvider, Product } from "../../../shared/api-types";
import { UNASSIGNED_SCOPE } from "../../../shared/chatScope";
import type { ProductScope } from "../lib/productCounts";
import { chatScopeForProduct, isOverviewScope } from "../lib/chatScopeForProduct";
import { useActiveProduct } from "../api/activeProduct";
import {
  useProductChat,
  type UseProductChatOptions,
} from "../api/useProductChat";
import { useStartFromIntent } from "../api/useStartFromIntent";
import type { StreamStartFromIntentFn } from "../api/client";
import { ProductControl, type ProductRow } from "./ProductControl";
import { AgentPicker } from "./AgentPicker";
import { ProductChat } from "./ProductChat";
import styles from "./ProductChatDock.module.css";

// Sentinel row ids the scope switcher uses (ProductControl scope mode), matched
// to the active-scope vocabulary on commit.
const ALL_ROW_ID = "all";
const UNASSIGNED_ROW_ID = "unassigned";

const SUGGESTION_CHIPS = [
  "What needs me?",
  "Start something new",
  "Show me what's stuck",
];

export interface ProductChatDockProps {
  products: Product[];
  fetchChatThread?: UseProductChatOptions["fetchChatThread"];
  streamProductChat?: UseProductChatOptions["streamProductChat"];
  putChatProvider?: UseProductChatOptions["putChatProvider"];
  /** Injected for tests; defaults to the real start-from-intent funnel. */
  streamStartFromIntent?: StreamStartFromIntentFn;
}

/** Map the active board scope → the scope switcher's selected row id. */
function scopeToRowId(scope: ProductScope): string {
  if (scope === null) return ALL_ROW_ID;
  if (scope === UNASSIGNED_SCOPE) return UNASSIGNED_ROW_ID;
  return scope;
}

/** Map a committed switcher row id → the board scope vocabulary. */
function rowIdToScope(id: string | null): ProductScope {
  if (id === ALL_ROW_ID || id === null) return null;
  if (id === UNASSIGNED_ROW_ID) return UNASSIGNED_SCOPE;
  return id;
}

export function ProductChatDock({
  products,
  fetchChatThread,
  streamProductChat,
  putChatProvider,
  streamStartFromIntent,
}: ProductChatDockProps) {
  const { activeProductId, setActiveProductId } = useActiveProduct();
  const scope = chatScopeForProduct(activeProductId);
  const overview = isOverviewScope(activeProductId);

  const chat = useProductChat(scope, {
    fetchChatThread,
    streamProductChat,
    putChatProvider,
  });

  const [collapsed, setCollapsed] = useState(false);
  const [draft, setDraft] = useState("");
  // The overview chat collects a product before proposing (ADR-004); this holds
  // the captured intent while the founder picks which product it belongs to.
  const [pendingIntent, setPendingIntent] = useState<string | null>(null);
  // The product the chat→card proposal targets — known up-front for a
  // per-product chat, chosen by the founder for the overview chat.
  const [cardProductId, setCardProductId] = useState<string | null>(
    overview ? null : (activeProductId as string),
  );
  // An intent waiting to be proposed once `cardProductId` is settled. This
  // single queue is what lets BOTH paths drive the SAME hook.propose (one
  // creation path, ADR-004) — the per-product path resolves the product up
  // front; the overview path resolves it when the founder picks one.
  const [queuedIntent, setQueuedIntent] = useState<string | null>(null);

  const start = useStartFromIntent({
    productId: cardProductId ?? "",
    streamStartFromIntent,
  });

  // Drive the proposal once an intent is queued AND a product is resolved, so
  // the propose always carries the right productId (the hook reads it from its
  // options, which have re-rendered by the time this effect runs).
  useEffect(() => {
    if (queuedIntent !== null && cardProductId) {
      const intent = queuedIntent;
      setQueuedIntent(null);
      void start.propose(intent);
    }
  }, [queuedIntent, cardProductId, start]);

  // ── header tile echo ────────────────────────────────────────────────────
  // The active product's NAME drives the dock's aria-label + every "whose chat"
  // string. The tile GLYPH echo is rendered by the header's ProductControl
  // trigger itself (it derives the glyph from selectedId), so there is no second
  // glyph source here.
  const activeProduct = products.find((p) => p.productId === activeProductId);
  const headerName = useMemo(() => {
    if (activeProductId === null) return "All products";
    if (activeProductId === UNASSIGNED_SCOPE) return "Unassigned";
    return activeProduct?.name ?? "Product";
  }, [activeProductId, activeProduct]);

  const switcherRows: ProductRow[] = useMemo(
    () => [
      { productId: ALL_ROW_ID, name: "All products", glyph: "all-grid" },
      { productId: UNASSIGNED_ROW_ID, name: "Unassigned", glyph: "unassigned-dashed" },
      ...products.map((p) => ({
        productId: p.productId,
        name: p.name,
        glyph: "monogram" as const,
      })),
    ],
    [products],
  );

  const productRows: ProductRow[] = useMemo(
    () =>
      products.map((p) => ({
        productId: p.productId,
        name: p.name,
        glyph: "monogram" as const,
      })),
    [products],
  );

  function handleSwitch(rowId: string | null) {
    const nextScope = rowIdToScope(rowId);
    setActiveProductId(nextScope);
    // Switching scope drops any in-flight which-product disambiguation, and
    // re-baselines the chat→card target so a residual value from the previous
    // scope can never leak into a later propose (the invariant is explicit
    // here, not emergent from every caller re-setting it).
    setPendingIntent(null);
    setQueuedIntent(null);
    setCardProductId(nextScope === null || nextScope === UNASSIGNED_SCOPE ? null : nextScope);
  }

  // ── send a chat message (ADR-001/003) ─────────────────────────────────────
  // The composer's primary action: stream a reply on the scope's provider. This
  // is distinct from "Start work" (chat→card, below) — one talks, the other
  // files a card.
  function sendMessage() {
    const prompt = draft.trim();
    if (!prompt || chat.isStreaming) return;
    setDraft("");
    void chat.send(prompt);
  }

  function onComposerKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    // Enter sends; Shift+Enter inserts a newline (the Slack-style convention the
    // existing Composer uses).
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  // ── chat→card (ADR-004) ───────────────────────────────────────────────────
  function startWork() {
    const intent = draft.trim();
    if (!intent) return;
    if (overview) {
      // Overview chat: ask which product BEFORE proposing — never file unscoped.
      setPendingIntent(intent);
      return;
    }
    // Per-product chat: the product is already known — queue the propose (the
    // effect fires it with the resolved product).
    setCardProductId(activeProductId as string);
    setQueuedIntent(intent);
  }

  function chooseProductForCard(productId: string | null) {
    if (!productId || pendingIntent === null) return;
    // The overview chat now has its product — bind it + queue the propose; the
    // effect drives the SAME hook.propose with the chosen product (ADR-004:
    // one creation path, never a second).
    const intent = pendingIntent;
    setPendingIntent(null);
    setCardProductId(productId);
    setQueuedIntent(intent);
  }

  function onSwitchProvider(provider: ChatProvider) {
    void chat.switchProvider(provider);
  }

  const sessionRunning = chat.isStreaming;
  const statusWord = sessionRunning ? "Working…" : "Idle";

  // chat-ux Fix 2 — collapsed is a slim vertical RAIL on the right (not empty
  // white space): a thin strip carrying the expand affordance + the active
  // product's identity, so "whose chat" stays legible while it's tucked away.
  if (collapsed) {
    return (
      <aside
        className={`${styles.dock} ${styles.collapsed}`}
        aria-label={`${headerName} chat`}
        data-testid="product-chat-dock"
      >
        <div className={styles.rail} data-testid="chat-rail">
          <button
            type="button"
            className={styles.railToggle}
            data-testid="chat-toggle"
            aria-pressed={true}
            aria-label="Show chat"
            onClick={() => setCollapsed(false)}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
              <polyline points="15 18 9 12 15 6" />
            </svg>
          </button>
          <span
            className={`${styles.railDot} ${sessionRunning ? styles.working : styles.idle}`}
            data-testid="agent-status"
            data-state={sessionRunning ? "working" : "idle"}
            aria-hidden="true"
          />
          {/* The active product's identity, set sideways down the rail. */}
          <span className={styles.railName}>{headerName}</span>
        </div>
      </aside>
    );
  }

  return (
    <aside
      className={styles.dock}
      aria-label={`${headerName} chat`}
      data-testid="product-chat-dock"
    >
      {/* ── header: the active product tile echo + honest status ───────────── */}
      <header className={styles.head}>
        <div className={styles.switcher} data-testid="dock-switcher">
          <ProductControl
            mode="scope"
            rows={switcherRows}
            selectedId={scopeToRowId(activeProductId)}
            onSelect={handleSwitch}
            testIdPrefix="dock-switcher"
            triggerLabel={`Viewing ${headerName}. Switch product — moves the board and the chat together.`}
          />
        </div>

        <div className={styles.right}>
          <span
            className={`${styles.status} ${sessionRunning ? styles.working : styles.idle}`}
            data-testid="agent-status"
            data-state={sessionRunning ? "working" : "idle"}
          >
            <span className={styles.sdot} aria-hidden="true" />
            {statusWord}
          </span>
          <button
            type="button"
            className={styles.toggle}
            data-testid="chat-toggle"
            aria-pressed={false}
            aria-label="Hide chat"
            onClick={() => setCollapsed(true)}
          >
            Hide chat
          </button>
        </div>
      </header>

      {!collapsed && (
        <>
          {/* ── the three honest states + the transcript ──────────────────── */}
          {chat.isLoading ? (
            <div className={styles.skel} data-testid="chat-loading" aria-busy="true">
              <span className={`${styles.skelLine} ${styles.med}`} />
              <span className={styles.skelLine} />
              <span className={`${styles.skelLine} ${styles.short}`} />
            </div>
          ) : chat.isError ? (
            <div className={styles.errBox} role="alert" data-testid="chat-error">
              <div className={styles.errTitle}>I couldn't reach this chat</div>
              <p>Something went wrong loading this conversation.</p>
              <button
                type="button"
                className={styles.btnGhost}
                data-testid="chat-error-retry"
                onClick={chat.retry}
              >
                Try again
              </button>
            </div>
          ) : chat.messages.length === 0 &&
            !chat.isStreaming &&
            chat.replyText.length === 0 ? (
            <div className={styles.empty} data-testid="chat-empty">
              <h5 className={styles.emptyTitle}>A fresh {headerName} chat</h5>
              <p>
                Tell me what you want to do for {headerName}, or pick a starter
                below.
              </p>
            </div>
          ) : (
            <ProductChat
              messages={chat.messages}
              provider={chat.provider}
              replyText={chat.replyText}
              isStreaming={chat.isStreaming}
            />
          )}

          {/* ── chat→card proposal + confirm (ADR-004 reuses start-from-intent) */}
          {start.proposal && (
            <div className={styles.gate} data-testid="chat-card-proposal">
              <p>
                Start <b>{start.proposal.slug}</b> ({start.proposal.primitive})?
              </p>
              <div className={styles.gateActs}>
                <button
                  type="button"
                  className={styles.btnPrimary}
                  data-testid="chat-card-confirm"
                  onClick={() => void start.confirm()}
                >
                  Start it
                </button>
                <button
                  type="button"
                  className={styles.btnGhost}
                  data-testid="chat-card-cancel"
                  onClick={start.reset}
                >
                  Not yet
                </button>
              </div>
            </div>
          )}

          {start.started && (
            <div className={styles.activity} data-testid="chat-card-started">
              Started {start.started.slug} — it's on the {headerName} board now.
            </div>
          )}

          {/* ── overview chat: which-product disambiguation (ADR-004) ──────── */}
          {pendingIntent !== null && (
            <div className={styles.which} data-testid="which-product">
              <p>Which product should that live under?</p>
              <div data-testid="which-product-menu-wrap">
                <ProductControl
                  mode="scope"
                  rows={productRows}
                  selectedId={null}
                  onSelect={chooseProductForCard}
                  testIdPrefix="which-product"
                  triggerLabel="Choose which product the new work belongs to"
                />
              </div>
            </div>
          )}

          {/* ── composer: chips + dual-mode input + slash hint + agent foot ── */}
          <div className={styles.composer}>
            <div className={styles.chips}>
              {SUGGESTION_CHIPS.map((c) => (
                <button
                  key={c}
                  type="button"
                  className={styles.chip}
                  data-testid="chat-chip"
                  onClick={() => setDraft(c)}
                >
                  {c}
                </button>
              ))}
            </div>

            {chat.errorMessage && (
              <div className={styles.relayError} role="alert" data-testid="chat-send-error">
                {chat.errorMessage}
              </div>
            )}

            <div className={styles.field}>
              <textarea
                aria-label={`Message the ${headerName} chat`}
                data-testid="chat-intent-input"
                placeholder="Type a message, or / for commands…"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={onComposerKeyDown}
              />
            </div>

            <div className={styles.foot}>
              <AgentPicker
                running={chat.provider}
                selected={chat.provider}
                sessionRunning={sessionRunning}
                onSwitch={onSwitchProvider}
              />
              <span className={styles.slashhint}>
                <kbd>/</kbd> for commands · <kbd>Enter</kbd> to send ·{" "}
                <kbd>Shift</kbd>+<kbd>Enter</kbd> for a newline
              </span>
              <span className={styles.grow} />
              <button
                type="button"
                className={styles.btnGhost}
                data-testid="chat-start-work"
                onClick={startWork}
              >
                Start work
              </button>
              <button
                type="button"
                className={styles.send}
                data-testid="chat-send"
                disabled={chat.isStreaming}
                onClick={sendMessage}
              >
                Send
              </button>
            </div>
          </div>
        </>
      )}
    </aside>
  );
}
