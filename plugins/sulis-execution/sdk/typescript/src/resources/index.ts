import { kwargsToParams, resultPayload } from '../helpers.js';
import type {
  AsyncSubprocessTransport,
  SubprocessTransport,
  TransportConfig,
} from '../transport.js';
import type {
  IndexAddWpResult,
  IndexFlipStatusResult,
  IndexListReadyResult,
  IndexPropagateBlockedResult,
  IndexReadConfigResult,
  IndexSyncAutoDraftsResult,
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

export interface IndexAddWpParams {
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

  propagateBlocked(params: { wp: string }): IndexPropagateBlockedResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'propagate-blocked', {
        ...common(this.config),
        ...params,
      }),
    ) as unknown as IndexPropagateBlockedResult;
  }

  addWp(params: IndexAddWpParams): IndexAddWpResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'add-wp', {
        ...common(this.config),
        ...kwargsToParams(params),
      }),
    ) as unknown as IndexAddWpResult;
  }

  syncAutoDrafts(): IndexSyncAutoDraftsResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'sync-auto-drafts', common(this.config)),
    ) as unknown as IndexSyncAutoDraftsResult;
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

  async propagateBlocked(params: { wp: string }): Promise<IndexPropagateBlockedResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'propagate-blocked', {
        ...common(this.config),
        ...params,
      }),
    ) as unknown as IndexPropagateBlockedResult;
  }

  async addWp(params: IndexAddWpParams): Promise<IndexAddWpResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'add-wp', {
        ...common(this.config),
        ...kwargsToParams(params),
      }),
    ) as unknown as IndexAddWpResult;
  }

  async syncAutoDrafts(): Promise<IndexSyncAutoDraftsResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'sync-auto-drafts', common(this.config)),
    ) as unknown as IndexSyncAutoDraftsResult;
  }
}
