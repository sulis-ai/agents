import { kwargsToParams, resultPayload } from '../helpers.js';
import type {
  AsyncSubprocessTransport,
  SubprocessTransport,
  TransportConfig,
} from '../transport.js';
import type {
  JournalAddPlanItemResult,
  JournalAttemptResult,
  JournalMarkPlanItemResult,
  JournalPathResult,
  JournalPostdeployResult,
  JournalPreflightResult,
  JournalReadResult,
  JournalSeedPlanResult,
  JournalStepResult,
} from '../types.js';

const BINARY = 'wpx-journal';

function common(config: TransportConfig): Record<string, unknown> {
  return { project: config.project, repo_root: config.repoRoot };
}

interface BothResources {
  invoke(binary: string, sub: string, params: Record<string, unknown>): unknown;
}

// Reusable per-binding implementations by composing the transport.
// We split sync + async classes below for the same parity contract as Python.

export class JournalResource {
  constructor(
    private readonly transport: SubprocessTransport,
    private readonly config: TransportConfig,
  ) {}

  init(params: { wp: string; force?: boolean }): JournalPathResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'init', {
        ...common(this.config),
        ...kwargsToParams(params),
      }),
    ) as unknown as JournalPathResult;
  }

  startStep(params: { wp: string; step: number }): JournalStepResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'start-step', { ...common(this.config), ...params }),
    ) as unknown as JournalStepResult;
  }

  completeStep(params: {
    wp: string;
    step: number;
    outcome: string;
  }): JournalStepResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'complete-step', {
        ...common(this.config),
        ...params,
      }),
    ) as unknown as JournalStepResult;
  }

  recordAttempt(params: {
    wp: string;
    step: number;
    attempt: number;
    failure: string;
    root_cause: string;
    change: string;
    outcome: string;
  }): JournalAttemptResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'record-attempt', {
        ...common(this.config),
        ...params,
      }),
    ) as unknown as JournalAttemptResult;
  }

  recordPreflight(params: {
    wp: string;
    tool: string;
    status: string;
    fallback?: string;
  }): JournalPreflightResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'record-preflight', {
        ...common(this.config),
        ...kwargsToParams(params),
      }),
    ) as unknown as JournalPreflightResult;
  }

  recordPostdeploy(params: {
    wp: string;
    verdict: string;
    findings_json?: string;
  }): JournalPostdeployResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'record-postdeploy', {
        ...common(this.config),
        ...kwargsToParams(params),
      }),
    ) as unknown as JournalPostdeployResult;
  }

  seedPlan(params: {
    wp: string;
    approach: string;
    plan_json: string;
    force?: boolean;
  }): JournalSeedPlanResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'seed-plan', {
        ...common(this.config),
        ...params,
      }),
    ) as unknown as JournalSeedPlanResult;
  }

  markPlanItem(params: {
    wp: string;
    item: number;
    status: string;
    expected?: string;
    notes?: string;
  }): JournalMarkPlanItemResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'mark-plan-item', {
        ...common(this.config),
        ...kwargsToParams(params),
      }),
    ) as unknown as JournalMarkPlanItemResult;
  }

  addPlanItem(params: {
    wp: string;
    description: string;
    step: string;
    notes?: string;
  }): JournalAddPlanItemResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'add-plan-item', {
        ...common(this.config),
        ...kwargsToParams(params),
      }),
    ) as unknown as JournalAddPlanItemResult;
  }

  read(params: { wp: string; field: string }): JournalReadResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'read', { ...common(this.config), ...params }),
    ) as unknown as JournalReadResult;
  }
}

export class AsyncJournalResource {
  constructor(
    private readonly transport: AsyncSubprocessTransport,
    private readonly config: TransportConfig,
  ) {}

  async init(params: { wp: string; force?: boolean }): Promise<JournalPathResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'init', {
        ...common(this.config),
        ...kwargsToParams(params),
      }),
    ) as unknown as JournalPathResult;
  }

  async startStep(params: { wp: string; step: number }): Promise<JournalStepResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'start-step', { ...common(this.config), ...params }),
    ) as unknown as JournalStepResult;
  }

  async completeStep(params: {
    wp: string;
    step: number;
    outcome: string;
  }): Promise<JournalStepResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'complete-step', {
        ...common(this.config),
        ...params,
      }),
    ) as unknown as JournalStepResult;
  }

  async recordAttempt(params: {
    wp: string;
    step: number;
    attempt: number;
    failure: string;
    root_cause: string;
    change: string;
    outcome: string;
  }): Promise<JournalAttemptResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'record-attempt', {
        ...common(this.config),
        ...params,
      }),
    ) as unknown as JournalAttemptResult;
  }

  async recordPreflight(params: {
    wp: string;
    tool: string;
    status: string;
    fallback?: string;
  }): Promise<JournalPreflightResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'record-preflight', {
        ...common(this.config),
        ...kwargsToParams(params),
      }),
    ) as unknown as JournalPreflightResult;
  }

  async recordPostdeploy(params: {
    wp: string;
    verdict: string;
    findings_json?: string;
  }): Promise<JournalPostdeployResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'record-postdeploy', {
        ...common(this.config),
        ...kwargsToParams(params),
      }),
    ) as unknown as JournalPostdeployResult;
  }

  async seedPlan(params: {
    wp: string;
    approach: string;
    plan_json: string;
    force?: boolean;
  }): Promise<JournalSeedPlanResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'seed-plan', {
        ...common(this.config),
        ...params,
      }),
    ) as unknown as JournalSeedPlanResult;
  }

  async markPlanItem(params: {
    wp: string;
    item: number;
    status: string;
    expected?: string;
    notes?: string;
  }): Promise<JournalMarkPlanItemResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'mark-plan-item', {
        ...common(this.config),
        ...kwargsToParams(params),
      }),
    ) as unknown as JournalMarkPlanItemResult;
  }

  async addPlanItem(params: {
    wp: string;
    description: string;
    step: string;
    notes?: string;
  }): Promise<JournalAddPlanItemResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'add-plan-item', {
        ...common(this.config),
        ...kwargsToParams(params),
      }),
    ) as unknown as JournalAddPlanItemResult;
  }

  async read(params: { wp: string; field: string }): Promise<JournalReadResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'read', { ...common(this.config), ...params }),
    ) as unknown as JournalReadResult;
  }
}
