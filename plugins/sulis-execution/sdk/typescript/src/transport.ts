/**
 * Subprocess transport for the sulis-execution TypeScript SDK.
 *
 * Per agent-consumable SDK spec v0.2.0 Part 4.3 — same binding the
 * Python SDK uses. Spawns the underlying CLI binary via Node's
 * child_process, reads stdout, parses JSON, maps exit code + envelope
 * to either a successful result or a typed exception.
 */

import { spawn, spawnSync } from 'node:child_process';
import { accessSync, constants } from 'node:fs';
import { resolve as resolvePath, join as joinPath } from 'node:path';
import { delimiter as pathSeparator } from 'node:path';

import {
  BinaryNotFoundError,
  ExpectedError,
  InternalError,
  ProtocolError,
  UnexpectedOutputError,
} from './errors.js';

export interface TransportConfig {
  repoRoot: string;
  project: string;
  /** Default 5400 (90 min) — matches wpx-pipeline's default. */
  timeoutSeconds?: number;
  /** Optional override for the binary lookup directory. */
  wpxDir?: string;
}

function resolveBinary(binaryName: string, config: TransportConfig): string {
  // 1. Explicit config override
  if (config.wpxDir) {
    const candidate = joinPath(config.wpxDir, binaryName);
    try {
      accessSync(candidate, constants.X_OK);
      return candidate;
    } catch {
      // fall through
    }
  }

  // 2. Env var override
  const envDir = process.env.WPX_DIR;
  if (envDir) {
    const candidate = joinPath(envDir, binaryName);
    try {
      accessSync(candidate, constants.X_OK);
      return candidate;
    } catch {
      // fall through
    }
  }

  // 3. PATH lookup
  const path = process.env.PATH ?? '';
  for (const dir of path.split(pathSeparator)) {
    if (!dir) continue;
    const candidate = joinPath(dir, binaryName);
    try {
      accessSync(candidate, constants.X_OK);
      return candidate;
    } catch {
      // not in this dir
    }
  }

  throw new BinaryNotFoundError(
    `Could not find binary ${JSON.stringify(binaryName)}. ` +
      `Set WPX_DIR env var to point at the scripts directory, ` +
      `or pass wpxDir to the client.`,
    { transportCode: 'exec_failure', context: { binary: binaryName } },
  );
}

function correlationId(pid: number): string {
  return `pid-${pid}-${Date.now()}`;
}

function buildArgv(
  binary: string,
  subcommand: string,
  params: Record<string, unknown>,
): string[] {
  const argv: string[] = [binary, subcommand];
  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined) continue;
    const flag = '--' + key.replace(/_/g, '-');
    if (typeof value === 'boolean') {
      if (value) argv.push(flag);
    } else {
      argv.push(flag, String(value));
    }
  }
  return argv;
}

function parseEnvelope(
  stdout: string,
  stderr: string,
  exitCode: number,
  cid: string,
  argv: string[],
): Record<string, unknown> {
  let parsed: Record<string, unknown> | null = null;
  if (stdout.trim().length > 0) {
    try {
      parsed = JSON.parse(stdout) as Record<string, unknown>;
    } catch (err) {
      throw new UnexpectedOutputError(
        `CLI output was not valid JSON: ${(err as Error).message}`,
        {
          transportCode: exitCode,
          correlationId: cid,
          body: { stdout, stderr },
          context: { argv },
        },
      );
    }
  }

  // Exit 2 → internal crash
  if (exitCode === 2) {
    const tail = stderr.trim().slice(-1000);
    const message =
      (parsed?.error as string | undefined) ??
      `CLI crashed with traceback:\n${tail}`;
    throw new InternalError(message, {
      transportCode: exitCode,
      correlationId: cid,
      body: parsed,
      context: { stderr_tail: stderr.trim().slice(-2000) },
    });
  }

  // Exit 1 + ok:false → expected error
  if (exitCode === 1 && parsed && parsed.ok === false) {
    const context = (parsed.context as Record<string, unknown> | undefined) ?? {};
    throw new ExpectedError(
      (parsed.error as string | undefined) ?? 'Unknown expected error',
      {
        transportCode: exitCode,
        correlationId: cid,
        body: parsed,
        context,
        code: (context.code as string | undefined) ?? null,
      },
    );
  }

  // Anything else with exit != 0 and no JSON → internal
  if (exitCode !== 0 && !parsed) {
    throw new InternalError(`CLI exited ${exitCode} with no JSON output`, {
      transportCode: exitCode,
      correlationId: cid,
      context: { stderr_tail: stderr.trim().slice(-2000) },
    });
  }

  return parsed ?? {};
}

// ─── Sync transport (Node spawnSync) ──────────────────────────────────

export class SubprocessTransport {
  constructor(public readonly config: TransportConfig) {}

  invoke(
    binaryName: string,
    subcommand: string,
    params: Record<string, unknown>,
  ): Record<string, unknown> {
    const binary = resolveBinary(binaryName, this.config);
    const argv = buildArgv(binary, subcommand, params);
    const timeoutMs = (this.config.timeoutSeconds ?? 5400) * 1000;

    const result = spawnSync(argv[0], argv.slice(1), {
      cwd: resolvePath(this.config.repoRoot),
      encoding: 'utf-8',
      timeout: timeoutMs,
    });

    if (result.error) {
      const errAny = result.error as NodeJS.ErrnoException;
      if (errAny.code === 'ENOENT') {
        throw new BinaryNotFoundError(
          `Binary ${binary} could not be executed`,
          { context: { argv } },
        );
      }
      if (errAny.code === 'ETIMEDOUT') {
        throw new ProtocolError(
          `CLI timed out after ${this.config.timeoutSeconds ?? 5400}s`,
          {
            transportCode: 'timeout',
            correlationId: correlationId(result.pid ?? process.pid),
            context: { argv },
          },
        );
      }
      throw new ProtocolError(
        `Subprocess error: ${(result.error as Error).message}`,
        { transportCode: 'exec_failure', context: { argv } },
      );
    }

    return parseEnvelope(
      result.stdout,
      result.stderr,
      result.status ?? 0,
      correlationId(result.pid ?? process.pid),
      argv,
    );
  }
}

// ─── Async transport (Promise wrapper around child_process.spawn) ─────

export class AsyncSubprocessTransport {
  constructor(public readonly config: TransportConfig) {}

  invoke(
    binaryName: string,
    subcommand: string,
    params: Record<string, unknown>,
  ): Promise<Record<string, unknown>> {
    const binary = resolveBinary(binaryName, this.config);
    const argv = buildArgv(binary, subcommand, params);
    const timeoutMs = (this.config.timeoutSeconds ?? 5400) * 1000;

    return new Promise((resolve, reject) => {
      const child = spawn(argv[0], argv.slice(1), {
        cwd: resolvePath(this.config.repoRoot),
      });

      let stdout = '';
      let stderr = '';
      let timedOut = false;

      const timeoutHandle = setTimeout(() => {
        timedOut = true;
        child.kill();
      }, timeoutMs);

      child.stdout.on('data', (chunk: Buffer) => {
        stdout += chunk.toString('utf-8');
      });
      child.stderr.on('data', (chunk: Buffer) => {
        stderr += chunk.toString('utf-8');
      });

      child.on('error', (err: NodeJS.ErrnoException) => {
        clearTimeout(timeoutHandle);
        if (err.code === 'ENOENT') {
          reject(
            new BinaryNotFoundError(
              `Binary ${binary} could not be executed`,
              { context: { argv } },
            ),
          );
        } else {
          reject(
            new ProtocolError(`Subprocess error: ${err.message}`, {
              transportCode: 'exec_failure',
              context: { argv },
            }),
          );
        }
      });

      child.on('close', (code: number | null) => {
        clearTimeout(timeoutHandle);
        if (timedOut) {
          reject(
            new ProtocolError(
              `CLI timed out after ${this.config.timeoutSeconds ?? 5400}s`,
              {
                transportCode: 'timeout',
                correlationId: correlationId(child.pid ?? process.pid),
                context: { argv },
              },
            ),
          );
          return;
        }
        try {
          const envelope = parseEnvelope(
            stdout,
            stderr,
            code ?? 0,
            correlationId(child.pid ?? process.pid),
            argv,
          );
          resolve(envelope);
        } catch (err) {
          reject(err);
        }
      });
    });
  }
}
