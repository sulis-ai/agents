import { kwargsToParams, resultPayload } from '../helpers.js';
import type {
  AsyncSubprocessTransport,
  SubprocessTransport,
  TransportConfig,
} from '../transport.js';
import type {
  TrainAbortResult,
  TrainDoctorResult,
  TrainInspectResult,
  TrainMarkGatesCompleteResult,
  TrainRetryWpResult,
  TrainSkipWpResult,
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
  /**
   * HD-007 — when true, the train pauses at the new `verifying_gates`
   * phase after deploy/health/smoke green instead of going directly to
   * terminal success. Emits outcome=`awaiting_gates` with a
   * `gate_handoff` envelope. Calling session dispatches Step 10.5 +
   * Step 11, then invokes `markGatesComplete` to finalise.
   */
  enable_gate_handoff?: boolean;
  repo?: string;
}

export interface TrainMarkGatesCompleteParams {
  train_id: string;
  /**
   * Optional path to the gate findings JSON produced by Step 10.5 +
   * Step 11. Recorded in the historical YAML record's
   * `gate_findings_path` field for audit.
   */
  gate_findings?: string | null;
  /**
   * When true, transitions the train to phase=failed,
   * outcome=gate_blocker (exit 1). The gate dispatchers are expected to
   * have already written per-WP BLOCKERs and drafted remediation WPs;
   * this call just records the train outcome (no ADR-212 revert).
   */
  critical_found?: boolean;
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
  /**
   * Resume a paused train (pre-merge phases only in v0.19.0a). See
   * OpenAPI train.resume for full semantics.
   */
  abort(params: { train_id: string }): TrainAbortResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'abort', {
        ...common(this.config, undefined),
        train_id: params.train_id,
      }),
    ) as unknown as TrainAbortResult;
  }

  skipWp(params: { train_id: string; wp: string }): TrainSkipWpResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'skip-wp', {
        ...common(this.config, undefined),
        train_id: params.train_id,
        wp: params.wp,
      }),
    ) as unknown as TrainSkipWpResult;
  }

  retryWp(params: { train_id: string; wp: string }): TrainRetryWpResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'retry-wp', {
        ...common(this.config, undefined),
        train_id: params.train_id,
        wp: params.wp,
      }),
    ) as unknown as TrainRetryWpResult;
  }

  resume(params: {
    train_id: string;
    deploy_workflow?: string;
    staging_url?: string;
    health_path?: string;
    smoke_cmd?: string;
    deploy_cap?: number;
    base_branch?: string;
    force?: boolean;
    strict_ci?: boolean;
  }): TrainRunResult {
    const callParams: Record<string, unknown> = {
      ...common(this.config, undefined),
      train_id: params.train_id,
    };
    if (params.deploy_workflow !== undefined) callParams.deploy_workflow = params.deploy_workflow;
    if (params.staging_url !== undefined) callParams.staging_url = params.staging_url;
    if (params.health_path !== undefined) callParams.health_path = params.health_path;
    if (params.smoke_cmd !== undefined) callParams.smoke_cmd = params.smoke_cmd;
    if (params.deploy_cap !== undefined) callParams.deploy_cap = params.deploy_cap;
    if (params.base_branch !== undefined) callParams.base_branch = params.base_branch;
    if (params.force) callParams.force = true;
    if (params.strict_ci) callParams.strict_ci = true;
    return resultPayload(
      this.transport.invoke(BINARY, 'resume', callParams),
    ) as unknown as TrainRunResult;
  }

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
          enable_gate_handoff: params.enable_gate_handoff ?? false,
        }),
      }),
    ) as unknown as TrainRunResult;
  }

  /**
   * HD-007 — finalise a train paused at `verifying_gates`. Pair with
   * `train.run({ enable_gate_handoff: true })`. Two terminal paths:
   *
   * - **Clean gates** (default): transitions to `phase=success`,
   *   `outcome=success`.
   * - **CRITICAL finding** (`critical_found: true`): transitions to
   *   `phase=failed`, `outcome=gate_blocker`. The gate dispatchers are
   *   expected to have written per-WP BLOCKERs + drafted remediation WPs
   *   already; this call records the train outcome only (no ADR-212
   *   revert).
   *
   * Errors when the train is not in `phase=verifying_gates`.
   */
  markGatesComplete(
    params: TrainMarkGatesCompleteParams,
  ): TrainMarkGatesCompleteResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'mark-gates-complete', {
        ...common(this.config, params.repo),
        ...kwargsToParams({
          train_id: params.train_id,
          gate_findings: params.gate_findings,
          critical_found: params.critical_found ?? false,
        }),
      }),
    ) as unknown as TrainMarkGatesCompleteResult;
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

  async abort(params: { train_id: string }): Promise<TrainAbortResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'abort', {
        ...common(this.config, undefined),
        train_id: params.train_id,
      }),
    ) as unknown as TrainAbortResult;
  }

  async skipWp(params: { train_id: string; wp: string }): Promise<TrainSkipWpResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'skip-wp', {
        ...common(this.config, undefined),
        train_id: params.train_id,
        wp: params.wp,
      }),
    ) as unknown as TrainSkipWpResult;
  }

  async retryWp(params: { train_id: string; wp: string }): Promise<TrainRetryWpResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'retry-wp', {
        ...common(this.config, undefined),
        train_id: params.train_id,
        wp: params.wp,
      }),
    ) as unknown as TrainRetryWpResult;
  }

  async resume(params: {
    train_id: string;
    deploy_workflow?: string;
    staging_url?: string;
    health_path?: string;
    smoke_cmd?: string;
    deploy_cap?: number;
    base_branch?: string;
    force?: boolean;
    strict_ci?: boolean;
  }): Promise<TrainRunResult> {
    const callParams: Record<string, unknown> = {
      ...common(this.config, undefined),
      train_id: params.train_id,
    };
    if (params.deploy_workflow !== undefined) callParams.deploy_workflow = params.deploy_workflow;
    if (params.staging_url !== undefined) callParams.staging_url = params.staging_url;
    if (params.health_path !== undefined) callParams.health_path = params.health_path;
    if (params.smoke_cmd !== undefined) callParams.smoke_cmd = params.smoke_cmd;
    if (params.deploy_cap !== undefined) callParams.deploy_cap = params.deploy_cap;
    if (params.base_branch !== undefined) callParams.base_branch = params.base_branch;
    if (params.force) callParams.force = true;
    if (params.strict_ci) callParams.strict_ci = true;
    return resultPayload(
      await this.transport.invoke(BINARY, 'resume', callParams),
    ) as unknown as TrainRunResult;
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
          enable_gate_handoff: params.enable_gate_handoff ?? false,
        }),
      }),
    ) as unknown as TrainRunResult;
  }

  /**
   * Async parity for `TrainResource.markGatesComplete`. HD-007 —
   * finalise a train paused at `verifying_gates`.
   */
  async markGatesComplete(
    params: TrainMarkGatesCompleteParams,
  ): Promise<TrainMarkGatesCompleteResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'mark-gates-complete', {
        ...common(this.config, params.repo),
        ...kwargsToParams({
          train_id: params.train_id,
          gate_findings: params.gate_findings,
          critical_found: params.critical_found ?? false,
        }),
      }),
    ) as unknown as TrainMarkGatesCompleteResult;
  }
}
