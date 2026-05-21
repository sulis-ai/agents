import { resultPayload } from '../helpers.js';
import type {
  AsyncSubprocessTransport,
  SubprocessTransport,
  TransportConfig,
} from '../transport.js';
import type {
  WpAppendEvidenceResult,
  WpReadFrontmatterResult,
} from '../types.js';

const BINARY = 'wpx-wp';

function common(config: TransportConfig): Record<string, unknown> {
  return { project: config.project, repo_root: config.repoRoot };
}

export class WpResource {
  constructor(
    private readonly transport: SubprocessTransport,
    private readonly config: TransportConfig,
  ) {}

  readFrontmatter(params: { wp: string; field: string }): WpReadFrontmatterResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'read-frontmatter', {
        ...common(this.config),
        ...params,
      }),
    ) as unknown as WpReadFrontmatterResult;
  }

  appendEvidence(params: {
    wp: string;
    evidence_json: string;
  }): WpAppendEvidenceResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'append-evidence', {
        ...common(this.config),
        ...params,
      }),
    ) as unknown as WpAppendEvidenceResult;
  }
}

export class AsyncWpResource {
  constructor(
    private readonly transport: AsyncSubprocessTransport,
    private readonly config: TransportConfig,
  ) {}

  async readFrontmatter(params: {
    wp: string;
    field: string;
  }): Promise<WpReadFrontmatterResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'read-frontmatter', {
        ...common(this.config),
        ...params,
      }),
    ) as unknown as WpReadFrontmatterResult;
  }

  async appendEvidence(params: {
    wp: string;
    evidence_json: string;
  }): Promise<WpAppendEvidenceResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'append-evidence', {
        ...common(this.config),
        ...params,
      }),
    ) as unknown as WpAppendEvidenceResult;
  }
}
