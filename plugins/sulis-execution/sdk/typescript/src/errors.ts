/**
 * Error hierarchy for the sulis-execution SDK.
 *
 * Per the agent-consumable SDK spec v0.2.0 Part 3, errors are organised
 * into three universal outcome categories:
 *
 * - ProtocolError: the transport itself failed (subprocess couldn't run)
 * - ExpectedError: the operation reached the implementation but reported
 *   a deterministic failure (bad inputs, validation, conflict)
 * - InternalError: the operation crashed or produced an unexpected mode
 *
 * Class names are identical to the Python SDK per the parity contract
 * (v0.2.0 Part 6).
 */

export interface SulisExecutionErrorOptions {
  transportCode?: number | string | null;
  correlationId?: string | null;
  body?: Record<string, unknown> | null;
  code?: string | null;
  context?: Record<string, unknown> | null;
}

export class SulisExecutionError extends Error {
  category: 'protocol' | 'expected' | 'internal' = 'internal';
  transportCode?: number | string | null;
  correlationId?: string | null;
  body?: Record<string, unknown> | null;
  code?: string | null;
  context?: Record<string, unknown> | null;

  constructor(message: string, options: SulisExecutionErrorOptions = {}) {
    super(message);
    this.name = this.constructor.name;
    this.transportCode = options.transportCode ?? null;
    this.correlationId = options.correlationId ?? null;
    this.body = options.body ?? null;
    this.code = options.code ?? null;
    this.context = options.context ?? null;
  }
}

// ─── ProtocolError ────────────────────────────────────────────────────

export class ProtocolError extends SulisExecutionError {
  category: 'protocol' | 'expected' | 'internal' = 'protocol';
}

/** Raised when the wpx-* binary or sulis-change binary cannot be located. */
export class BinaryNotFoundError extends ProtocolError {}

// ─── ExpectedError ─────────────────────────────────────────────────────

export class ExpectedError extends SulisExecutionError {
  category: 'protocol' | 'expected' | 'internal' = 'expected';
}

/** An argument failed validation. */
export class InvalidArgumentError extends ExpectedError {}

// ─── InternalError ─────────────────────────────────────────────────────

export class InternalError extends SulisExecutionError {
  category: 'protocol' | 'expected' | 'internal' = 'internal';
}

/** The CLI produced output that couldn't be parsed. */
export class UnexpectedOutputError extends InternalError {}
