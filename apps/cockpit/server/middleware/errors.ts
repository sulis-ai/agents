// WP-010 — error mapper middleware (TDD §5, §13.2).
//
// Route handlers throw typed errors from `server/lib/errors.ts` (and
// the diff-route-specific `NoBaseShaError` below). This middleware
// translates them into the cockpit's JSON error envelope:
//
//   HTTP 4xx/5xx
//   Content-Type: application/json
//   { "error": "<human-readable message>", "code": "<TYPED_CODE>" }
//
// The mapping table (TDD §13.2 + WP-010 Contract):
//
//   PathOutsideWorktreeError → 400 PATH_OUTSIDE_WORKTREE
//   NotFoundError            → 404 NOT_FOUND
//   NotADirectoryError       → 400 NOT_A_DIRECTORY
//   IsADirectoryError        → 400 IS_A_DIRECTORY
//   GitError                 → 400 GIT_ERROR
//   TimeoutError             → 504 TIMEOUT
//   NoBaseShaError           → 422 NO_BASE_SHA
//   BadRequestError          → 400 BAD_REQUEST    (e.g. missing ?path=)
//   <unknown>                → 500 INTERNAL_ERROR
//
// The middleware is intentionally narrow: route handlers `next(err)`
// (or throw inside an async wrapper) and this is the one place that
// decides which status code + code string lands on the wire.

import type {
  ErrorRequestHandler,
  Request,
  Response,
  NextFunction,
} from "express";

import {
  GitError,
  IsADirectoryError,
  NotADirectoryError,
  NotFoundError,
  PathOutsideWorktreeError,
  TimeoutError,
} from "../lib/errors";

/**
 * Thrown by route handlers when the change-store record for an :id
 * parameter is missing. The lib layer does not throw this — it returns
 * `null` — so we define our own typed class here to keep the mapping
 * uniform (one `instanceof` check per error class in the mapper).
 */
export class NoSuchChangeError extends Error {
  readonly code = "NOT_FOUND";
  constructor(changeId: string) {
    super(`no change with id: ${changeId}`);
    this.name = "NoSuchChangeError";
  }
}

/**
 * Thrown by the diff route when the change has no `baseSha`. Distinct
 * from the lib's GitError — the situation is "we never recorded a
 * baseline; the diff is not computable" rather than "git rejected our
 * arguments". Mapped to 422 per the WP-010 Contract.
 */
export class NoBaseShaError extends Error {
  readonly code = "NO_BASE_SHA";
  constructor(changeId: string) {
    super(`no base_sha recorded for this change: ${changeId}`);
    this.name = "NoBaseShaError";
  }
}

/**
 * Thrown by route handlers for malformed request input (e.g. missing
 * required query parameter). The mapper renders it as 400 BAD_REQUEST.
 */
export class BadRequestError extends Error {
  readonly code = "BAD_REQUEST";
  constructor(message: string) {
    super(message);
    this.name = "BadRequestError";
  }
}

interface ErrorEnvelope {
  error: string;
  code: string;
}

function envelope(
  err: { code?: string; message?: string },
  fallbackCode: string,
): ErrorEnvelope {
  return {
    error: err.message ?? "internal error",
    code: typeof err.code === "string" ? err.code : fallbackCode,
  };
}

/**
 * The error-handling middleware. Express recognises a 4-arg signature
 * (err, req, res, next) as the error layer; we keep the unused `next`
 * parameter so Express routes the right handler.
 */
export const errorMiddleware: ErrorRequestHandler = (
  err,
  _req: Request,
  res: Response,
  _next: NextFunction,
) => {
  if (err instanceof PathOutsideWorktreeError) {
    res.status(400).json(envelope(err, "PATH_OUTSIDE_WORKTREE"));
    return;
  }
  if (err instanceof NotADirectoryError) {
    res.status(400).json(envelope(err, "NOT_A_DIRECTORY"));
    return;
  }
  if (err instanceof IsADirectoryError) {
    res.status(400).json(envelope(err, "IS_A_DIRECTORY"));
    return;
  }
  if (err instanceof NotFoundError || err instanceof NoSuchChangeError) {
    res.status(404).json(envelope(err, "NOT_FOUND"));
    return;
  }
  if (err instanceof TimeoutError) {
    res.status(504).json(envelope(err, "TIMEOUT"));
    return;
  }
  if (err instanceof GitError) {
    res.status(400).json(envelope(err, "GIT_ERROR"));
    return;
  }
  if (err instanceof NoBaseShaError) {
    res.status(422).json(envelope(err, "NO_BASE_SHA"));
    return;
  }
  if (err instanceof BadRequestError) {
    res.status(400).json(envelope(err, "BAD_REQUEST"));
    return;
  }
  // Unknown — log a single line (no stack to the client) and return 500.
  // Note: console.error is the only place in this middleware that
  // touches the log stream; the per-request log lives in request-log.ts.
  // eslint-disable-next-line no-console
  console.error("unhandled error in route:", err);
  const message =
    err instanceof Error &&
    typeof err.message === "string" &&
    err.message.length > 0
      ? err.message
      : "internal error";
  res.status(500).json({ error: message, code: "INTERNAL_ERROR" });
};
