// WP-011 — Routes definition + app root.
//
// AppRoutes is exported separately so tests can mount it inside a
// MemoryRouter; <App /> wraps it in BrowserRouter for production use.
//
// Route shape per WP Contract:
//   /                → <Dashboard>   (inside <Shell>)
//   /c/:changeId     → <ThreadView>  (inside <Shell>)
//   /*               → <NotFound>    (inside <Shell>)

import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Shell } from "./layouts/Shell";
import { Dashboard } from "./pages/Dashboard";
import { ThreadView } from "./pages/ThreadView";
import { NotFound } from "./pages/NotFound";
// WP-003 — the theme context layer wraps the whole app so every route is
// inside it. AppRoutes stays bare so MemoryRouter-based tests keep mounting
// it directly without needing the provider.
import { ThemeProvider } from "./theme/ThemeProvider";

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/c/:changeId" element={<ThreadView />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}

export function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </ThemeProvider>
  );
}
