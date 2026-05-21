/**
 * @sulis-ai/execution — typed TypeScript SDK for the sulis-execution
 * plugin's CLI tools.
 *
 * Per the agent-consumable SDK spec at
 * plugins/sulis-execution/docs/research/agent-consumable-sdk-spec.md (v0.2.0).
 *
 * Transport: subprocess (v0.2.0 Part 4.3) — spawns the underlying CLI
 * binaries (wpx-pipeline, wpx-train, sulis-change, etc.) via Node's
 * child_process; maps exit codes 0/1/2 to outcome categories (Protocol /
 * Expected / Internal) per v0.2.0 Part 3.
 *
 * 38 operations across 10 resources: pipeline (1), train (6), index (7),
 * journal (10), blocker (2), findings (2), wp (2), worktree (2),
 * step12 (1), change (5).
 */

export { SulisExecution, AsyncSulisExecution } from './client.js';
export type { SulisExecutionOptions } from './client.js';

export {
  SulisExecutionError,
  ProtocolError,
  ExpectedError,
  InternalError,
  BinaryNotFoundError,
  InvalidArgumentError,
  UnexpectedOutputError,
} from './errors.js';
export type { SulisExecutionErrorOptions } from './errors.js';

export type * from './types.js';
