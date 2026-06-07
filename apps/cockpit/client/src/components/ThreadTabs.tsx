// WP-013 / WP-008 — <ThreadTabs /> — URL-driven tab switcher
// (Chat | Files | Terminal).
//
// The active tab is read from the search-param ?tab=chat|files|terminal;
// clicking a tab updates the search param so the URL is the source of
// truth (shareable within the same machine; preserves on refresh).
//
// Renders ONE panel at a time (the inactive tab's children are not
// mounted). This keeps the Files tab (Monaco-bearing) AND the Terminal
// tab (xterm.js-bearing — it attaches a live session on mount) from
// loading when the founder is on another tab. (WP-008 added Terminal.)

import type { ReactNode } from "react";
import { useSearchParams } from "react-router-dom";
import styles from "../styles/Thread.module.css";

export type TabId = "chat" | "files" | "terminal";

interface Props {
  /** The Chat panel content. Always provided. */
  chat: ReactNode;
  /** The Files panel content. WP-014 ships the real one; this WP
   *  accepts a placeholder. */
  files: ReactNode;
  /** The Terminal panel content — <LiveTerminal/> (WP-008). Only mounted
   *  when the Terminal tab is active, so xterm.js attaches a live session
   *  only when the founder is actually looking at it. */
  terminal: ReactNode;
}

function parseTab(raw: string | null): TabId {
  if (raw === "files") return "files";
  if (raw === "terminal") return "terminal";
  return "chat";
}

export function ThreadTabs({ chat, files, terminal }: Props) {
  const [params, setParams] = useSearchParams();
  const active: TabId = parseTab(params.get("tab"));

  function select(tab: TabId) {
    const next = new URLSearchParams(params);
    if (tab === "chat") {
      next.delete("tab");
    } else {
      next.set("tab", tab);
    }
    setParams(next, { replace: false });
  }

  return (
    <div className={styles.tabs} data-testid="thread-tabs">
      <div className={styles.tabBar} role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={active === "chat"}
          className={active === "chat" ? styles.tabActive : styles.tab}
          onClick={() => select("chat")}
        >
          Chat
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={active === "files"}
          className={active === "files" ? styles.tabActive : styles.tab}
          onClick={() => select("files")}
        >
          Files
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={active === "terminal"}
          className={active === "terminal" ? styles.tabActive : styles.tab}
          onClick={() => select("terminal")}
        >
          Terminal
        </button>
      </div>
      {active === "chat" ? (
        <div
          role="tabpanel"
          data-testid="tab-panel-chat"
          className={styles.panel}
        >
          {chat}
        </div>
      ) : active === "files" ? (
        <div
          role="tabpanel"
          data-testid="tab-panel-files"
          className={styles.panel}
        >
          {files}
        </div>
      ) : (
        <div
          role="tabpanel"
          data-testid="tab-panel-terminal"
          className={styles.panel}
        >
          {terminal}
        </div>
      )}
    </div>
  );
}
