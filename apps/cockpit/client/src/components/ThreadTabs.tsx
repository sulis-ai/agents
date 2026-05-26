// WP-013 — <ThreadTabs /> — URL-driven tab switcher (Chat | Files).
//
// The active tab is read from the search-param ?tab=chat|files;
// clicking a tab updates the search param so the URL is the source of
// truth (shareable within the same machine; preserves on refresh).
//
// Renders ONE panel at a time (the inactive tab's children are not
// mounted). This keeps the Files tab (Monaco-bearing) from loading
// when the founder is on Chat.

import type { ReactNode } from "react";
import { useSearchParams } from "react-router-dom";
import styles from "../styles/Thread.module.css";

export type TabId = "chat" | "files";

interface Props {
  /** The Chat panel content. Always provided. */
  chat: ReactNode;
  /** The Files panel content. WP-014 ships the real one; this WP
   *  accepts a placeholder. */
  files: ReactNode;
}

export function ThreadTabs({ chat, files }: Props) {
  const [params, setParams] = useSearchParams();
  const rawTab = params.get("tab");
  const active: TabId = rawTab === "files" ? "files" : "chat";

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
      </div>
      {active === "chat" ? (
        <div role="tabpanel" data-testid="tab-panel-chat" className={styles.panel}>
          {chat}
        </div>
      ) : (
        <div role="tabpanel" data-testid="tab-panel-files" className={styles.panel}>
          {files}
        </div>
      )}
    </div>
  );
}
