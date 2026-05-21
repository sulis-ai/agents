import {
  AsyncSubprocessTransport,
  SubprocessTransport,
  type TransportConfig,
} from './transport.js';
import { BlockerResource, AsyncBlockerResource } from './resources/blocker.js';
import { ChangeResource, AsyncChangeResource } from './resources/change.js';
import {
  FindingsResource,
  AsyncFindingsResource,
} from './resources/findings.js';
import { IndexResource, AsyncIndexResource } from './resources/index.js';
import { JournalResource, AsyncJournalResource } from './resources/journal.js';
import {
  PipelineResource,
  AsyncPipelineResource,
} from './resources/pipeline.js';
import { Step12Resource, AsyncStep12Resource } from './resources/step12.js';
import { TrainResource, AsyncTrainResource } from './resources/train.js';
import {
  WorktreeResource,
  AsyncWorktreeResource,
} from './resources/worktree.js';
import { WpResource, AsyncWpResource } from './resources/wp.js';

export interface SulisExecutionOptions {
  repoRoot?: string;
  project: string;
  timeoutSeconds?: number;
  wpxDir?: string;
}

/**
 * Sync client for the sulis-execution CLI surface.
 *
 * @example
 * const client = new SulisExecution({ repoRoot: '.', project: 'my-project' });
 * const result = client.pipeline.run({
 *   wp: 'WP-001',
 *   branch: 'feat/wp-001-x',
 *   dev_sha_at_creation: 'abc123',
 *   deploy_workflow: 'Deploy to Dev',
 * });
 */
export class SulisExecution {
  private readonly transport: SubprocessTransport;
  public readonly pipeline: PipelineResource;
  public readonly train: TrainResource;
  public readonly index: IndexResource;
  public readonly journal: JournalResource;
  public readonly blocker: BlockerResource;
  public readonly findings: FindingsResource;
  public readonly wp: WpResource;
  public readonly worktree: WorktreeResource;
  public readonly step12: Step12Resource;
  public readonly change: ChangeResource;

  constructor(options: SulisExecutionOptions) {
    const config: TransportConfig = {
      repoRoot: options.repoRoot ?? '.',
      project: options.project,
      timeoutSeconds: options.timeoutSeconds,
      wpxDir: options.wpxDir,
    };
    this.transport = new SubprocessTransport(config);
    this.pipeline = new PipelineResource(this.transport, config);
    this.train = new TrainResource(this.transport, config);
    this.index = new IndexResource(this.transport, config);
    this.journal = new JournalResource(this.transport, config);
    this.blocker = new BlockerResource(this.transport, config);
    this.findings = new FindingsResource(this.transport, config);
    this.wp = new WpResource(this.transport, config);
    this.worktree = new WorktreeResource(this.transport, config);
    this.step12 = new Step12Resource(this.transport, config);
    this.change = new ChangeResource(this.transport, config);
  }
}

/**
 * Async client for the sulis-execution CLI surface.
 *
 * @example
 * const client = new AsyncSulisExecution({ repoRoot: '.', project: 'my-project' });
 * const result = await client.pipeline.run({
 *   wp: 'WP-001',
 *   branch: 'feat/wp-001-x',
 *   dev_sha_at_creation: 'abc123',
 *   deploy_workflow: 'Deploy to Dev',
 * });
 */
export class AsyncSulisExecution {
  private readonly transport: AsyncSubprocessTransport;
  public readonly pipeline: AsyncPipelineResource;
  public readonly train: AsyncTrainResource;
  public readonly index: AsyncIndexResource;
  public readonly journal: AsyncJournalResource;
  public readonly blocker: AsyncBlockerResource;
  public readonly findings: AsyncFindingsResource;
  public readonly wp: AsyncWpResource;
  public readonly worktree: AsyncWorktreeResource;
  public readonly step12: AsyncStep12Resource;
  public readonly change: AsyncChangeResource;

  constructor(options: SulisExecutionOptions) {
    const config: TransportConfig = {
      repoRoot: options.repoRoot ?? '.',
      project: options.project,
      timeoutSeconds: options.timeoutSeconds,
      wpxDir: options.wpxDir,
    };
    this.transport = new AsyncSubprocessTransport(config);
    this.pipeline = new AsyncPipelineResource(this.transport, config);
    this.train = new AsyncTrainResource(this.transport, config);
    this.index = new AsyncIndexResource(this.transport, config);
    this.journal = new AsyncJournalResource(this.transport, config);
    this.blocker = new AsyncBlockerResource(this.transport, config);
    this.findings = new AsyncFindingsResource(this.transport, config);
    this.wp = new AsyncWpResource(this.transport, config);
    this.worktree = new AsyncWorktreeResource(this.transport, config);
    this.step12 = new AsyncStep12Resource(this.transport, config);
    this.change = new AsyncChangeResource(this.transport, config);
  }
}
