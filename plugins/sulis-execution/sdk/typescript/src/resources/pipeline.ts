import { kwargsToParams, resultPayload } from '../helpers.js';
import type {
  AsyncSubprocessTransport,
  SubprocessTransport,
  TransportConfig,
} from '../transport.js';
import type { PipelineResult } from '../types.js';

const BINARY = 'wpx-pipeline';

export interface PipelineRunParams {
  wp: string;
  branch: string;
  dev_sha_at_creation: string;
  deploy_workflow: string;
  repo?: string;
  worktree_path?: string;
  staging_url?: string;
  health_path?: string;
  smoke_cmd?: string;
  ci_poll_interval?: number;
  deploy_poll_interval?: number;
  skip_ci_poll?: boolean;
  base_branch?: string;
}

function buildParams(
  config: TransportConfig,
  params: PipelineRunParams,
): Record<string, unknown> {
  return kwargsToParams({
    project: config.project,
    repo_root: config.repoRoot,
    ...params,
  });
}

export class PipelineResource {
  constructor(
    private readonly transport: SubprocessTransport,
    private readonly config: TransportConfig,
  ) {}

  run(params: PipelineRunParams): PipelineResult {
    const envelope = this.transport.invoke(
      BINARY,
      'run',
      buildParams(this.config, params),
    );
    return resultPayload(envelope) as unknown as PipelineResult;
  }
}

export class AsyncPipelineResource {
  constructor(
    private readonly transport: AsyncSubprocessTransport,
    private readonly config: TransportConfig,
  ) {}

  async run(params: PipelineRunParams): Promise<PipelineResult> {
    const envelope = await this.transport.invoke(
      BINARY,
      'run',
      buildParams(this.config, params),
    );
    return resultPayload(envelope) as unknown as PipelineResult;
  }
}
