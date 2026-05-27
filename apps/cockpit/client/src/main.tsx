// WP-011 — client entry point.
//
// Mounts <App /> wrapped in QueryClientProvider (TanStack Query)
// inside React.StrictMode. The BrowserRouter wrap lives inside <App />
// itself so tests can swap in MemoryRouter via <AppRoutes />.

import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { App } from "./App";
import { queryClient } from "./queryClient";
import "./index.css";

const rootEl = document.getElementById("root");
if (!rootEl) {
  throw new Error("cockpit: #root element missing from index.html");
}

ReactDOM.createRoot(rootEl).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);
