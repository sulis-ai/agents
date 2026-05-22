import { kwargsToParams, resultPayload } from '../helpers.js';
import type {
  AsyncSubprocessTransport,
  SubprocessTransport,
  TransportConfig,
} from '../transport.js';
import type {
  TrainDoctorResult,
  TrainInspectResult,
  TrainOverrideResult,
  TrainQueueListResult,
  TrainRunResult,
  TrainStatusResult,
} from '../types.js';

const BINARY = 'wpx-train';

function common(config: TransportConfig, repo?: string): Record<string, unknown> {
  return kwargsToParams({
    project: config.project,
    repo_root: config.repoRoot,
    repo,
  });
}

export interface TrainQueueAddParams {
  wp: string;
  reason?: string;
  repo?: string;
}

export interface TrainRunParams {
  deploy_workflow: string;
  force?: boolean;
  staging_url?: string;
  health_path?: string;
  smoke_cmd?: string;
  ci_poll_interval?: number;
  deploy_poll_interval?: number;
  max_batch_size?: number;
  base_branch?: string;
  repo?: string;
}

export class TrainResource {
  constructor(
    private readonly transport: SubprocessTransport,
    private readonly config: TransportConfig,
  ) {}

  queueList(opts: { repo?: string } = {}): TrainQueueListResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'queue-list', common(this.config, opts.repo)),
    ) as unknown as TrainQueueListResult;
  }

  queueAdd(params: TrainQueueAddParams): TrainOverrideResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'queue-add', {
        ...common(this.config, params.repo),
        wp: params.wp,
        reason: params.reason ?? '',
      }),
    ) as unknown as TrainOverrideResult;
  }

  queueRemove(params: TrainQueueAddParams): TrainOverrideResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'queue-remove', {
        ...common(this.config, params.repo),
        wp: params.wp,
        reason: params.reason ?? '',
      }),
    ) as unknown as TrainOverrideResult;
  }

  status(opts: { repo?: string } = {}): TrainStatusResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'status', common(this.config, opts.repo)),
    ) as unknown as TrainStatusResult;
  }

  doctor(opts: { repo?: string } = {}): TrainDoctorResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'doctor', common(this.config, opts.repo)),
    ) as unknown as TrainDoctorResult;
  }

  /**
   * Inspect a train's in-flight or historical state.
   *
   * With train_id: returns the train's state snapshot (phase,
   * phase_history, per-WP outcomes, pause_reason + recovery_hint
   * when present).
   *
   * Without train_id: returns a listing of recent trains.
   */
  inspect(opts: { train_id?: string } = {}): TrainInspectResult {
    const params: Record<string, unknown> = {
      ...common(this.config, undefined),
      json: true,
    };
    if (opts.train_id !== undefined) {
      params.train_id = opts.train_id;
    }
    return resultPayload(
      this.transport.invoke(BINARY, 'inspect', params),
    ) as unknown as TrainInspectResult;
  }

  run(params: TrainRunParams): TrainRunResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'run', {
        ...common(this.config, params.repo),
        ...kwargsToParams({
          force: params.force ?? false,
          deploy_workflow: params.deploy_workflow,
          staging_url: params.staging_url,
          health_path: params.health_path,
          smoke_cmd: params.smoke_cmd,
          ci_poll_interval: params.ci_poll_interval,
          deploy_poll_interval: params.deploy_poll_interval,
          max_batch_size: params.max_batch_size ?? 5,
          base_branch: params.base_branch,
        }),
      }),
    ) as unknown as TrainRunResult;
  }
}

export class AsyncTrainResource {
  constructor(
    private readonly transport: AsyncSubprocessTransport,
    private readonly config: TransportConfig,
  ) {}

  async queueList(opts: { repo?: string } = {}): Promise<TrainQueueListResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'queue-list', common(this.config, opts.repo)),
    ) as unknown as TrainQueueListResult;
  }

  async queueAdd(params: TrainQueueAddParams): Promise<TrainOverrideResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'queue-add', {
        ...common(this.config, params.repo),
        wp: params.wp,
        reason: params.reason ?? '',
      }),
    ) as unknown as TrainOverrideResult;
  }

  async queueRemove(params: TrainQueueAddParams): Promise<TrainOverrideResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'queue-remove', {
        ...common(this.config, params.repo),
        wp: params.wp,
        reason: params.reason ?? '',
      }),
    ) as unknown as TrainOverrideResult;
  }

  async status(opts: { repo?: string } = {}): Promise<TrainStatusResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'status', common(this.config, opts.repo)),
    ) as unknown as TrainStatusResult;
  }

  async doctor(opts: { repo?: string } = {}): Promise<TrainDoctorResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'doctor', common(this.config, opts.repo)),
    ) as unknown as TrainDoctorResult;
  }

  async inspect(opts: { train_id?: string } = {}): Promise<TrainInspectResult> {
    const params: Record<string, unknown> = {
      ...common(this.config, undefined),
      json: true,
    };
    if (opts.train_id !== undefined) {
      params.train_id = opts.train_id;
    }
    return resultPayload(
      await this.transport.invoke(BINARY, 'inspect', params),
    ) as unknown as TrainInspectResult;
  }

  async run(params: TrainRunParams): Promise<TrainRunResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'run', {
        ...common(this.config, params.repo),
        ...kwargsToParams({
          force: params.force ?? false,
          deploy_workflow: params.deploy_workflow,
          staging_url: params.staging_url,
          health_path: params.health_path,
          smoke_cmd: params.smoke_cmd,
          ci_poll_interval: params.ci_poll_interval,
          deploy_poll_interval: params.deploy_poll_interval,
          max_batch_size: params.max_batch_size ?? 5,
          base_branch: params.base_branch,
        }),
      }),
    ) as unknown as TrainRunResult;
  }
}
