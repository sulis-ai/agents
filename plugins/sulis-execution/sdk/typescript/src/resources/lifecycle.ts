import { kwargsToParams, resultPayload } from '../helpers.js';
import type {
  AsyncSubprocessTransport,
  SubprocessTransport,
  TransportConfig,
} from '../transport.js';
import type { LifecycleCompleteResult } from '../types.js';

/**
 * Lifecycle resource — atomically complete a Work Package's lifecycle.
 *
 * Underlying CLI: `wpx-step12 wrap`. The SDK wraps that under cleaner
 * names (`lifecycle.complete` vs the CLI's `step12 wrap`).
 */

const BINARY = 'wpx-step12';
const SUBCOMMAND = 'wrap'; // SDK method is `complete`; CLI keeps `wrap`

function common(config: TransportConfig): Record<string, unknown> {
  return { project: config.project, repo_root: config.repoRoot };
}

export interface LifecycleCompleteParams {
  wp: string;
  branch: string;
  pipeline_result: string;
  pre_squash_sha?: string;
  worktree_path?: string;
  post_deploy_verification?: string;
}

export class LifecycleResource {
  constructor(
    private readonly transport: SubprocessTransport,
    private readonly config: TransportConfig,
  ) {}

  /**
   * Atomically complete a Work Package's lifecycle.
   *
   * Chains three operations fail-fast: append evidence to the WP file,
   * flip INDEX status to `done` (expected: in_progress → done), remove
   * the worktree. If any fails, returns details of what succeeded vs
   * failed.
   */
  complete(params: LifecycleCompleteParams): LifecycleCompleteResult {
    return resultPayload(
      this.transport.invoke(BINARY, SUBCOMMAND, {
        ...common(this.config),
        ...kwargsToParams(params),
      }),
    ) as unknown as LifecycleCompleteResult;
  }
}

export class AsyncLifecycleResource {
  constructor(
    private readonly transport: AsyncSubprocessTransport,
    private readonly config: TransportConfig,
  ) {}

  async complete(
    params: LifecycleCompleteParams,
  ): Promise<LifecycleCompleteResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, SUBCOMMAND, {
        ...common(this.config),
        ...kwargsToParams(params),
      }),
    ) as unknown as LifecycleCompleteResult;
  }
}
