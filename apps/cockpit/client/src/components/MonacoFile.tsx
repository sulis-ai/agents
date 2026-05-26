// WP-014 — <MonacoFile /> — lazy entry point for the Monaco viewer.
//
// Exported as a React.lazy() wrapper so the Monaco bundle (heavy) is
// code-split and only fetched when the founder actually opens a file.
// The real wrapper lives in MonacoFileInner.tsx; this module exists
// solely to be the lazy boundary. Consumers (<FilePane>) mount it
// inside a <Suspense> so the chunk loads on demand.
//
// References: WP-014 Contract (<MonacoFile> lazy-loaded via React.lazy),
// ADR-001.

import { lazy } from "react";
import type { MonacoFileProps } from "./MonacoFileInner";

export type { MonacoFileProps };

export const MonacoFile = lazy(() => import("./MonacoFileInner"));
