/**
 * Pilot tests — exercise the end-to-end loop on multiple resources.
 *
 * Uses a fake CLI binary (a shell script written into a tmp directory)
 * to exercise the subprocess transport without needing the real wpx-*
 * tools or any git/GitHub state.
 */

import { describe, expect, it, beforeEach, afterEach } from 'vitest';
import { mkdtempSync, rmSync, writeFileSync, chmodSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { tmpdir } from 'node:os';

import {
  SulisExecution,
  ExpectedError,
  InternalError,
  BinaryNotFoundError,
} from '../src/index.js';

let tmpDir: string;
let fakeWpxDir: string;
let repoRoot: string;

beforeEach(() => {
  tmpDir = mkdtempSync(join(tmpdir(), 'sulis-exec-ts-'));
  fakeWpxDir = join(tmpDir, 'wpx');
  repoRoot = join(tmpDir, 'repo');
  // Both directories must exist for the tests
  writeFakeBinarySetup();
});

afterEach(() => {
  rmSync(tmpDir, { recursive: true, force: true });
});

function writeFakeBinarySetup(): void {
  // Create dirs (cheap; idempotent)
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const fs = require('node:fs');
  fs.mkdirSync(fakeWpxDir, { recursive: true });
  fs.mkdirSync(repoRoot, { recursive: true });
}

function makeFakeBinary(
  binaryName: string,
  opts: { stdout?: string; stderr?: string; exit?: number },
): void {
  const stdout = opts.stdout ?? '';
  const stderr = opts.stderr ?? '';
  const exit = opts.exit ?? 0;
  const script = `#!/bin/sh\nprintf '%s' ${JSON.stringify(stdout)}\nprintf '%s' ${JSON.stringify(stderr)} 1>&2\nexit ${exit}\n`;
  const path = join(fakeWpxDir, binaryName);
  writeFileSync(path, script);
  chmodSync(path, 0o755);
}

function client(): SulisExecution {
  return new SulisExecution({
    repoRoot: resolve(repoRoot),
    project: 'test-project',
    wpxDir: resolve(fakeWpxDir),
  });
}

const successEnvelope = JSON.stringify({
  ok: true,
  data: {
    result: {
      wp: 'WP-001',
      outcome: 'success',
      merge_sha: 'abc123def456',
      deploy_url: 'https://staging.example.com',
      deploy_workflow_run: '12345',
      health_status: 'healthy',
      health_url: 'https://staging.example.com/health',
      smoke_verdict: 'PASS',
      blocker_reason: null,
      ci_poll_skipped: false,
      merge_already_complete: false,
      started_at: '2026-05-21T12:00:00Z',
      completed_at: '2026-05-21T12:30:00Z',
    },
  },
});

const blockerEnvelope = JSON.stringify({
  ok: true,
  data: {
    result: {
      wp: 'WP-001',
      outcome: 'blocker',
      merge_sha: null,
      deploy_url: null,
      deploy_workflow_run: null,
      health_status: null,
      health_url: null,
      smoke_verdict: null,
      blocker_reason: 'CI checks failed after 3 rebase attempts',
      ci_poll_skipped: false,
      merge_already_complete: false,
      started_at: '2026-05-21T12:00:00Z',
      completed_at: '2026-05-21T12:15:00Z',
    },
  },
});

// ─── Happy path ────────────────────────────────────────────────────

describe('pipeline.run', () => {
  it('returns a typed result on success', () => {
    makeFakeBinary('wpx-pipeline', { stdout: successEnvelope });
    const result = client().pipeline.run({
      wp: 'WP-001',
      branch: 'feat/wp-001-x',
      dev_sha_at_creation: 'abc123de',
      deploy_workflow: 'Deploy to Dev',
    });

    expect(result.wp).toBe('WP-001');
    expect(result.outcome).toBe('success');
    expect(result.merge_sha).toBe('abc123def456');
    expect(result.health_status).toBe('healthy');
  });

  it('returns blocker outcome as a normal result (NOT exception)', () => {
    makeFakeBinary('wpx-pipeline', { stdout: blockerEnvelope, exit: 1 });
    const result = client().pipeline.run({
      wp: 'WP-001',
      branch: 'feat/wp-001-x',
      dev_sha_at_creation: 'abc123de',
      deploy_workflow: 'Deploy to Dev',
    });

    // The key v0.2.0 contract: blocker is a result, not an exception
    expect(result.outcome).toBe('blocker');
    expect(result.blocker_reason).toBe(
      'CI checks failed after 3 rebase attempts',
    );
    expect(result.merge_sha).toBeNull();
  });
});

// ─── Error mapping ─────────────────────────────────────────────────

describe('error handling', () => {
  it('raises ExpectedError on exit 1 + ok:false', () => {
    makeFakeBinary('wpx-pipeline', {
      stdout: JSON.stringify({
        ok: false,
        error: 'WP-001 not found in INDEX.md',
        context: { code: 'wp_not_found' },
      }),
      exit: 1,
    });

    expect(() =>
      client().pipeline.run({
        wp: 'WP-001',
        branch: 'feat/wp-001-x',
        dev_sha_at_creation: 'abc123de',
        deploy_workflow: 'Deploy to Dev',
      }),
    ).toThrowError(ExpectedError);
  });

  it('raises InternalError on exit 2', () => {
    makeFakeBinary('wpx-pipeline', {
      stdout: '',
      stderr:
        'Traceback (most recent call last):\n  File "...", line 1\n    raise RuntimeError("boom")\nRuntimeError: boom\n',
      exit: 2,
    });

    expect(() =>
      client().pipeline.run({
        wp: 'WP-001',
        branch: 'feat/wp-001-x',
        dev_sha_at_creation: 'abc123de',
        deploy_workflow: 'Deploy to Dev',
      }),
    ).toThrowError(InternalError);
  });

  it('raises BinaryNotFoundError when binary is missing', () => {
    // Do not create the fake binary
    expect(() =>
      client().pipeline.run({
        wp: 'WP-001',
        branch: 'feat/wp-001-x',
        dev_sha_at_creation: 'abc123de',
        deploy_workflow: 'Deploy to Dev',
      }),
    ).toThrowError(BinaryNotFoundError);
  });
});

// ─── Other resources (smoke) ───────────────────────────────────────

describe('resource smoke coverage', () => {
  it('train.queueList parses TrainQueueListResult', () => {
    makeFakeBinary('wpx-train', {
      stdout: JSON.stringify({
        ok: true,
        data: {
          project: 'test-project',
          eligible_count: 2,
          ineligible_count: 0,
          eligible: [
            {
              wp: 'WP-001',
              branch: 'feat/wp-001',
              eligible: true,
              reason: 'ready',
              primitive: 'EXPAND',
              forced: false,
            },
            {
              wp: 'WP-002',
              branch: 'feat/wp-002',
              eligible: true,
              reason: 'ready',
              primitive: 'EXPAND',
              forced: false,
            },
          ],
          ineligible: [],
          overrides: { includes: [], holds: [] },
        },
      }),
    });

    const result = client().train.queueList();
    expect(result.eligible_count).toBe(2);
    expect(result.eligible[0].wp).toBe('WP-001');
  });

  it('index.flipStatus parses IndexFlipStatusResult', () => {
    makeFakeBinary('wpx-index', {
      stdout: JSON.stringify({
        ok: true,
        data: { wp: 'WP-001', status: 'done' },
      }),
    });

    const result = client().index.flipStatus({
      wp: 'WP-001',
      to: 'done',
      expected: 'in_progress',
    });
    expect(result.wp).toBe('WP-001');
    expect(result.status).toBe('done');
  });

  it('change.start parses ChangeStartResult', () => {
    makeFakeBinary('sulis-change', {
      stdout: JSON.stringify({
        ok: true,
        data: {
          branch: 'change/create-introduce-payments',
          primitive: 'create',
          slug: 'introduce-payments',
          worktree_path: '/tmp/repo-change-create-introduce-payments',
          base_branch: 'dev',
          base_sha: 'abc123de',
          metadata_path: '/tmp/.changes/create-introduce-payments.yaml',
        },
      }),
    });

    const result = client().change.start({
      slug: 'introduce-payments',
      primitive: 'create',
    });
    expect(result.branch).toBe('change/create-introduce-payments');
    expect(result.primitive).toBe('create');
    expect(result.slug).toBe('introduce-payments');
  });

  it('change.list parses ChangeListResult', () => {
    makeFakeBinary('sulis-change', {
      stdout: JSON.stringify({
        ok: true,
        data: {
          active_count: 1,
          changes: [
            {
              primitive: 'create',
              slug: 'introduce-payments',
              branch: 'change/create-introduce-payments',
              worktree_path: '/tmp/x',
              worktree_present: true,
              dirty: false,
            },
          ],
        },
      }),
    });

    const result = client().change.list();
    expect(result.active_count).toBe(1);
    expect(result.changes[0].primitive).toBe('create');
  });
});
