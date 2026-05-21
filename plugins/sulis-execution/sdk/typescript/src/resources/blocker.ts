import { kwargsToParams, resultPayload } from '../helpers.js';
import type {
  AsyncSubprocessTransport,
  SubprocessTransport,
  TransportConfig,
} from '../transport.js';
import type { BlockerArchiveResult, BlockerWriteResult } from '../types.js';

const BINARY = 'wpx-blocker';

export interface BlockerWriteParams {
  wp: string;
  title: string;
  step: string;
  trigger: 'scope-guard' | 'budget-exhausted' | 'five-whys-non-convergence';
  observation: string;
  root_cause: string;
  scope: 'in-scope-budget-exhausted' | 'out-of-scope' | 'indeterminate';
  plain_english: string;
  suggested_next: string;
  five_whys_json?: string;
  scope_reason?: string;
  attempts_json?: string;
  force?: boolean;
}

function common(config: TransportConfig): Record<string, unknown> {
  return { project: config.project, repo_root: config.repoRoot };
}

export class BlockerResource {
  constructor(
    private readonly transport: SubprocessTransport,
    private readonly config: TransportConfig,
  ) {}

  write(params: BlockerWriteParams): BlockerWriteResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'write', {
        ...common(this.config),
        ...kwargsToParams(params),
      }),
    ) as unknown as BlockerWriteResult;
  }

  archive(params: { wp: string }): BlockerArchiveResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'archive', { ...common(this.config), ...params }),
    ) as unknown as BlockerArchiveResult;
  }
}

export class AsyncBlockerResource {
  constructor(
    private readonly transport: AsyncSubprocessTransport,
    private readonly config: TransportConfig,
  ) {}

  async write(params: BlockerWriteParams): Promise<BlockerWriteResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'write', {
        ...common(this.config),
        ...kwargsToParams(params),
      }),
    ) as unknown as BlockerWriteResult;
  }

  async archive(params: { wp: string }): Promise<BlockerArchiveResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'archive', { ...common(this.config), ...params }),
    ) as unknown as BlockerArchiveResult;
  }
}
