import { resultPayload } from '../helpers.js';
import type {
  AsyncSubprocessTransport,
  SubprocessTransport,
  TransportConfig,
} from '../transport.js';
import type {
  WorkPackageAppendEvidenceResult,
  WorkPackageReadMetadataResult,
} from '../types.js';

/**
 * Work Package resource — wraps `wpx-wp` subcommands.
 *
 * Underlying CLI: `wpx-wp`. The SDK exposes `readMetadata` instead of
 * the CLI's `read-frontmatter` (which leaks markdown-author jargon).
 */

const BINARY = 'wpx-wp';

function common(config: TransportConfig): Record<string, unknown> {
  return { project: config.project, repo_root: config.repoRoot };
}

export class WorkPackageResource {
  constructor(
    private readonly transport: SubprocessTransport,
    private readonly config: TransportConfig,
  ) {}

  /** Read frontmatter metadata from a WP file. CLI subcommand: read-frontmatter. */
  readMetadata(params: {
    wp: string;
    field: string;
  }): WorkPackageReadMetadataResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'read-frontmatter', {
        ...common(this.config),
        ...params,
      }),
    ) as unknown as WorkPackageReadMetadataResult;
  }

  /** Append `## Acceptance Evidence` to a WP file. */
  appendEvidence(params: {
    wp: string;
    evidence_json: string;
  }): WorkPackageAppendEvidenceResult {
    return resultPayload(
      this.transport.invoke(BINARY, 'append-evidence', {
        ...common(this.config),
        ...params,
      }),
    ) as unknown as WorkPackageAppendEvidenceResult;
  }
}

export class AsyncWorkPackageResource {
  constructor(
    private readonly transport: AsyncSubprocessTransport,
    private readonly config: TransportConfig,
  ) {}

  async readMetadata(params: {
    wp: string;
    field: string;
  }): Promise<WorkPackageReadMetadataResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'read-frontmatter', {
        ...common(this.config),
        ...params,
      }),
    ) as unknown as WorkPackageReadMetadataResult;
  }

  async appendEvidence(params: {
    wp: string;
    evidence_json: string;
  }): Promise<WorkPackageAppendEvidenceResult> {
    return resultPayload(
      await this.transport.invoke(BINARY, 'append-evidence', {
        ...common(this.config),
        ...params,
      }),
    ) as unknown as WorkPackageAppendEvidenceResult;
  }
}
