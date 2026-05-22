import { kwargsToParams, resultPayload } from '../helpers.js';
import type {
  AsyncSubprocessTransport,
  SubprocessTransport,
  TransportConfig,
} from '../transport.js';
import type {
  IndexAddResult,
  IndexFlipStatusResult,
  IndexListReadyResult,
  IndexMarkDownstreamBlockedResult,
  IndexReadConfigResult,
  IndexRegisterPendingDraftsResult,
} from '../types.js';

const BINARY = 'wpx-index';

function common(config: TransportConfig): Record<string, unknown> {
  return { project: config.project, repo_root: config.repoRoot };
}

export interface IndexFlipStatusParams {
  wp: string;
  to: string;
  expected?: string;
}

export interface IndexAddParams {
  wp: string;
  from_wp_file?: boolean;
  title?: string;
  primitive?: string;
  status?: string;
  depends_on?: string;
  blocks?: string;
  token_estimate?: string;
  tdd?: string;
}

export class IndexResource {
  constructor(
    private readonly transport: SubprocessTransport,
    private readonly config: TransportConfig,
  ) {}

  flipStatus(params: IndexFlipStatusParams): IndexFlipStatusResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'flip-status', {
        ...common(this.config),
        ...kwargsToParams(params),
      }),
    ) as unknown as IndexFlipStatusResult;
  }

  setStatus(params: { wp: string; to: string }): IndexFlipStatusResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'set-status', { ...common(this.config), ...params }),
    ) as unknown as IndexFlipStatusResult;
  }

  listReady(): IndexListReadyResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'list-ready', common(this.config)),
    ) as unknown as IndexListReadyResult;
  }

  readConfig(): IndexReadConfigResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'read-config', common(this.config)),
    ) as unknown as IndexReadConfigResult;
  }

  markDownstreamBlocked(params: { wp: string }): IndexMarkDownstreamBlockedResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'propagate-blocked', {
        ...common(this.config),
        ...params,
      }),
    ) as unknown as IndexMarkDownstreamBlockedResult;
  }

  add(params: IndexAddParams): IndexAddResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'add-wp', {
        ...common(this.config),
        ...kwargsToParams(params),
      }),
    ) as unknown as IndexAddResult;
  }

  registerPendingDrafts(): IndexRegisterPendingDraftsResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'sync-auto-drafts', common(this.config)),
    ) as unknown as IndexRegisterPendingDraftsResult;
  }
}

export class AsyncIndexResource {
  constructor(
    private readonly transport: AsyncSubprocessTransport,
    private readonly config: TransportConfig,
  ) {}

  async flipStatus(params: IndexFlipStatusParams): Promise<IndexFlipStatusResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'flip-status', {
        ...common(this.config),
        ...kwargsToParams(params),
      }),
    ) as unknown as IndexFlipStatusResult;
  }

  async setStatus(params: { wp: string; to: string }): Promise<IndexFlipStatusResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'set-status', { ...common(this.config), ...params }),
    ) as unknown as IndexFlipStatusResult;
  }

  async listReady(): Promise<IndexListReadyResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'list-ready', common(this.config)),
    ) as unknown as IndexListReadyResult;
  }

  async readConfig(): Promise<IndexReadConfigResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'read-config', common(this.config)),
    ) as unknown as IndexReadConfigResult;
  }

  async markDownstreamBlocked(params: { wp: string }): Promise<IndexMarkDownstreamBlockedResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'propagate-blocked', {
        ...common(this.config),
        ...params,
      }),
    ) as unknown as IndexMarkDownstreamBlockedResult;
  }

  async add(params: IndexAddParams): Promise<IndexAddResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'add-wp', {
        ...common(this.config),
        ...kwargsToParams(params),
      }),
    ) as unknown as IndexAddResult;
  }

  async registerPendingDrafts(): Promise<IndexRegisterPendingDraftsResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'sync-auto-drafts', common(this.config)),
    ) as unknown as IndexRegisterPendingDraftsResult;
  }
}
