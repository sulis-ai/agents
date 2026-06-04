// WP-011 — Routes definition + app root.
//
// AppRoutes is exported separately so tests can mount it inside a
// MemoryRouter; <App /> wraps it in BrowserRouter for production use.
//
// Route shape per WP Contract:
//   /                → <Board>          (inside <Shell>) — WP-003 stage board
//   /c/:changeId     → <ThreadView>     (inside <Shell>)
//   /concierge       → <ConciergePage>  (inside <Shell>) — WP-009 front door
//   /*               → <NotFound>       (inside <Shell>)

import { BrowserRouter, Route, Routes } from "react-router-dom";
import { ActiveProductProvider } from "./api/activeProduct";
import { Shell } from "./layouts/Shell";
import { Board } from "./pages/Board";
import { ThreadView } from "./pages/ThreadView";
import { ConciergePage } from "./pages/ConciergePage";
import { OnboardingPage } from "./pages/OnboardingPage";
import { NotFound } from "./pages/NotFound";

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route path="/" element={<Board />} />
        <Route path="/c/:changeId" element={<ThreadView />} />
        <Route path="/concierge" element={<ConciergePage />} />
        {/* WP-010 — the cold-start onboarding surface (UC-07). */}
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}

export function App() {
  return (
    // WP-008 — the active-Product UI scope wraps the whole app so the sidebar
    // switcher and the board share one scope; switching re-scopes the board +
    // per-product views (FR-37/38, ADR-009).
    <ActiveProductProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </ActiveProductProvider>
  );
}
