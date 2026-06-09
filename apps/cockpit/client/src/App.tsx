// Routes definition + app root.
//
// AppRoutes is exported separately so tests can mount it inside a
// MemoryRouter; <App /> wraps it in BrowserRouter for production use.
//
// Route shape:
//   /                → <Board>          (inside <WorkspaceShell>) — the stage board
//   /c/:changeId     → <ThreadView>     (inside <WorkspaceShell>) — a change, in its own tab
//   /concierge       → <ConciergePage>  (inside <WorkspaceShell>) — the front door
//   /settings        → <SettingsPage>   (inside <WorkspaceShell>) — products/projects/repos tree (WP-008)
//   /*               → <NotFound>       (inside <WorkspaceShell>)
//
// Chat-redesign (chat-B2): the persistent left Sidebar is replaced by the
// WorkspaceShell's top bar (product switcher + a tab per open change).

import { BrowserRouter, Route, Routes } from "react-router-dom";
import { ActiveProductProvider } from "./api/activeProduct";
import { OpenTabsProvider } from "./api/openTabs";
import { WorkspaceShell } from "./layouts/WorkspaceShell";
import { Board } from "./pages/Board";
import { ThreadView } from "./pages/ThreadView";
import { ConciergePage } from "./pages/ConciergePage";
import { OnboardingPage } from "./pages/OnboardingPage";
import { StartFromIntentPage } from "./pages/StartFromIntentPage";
import { SettingsPage } from "./pages/SettingsPage";
import { NotFound } from "./pages/NotFound";
// WP-003 — the theme context layer wraps the whole app so every route is
// inside it. AppRoutes stays bare so MemoryRouter-based tests keep mounting
// it directly without needing the provider.
import { ThemeProvider } from "./theme/ThemeProvider";

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<WorkspaceShell />}>
        <Route path="/" element={<Board />} />
        <Route path="/c/:changeId" element={<ThreadView />} />
        <Route path="/concierge" element={<ConciergePage />} />
        {/* The cold-start onboarding surface (UC-07). */}
        <Route path="/onboarding" element={<OnboardingPage />} />
        {/* start-from-intent (UC-08) + investigation→change (UC-10). */}
        <Route path="/start" element={<StartFromIntentPage />} />
        {/* Settings — products/projects/repos tree (WP-008). */}
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}

export function App() {
  return (
    // ThemeProvider (WP-003) wraps the whole app so every route is inside the
    // theme context (sets root data-theme; first visit follows the OS, choice
    // persists). The active-Product UI scope wraps the app so the product
    // switcher and the board share one scope; switching re-scopes the board
    // (ADR-009). OpenTabsProvider holds which changes have an open tab
    // (chat-B2).
    <ThemeProvider>
      <ActiveProductProvider>
        <OpenTabsProvider>
          <BrowserRouter>
            <AppRoutes />
          </BrowserRouter>
        </OpenTabsProvider>
      </ActiveProductProvider>
    </ThemeProvider>
  );
}
