// WP-010 — per-request logging middleware (TDD §13.8).
//
// Logs ONE LINE per request: method, path, status, duration in ms.
// Deliberately MINIMAL — no headers, no bodies, no file contents, no
// query-string contents (the path itself includes the query in
// `req.originalUrl`, which is OK as a single-user local log; the
// hygiene gate the request-log.test.ts covers is that the response
// body never lands in the log line).
//
// Format: `[cockpit] METHOD PATH STATUS DURATIONms`
// Example: `[cockpit] GET /api/changes 200 4ms`
//
// The middleware writes via `console.log` so it shares the dev-runner
// pipe with the placeholder banner from WP-001 (and any future
// structured-log refactor lives in a single seam).

import type { Request, Response, NextFunction } from "express";

export function requestLogMiddleware(
  req: Request,
  res: Response,
  next: NextFunction,
): void {
  const start = Date.now();
  res.on("finish", () => {
    const duration = Date.now() - start;
    // eslint-disable-next-line no-console -- intentional: dev request log
    console.log(
      `[cockpit] ${req.method} ${req.originalUrl} ${res.statusCode} ${duration}ms`,
    );
  });
  next();
}
