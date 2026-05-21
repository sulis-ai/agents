import { resultPayload } from '../helpers.js';
import type {
  AsyncSubprocessTransport,
  SubprocessTransport,
  TransportConfig,
} from '../transport.js';
import type {
  ChangeAdoptResult,
  ChangeFinishResult,
  ChangeListResult,
  ChangeStartResult,
  ChangeStatusResult,
} from '../types.js';

const BINARY = 'sulis-change';

function common(config: TransportConfig): Record<string, unknown> {
  return { repo_root: config.repoRoot };
}

export interface ChangeStartParams {
  slug: string;
  primitive?: string;
  base?: string;
}

export interface ChangeAdoptParams {
  slug: string;
  primitive?: string;
  base?: string;
  mode?: 'forward' | 'rewrite';
  remote_ref?: string;
  force?: boolean;
}

export interface ChangeFinishParams {
  slug: string;
  primitive?: string;
  base?: string;
  merge?: boolean;
  pr?: boolean;
  no_cleanup?: boolean;
}

export class ChangeResource {
  constructor(
    private readonly transport: SubprocessTransport,
    private readonly config: TransportConfig,
  ) {}

  start(params: ChangeStartParams): ChangeStartResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'start', {
        ...common(this.config),
        primitive: 'feat',
        base: 'dev',
        ...params,
      }),
    ) as unknown as ChangeStartResult;
  }

  adopt(params: ChangeAdoptParams): ChangeAdoptResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'adopt', {
        ...common(this.config),
        primitive: 'feat',
        base: 'dev',
        mode: 'forward',
        remote_ref: 'origin/dev',
        force: false,
        ...params,
      }),
    ) as unknown as ChangeAdoptResult;
  }

  finish(params: ChangeFinishParams): ChangeFinishResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'finish', {
        ...common(this.config),
        primitive: 'feat',
        base: 'dev',
        merge: false,
        pr: false,
        no_cleanup: false,
        ...params,
      }),
    ) as unknown as ChangeFinishResult;
  }

  list(params: { base?: string } = {}): ChangeListResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'list', {
        ...common(this.config),
        base: 'dev',
        ...params,
      }),
    ) as unknown as ChangeListResult;
  }

  status(params: {
    slug: string;
    primitive?: string;
    base?: string;
  }): ChangeStatusResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'status', {
        ...common(this.config),
        primitive: 'feat',
        base: 'dev',
        ...params,
      }),
    ) as unknown as ChangeStatusResult;
  }
}

export class AsyncChangeResource {
  constructor(
    private readonly transport: AsyncSubprocessTransport,
    private readonly config: TransportConfig,
  ) {}

  async start(params: ChangeStartParams): Promise<ChangeStartResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'start', {
        ...common(this.config),
        primitive: 'feat',
        base: 'dev',
        ...params,
      }),
    ) as unknown as ChangeStartResult;
  }

  async adopt(params: ChangeAdoptParams): Promise<ChangeAdoptResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'adopt', {
        ...common(this.config),
        primitive: 'feat',
        base: 'dev',
        mode: 'forward',
        remote_ref: 'origin/dev',
        force: false,
        ...params,
      }),
    ) as unknown as ChangeAdoptResult;
  }

  async finish(params: ChangeFinishParams): Promise<ChangeFinishResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'finish', {
        ...common(this.config),
        primitive: 'feat',
        base: 'dev',
        merge: false,
        pr: false,
        no_cleanup: false,
        ...params,
      }),
    ) as unknown as ChangeFinishResult;
  }

  async list(params: { base?: string } = {}): Promise<ChangeListResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'list', {
        ...common(this.config),
        base: 'dev',
        ...params,
      }),
    ) as unknown as ChangeListResult;
  }

  async status(params: {
    slug: string;
    primitive?: string;
    base?: string;
  }): Promise<ChangeStatusResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'status', {
        ...common(this.config),
        primitive: 'feat',
        base: 'dev',
        ...params,
      }),
    ) as unknown as ChangeStatusResult;
  }
}
