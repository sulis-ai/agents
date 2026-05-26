// WP-015 — <MonacoDiff /> — lazy entry point for the Monaco diff viewer.
//
// Exported as a React.lazy() wrapper so the Monaco bundle (heavy) is
// code-split and only fetched when the founder toggles into the diff
// view. The real wrapper lives in MonacoDiffInner.tsx; this module
// exists solely to be the lazy boundary — the same shape <MonacoFile>
// uses for the read-only file viewer (WP-014). Consumers (<FilePane>)
// mount it inside a <Suspense> so the chunk loads on demand.
//
// References: WP-015 Contract (<MonacoDiff> lazy-loaded via
// React.lazy), ADR-006.

import { lazy } from "react";
import type { MonacoDiffProps } from "./MonacoDiffInner";

export type { MonacoDiffProps };

export const MonacoDiff = lazy(() => import("./MonacoDiffInner"));
