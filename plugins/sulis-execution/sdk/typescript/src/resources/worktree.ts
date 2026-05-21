import { resultPayload } from '../helpers.js';
import type {
  AsyncSubprocessTransport,
  SubprocessTransport,
  TransportConfig,
} from '../transport.js';
import type { WorktreeCreateResult, WorktreeRemoveResult } from '../types.js';

const BINARY = 'wpx-worktree';

function common(config: TransportConfig): Record<string, unknown> {
  return { project: config.project, repo_root: config.repoRoot };
}

export class WorktreeResource {
  constructor(
    private readonly transport: SubprocessTransport,
    private readonly config: TransportConfig,
  ) {}

  create(params: {
    wp: string;
    branch: string;
    worktree_path: string;
  }): WorktreeCreateResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'create', { ...common(this.config), ...params }),
    ) as unknown as WorktreeCreateResult;
  }

  remove(params: {
    wp: string;
    worktree_path: string;
    force?: boolean;
    tolerate_missing?: boolean;
  }): WorktreeRemoveResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'remove', {
        ...common(this.config),
        force: false,
        tolerate_missing: false,
        ...params,
      }),
    ) as unknown as WorktreeRemoveResult;
  }
}

export class AsyncWorktreeResource {
  constructor(
    private readonly transport: AsyncSubprocessTransport,
    private readonly config: TransportConfig,
  ) {}

  async create(params: {
    wp: string;
    branch: string;
    worktree_path: string;
  }): Promise<WorktreeCreateResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'create', { ...common(this.config), ...params }),
    ) as unknown as WorktreeCreateResult;
  }

  async remove(params: {
    wp: string;
    worktree_path: string;
    force?: boolean;
    tolerate_missing?: boolean;
  }): Promise<WorktreeRemoveResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'remove', {
        ...common(this.config),
        force: false,
        tolerate_missing: false,
        ...params,
      }),
    ) as unknown as WorktreeRemoveResult;
  }
}
