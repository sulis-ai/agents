// WP-001 — placeholder client entry point.
//
// Mounts <App /> into the #root element from index.html. WP-011 will
// wrap this with QueryClientProvider + BrowserRouter; for the
// skeleton, a bare React.StrictMode + render is enough to validate the
// Vite + React + TS toolchain.

import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";

const rootEl = document.getElementById("root");
if (!rootEl) {
  throw new Error("cockpit: #root element missing from index.html");
}

ReactDOM.createRoot(rootEl).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
