import { kwargsToParams, resultPayload } from '../helpers.js';
import type {
  AsyncSubprocessTransport,
  SubprocessTransport,
  TransportConfig,
} from '../transport.js';
import type { Step12WrapResult } from '../types.js';

const BINARY = 'wpx-step12';

function common(config: TransportConfig): Record<string, unknown> {
  return { project: config.project, repo_root: config.repoRoot };
}

export interface Step12WrapParams {
  wp: string;
  branch: string;
  pipeline_result: string;
  pre_squash_sha?: string;
  worktree_path?: string;
  post_deploy_verification?: string;
}

export class Step12Resource {
  constructor(
    private readonly transport: SubprocessTransport,
    private readonly config: TransportConfig,
  ) {}

  wrap(params: Step12WrapParams): Step12WrapResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'wrap', {
        ...common(this.config),
        ...kwargsToParams(params),
      }),
    ) as unknown as Step12WrapResult;
  }
}

export class AsyncStep12Resource {
  constructor(
    private readonly transport: AsyncSubprocessTransport,
    private readonly config: TransportConfig,
  ) {}

  async wrap(params: Step12WrapParams): Promise<Step12WrapResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'wrap', {
        ...common(this.config),
        ...kwargsToParams(params),
      }),
    ) as unknown as Step12WrapResult;
  }
}
