// WP-010 — tiny async-handler shim.
//
// Express 5 natively passes async rejections to `next(err)`, but
// declaring the wrapper explicitly keeps the route signatures uniform
// and version-independent. Every route file imports this.
//
// One adopter today (six routes), so EP-03's "extract at 2 consumers"
// threshold has already fired — this is the shared primitive.

import type { Request, Response, NextFunction, RequestHandler } from "express";

type AsyncHandler = (
  req: Request,
  res: Response,
  next: NextFunction,
) => Promise<unknown>;

/**
 * Wrap an `async` route handler so any thrown / rejected error is
 * forwarded to Express's error middleware. The route file's exported
 * function is the unwrapped async fn; this shim is what `app.get()`
 * registers.
 */
export function asyncHandler(fn: AsyncHandler): RequestHandler {
  return (req, res, next) => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
}
