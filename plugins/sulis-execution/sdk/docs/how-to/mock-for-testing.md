# How to mock the SDK for testing

**Applies to:** sulis-execution v0.1.0

## The pattern

The SDK uses subprocess transport. To test code that calls the SDK
without invoking real wpx-* binaries, point the client at a fake
binary directory and write executable scripts that emit known JSON.

## Python — pytest fixture

The SDK ships with `make_fake_binary` patterns in its own test suite.
Copy this approach into your test code:

```python
import stat
import sys
from pathlib import Path
import pytest

@pytest.fixture
def fake_wpx_dir(tmp_path):
    d = tmp_path / "fake-wpx"
    d.mkdir()
    return d

@pytest.fixture
def make_fake_binary(fake_wpx_dir):
    def _factory(binary_name, *, stdout_payload, exit_code=0, stderr_payload=""):
        import json
        binary = fake_wpx_dir / binary_name
        stdout_text = (
            json.dumps(stdout_payload)
            if isinstance(stdout_payload, dict)
            else stdout_payload
        )
        script = (
            f"#!{sys.executable}\n"
            f"import sys\n"
            f"sys.stdout.write({stdout_text!r})\n"
            f"sys.stderr.write({stderr_payload!r})\n"
            f"sys.exit({exit_code})\n"
        )
        binary.write_text(script)
        binary.chmod(binary.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        return binary
    return _factory
```

Then in your test:

```python
def test_my_code_handles_blocker(make_fake_binary, fake_wpx_dir, tmp_path):
    make_fake_binary(
        "wpx-pipeline",
        stdout_payload={
            "ok": True,
            "data": {"result": {
                "wp": "WP-001",
                "outcome": "blocker",
                "blocker_reason": "CI failed",
                "started_at": "2026-05-21T12:00:00Z",
            }}
        },
        exit_code=1,
    )

    # Your code under test
    result = my_function_that_uses_sdk(
        repo_root=tmp_path,
        wpx_dir=fake_wpx_dir,
    )
    assert result == "blocked"
```

## TypeScript — vitest

```typescript
import { writeFileSync, chmodSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';

function makeFakeBinary(dir: string, name: string, stdout: string, exit = 0) {
  mkdirSync(dir, { recursive: true });
  const path = join(dir, name);
  writeFileSync(
    path,
    `#!/bin/sh\nprintf '%s' ${JSON.stringify(stdout)}\nexit ${exit}\n`,
  );
  chmodSync(path, 0o755);
}

it('handles blocker outcome', () => {
  makeFakeBinary('/tmp/fake-wpx', 'wpx-pipeline',
    JSON.stringify({
      ok: true,
      data: { result: { wp: 'WP-001', outcome: 'blocker',
                        blocker_reason: 'CI failed',
                        started_at: '2026-05-21T12:00:00Z' } },
    }),
    1,
  );

  const result = myFunctionThatUsesSdk({
    repoRoot: '/tmp/repo',
    wpxDir: '/tmp/fake-wpx',
  });

  expect(result).toBe('blocked');
});
```

## What to mock vs what to integration-test

| Test type | What to do |
|---|---|
| Unit (your code that uses the SDK) | Mock the binary (above pattern) |
| Integration (real wpx-* against a sandbox repo) | Use real wpx-* binaries; create a tmp git repo per-test |
| End-to-end (your full workflow with real CI/deploy) | Run against a real test project; takes minutes per test |

The mock pattern is enough for ~90% of tests. Integration tests are
the SDK's own job (the SDK ships them in `sdk/python/tests/` and
`sdk/typescript/tests/`).

## See also

- [Configure the client](configure-client.md) — `wpx_dir` option
- [Handle errors](handle-errors.md) — what to assert in failure tests
