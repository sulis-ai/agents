import { kwargsToParams, resultPayload } from '../helpers.js';
import type {
  AsyncSubprocessTransport,
  SubprocessTransport,
  TransportConfig,
} from '../transport.js';
import type {
  FindingsAutoDraftWpResult,
  FindingsRegisterResult,
} from '../types.js';

const BINARY = 'wpx-findings';

function common(config: TransportConfig): Record<string, unknown> {
  return { project: config.project, repo_root: config.repoRoot };
}

export interface FindingsRegisterParams {
  wp: string;
  severity: 'CRITICAL' | 'CONCERN' | 'ADVISORY';
  summary: string;
  file: string;
  evidence_json?: string;
  suggested_fix?: string;
  primitive?: string;
}

export interface FindingsAutoDraftWpParams {
  source_finding: string;
  source_wp: string;
  auto_wp_id: string;
  severity: 'CONCERN' | 'ADVISORY';
  primitive?: 'Secure' | 'Harden' | 'Instrument' | 'Gate';
}

export class FindingsResource {
  constructor(
    private readonly transport: SubprocessTransport,
    private readonly config: TransportConfig,
  ) {}

  register(params: FindingsRegisterParams): FindingsRegisterResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'register', {
        ...common(this.config),
        ...kwargsToParams(params),
      }),
    ) as unknown as FindingsRegisterResult;
  }

  autoDraftWp(params: FindingsAutoDraftWpParams): FindingsAutoDraftWpResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'auto-draft-wp', {
        ...common(this.config),
        primitive: 'Secure',
        ...params,
      }),
    ) as unknown as FindingsAutoDraftWpResult;
  }
}

export class AsyncFindingsResource {
  constructor(
    private readonly transport: AsyncSubprocessTransport,
    private readonly config: TransportConfig,
  ) {}

  async register(params: FindingsRegisterParams): Promise<FindingsRegisterResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'register', {
        ...common(this.config),
        ...kwargsToParams(params),
      }),
    ) as unknown as FindingsRegisterResult;
  }

  async autoDraftWp(
    params: FindingsAutoDraftWpParams,
  ): Promise<FindingsAutoDraftWpResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'auto-draft-wp', {
        ...common(this.config),
        primitive: 'Secure',
        ...params,
      }),
    ) as unknown as FindingsAutoDraftWpResult;
  }
}
