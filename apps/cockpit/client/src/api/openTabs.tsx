// Chat-redesign (chat-B2 signed contract) — open-tabs workspace state.
//
// A change opens in its OWN tab. This holds the ordered list of open change
// tabs (by changeId); the Board is an always-present tab rendered separately.
// Visiting /c/:id registers that change as an open tab (WorkspaceShell does
// the registration); closing a tab removes it. Display info (name, stage,
// liveness dot) is resolved from the changes query in the tab strip — we
// store only ids here.
//
// Safe defaults (no-op) so a tree mounted WITHOUT the provider — e.g.
// AppRoutes in a routing test — behaves exactly as before.

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export interface OpenTabsValue {
  /** Ordered changeIds with an open tab. */
  openChangeIds: string[];
  /** Open (or no-op if already open) a change's tab. */
  openTab: (changeId: string) => void;
  /** Close a change's tab. Returns the changeId to navigate to next, or
   * null for the Board (caller owns navigation). */
  closeTab: (changeId: string) => string | null;
}

const OpenTabsContext = createContext<OpenTabsValue>({
  openChangeIds: [],
  openTab: () => {},
  closeTab: () => null,
});

export function OpenTabsProvider({ children }: { children: ReactNode }) {
  const [openChangeIds, setOpen] = useState<string[]>([]);

  const openTab = useCallback((changeId: string) => {
    setOpen((ids) => (ids.includes(changeId) ? ids : [...ids, changeId]));
  }, []);

  // Returns the neighbour tab to land on after closing (the tab to the left,
  // else the new last tab, else null = Board). Navigation is the caller's job.
  const closeTab = useCallback(
    (changeId: string): string | null => {
      let next: string | null = null;
      setOpen((ids) => {
        const i = ids.indexOf(changeId);
        const remaining = ids.filter((x) => x !== changeId);
        if (i > 0) next = remaining[i - 1] ?? remaining[remaining.length - 1] ?? null;
        else next = remaining[0] ?? null;
        return remaining;
      });
      return next;
    },
    [],
  );

  const value = useMemo<OpenTabsValue>(
    () => ({ openChangeIds, openTab, closeTab }),
    [openChangeIds, openTab, closeTab],
  );

  return (
    <OpenTabsContext.Provider value={value}>
      {children}
    </OpenTabsContext.Provider>
  );
}

export function useOpenTabs(): OpenTabsValue {
  return useContext(OpenTabsContext);
}
