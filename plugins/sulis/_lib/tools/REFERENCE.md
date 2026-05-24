# `_lib/tools/` — tool-integration reference

> **Adapted from** `plugins/sulis-security/skills/codebase-assess/references/tool-commands.md`
> — the platform's tool-command catalogue. This document is the sulis-local
> equivalent: invocation contracts per tool, degradation behaviour, version
> pinning.

This directory contains the shared tool-integration layer for sulis check-*
skills. Every tool referenced in a skill's `verification_spiral.custom_dimensions`
or in the SKILL.md body must have a wrapper here, OR be explicitly flagged
"NEW — to be created" in VERIFICATION_REPORT.md (per the Codebase Referential
Integrity dimension).

## Contract

Each wrapper exposes (at minimum):

```python
from ._detection import ToolMode, tool_available
from ._runner import ToolResult, run_tool


def is_available() -> ToolMode:
    """Return DOCKER / NATIVE / NOT_AVAILABLE for this tool."""
    return tool_available("tool-name", native_binary="binary-name")


def run(args: list[str], *, repo_root: str | None = None) -> ToolResult:
    """Invoke the tool with given args; return structured result."""
    mode = is_available()
    if mode == ToolMode.DOCKER:
        cmd = ["docker", "run", "--rm", "-v", f"{repo_root}:/src", "image:tag", *args]
    elif mode == ToolMode.NATIVE:
        cmd = ["binary-name", *args]
    else:
        cmd = []  # NOT_AVAILABLE — runner returns degraded ToolResult
    return run_tool(cmd, mode=mode, version="x.y.z")
```

## Degradation policy

- Docker preferred (clean environment + version pinning)
- Native binary fallback (PATH lookup; whatever version is installed)
- NOT_AVAILABLE: the wrapper returns a `ToolResult` with `mode_used=NOT_AVAILABLE`,
  `exit_code=127`, empty `stdout`. The calling skill MUST treat this as
  NOT_ASSESSED for the affected primitives. Never silent regex fallback —
  founders need to see explicitly which primitives could not be checked.

## Catalogue (current + planned)

| Tool | Wrapper file | Status | Used by | Primitives covered |
|------|--------------|--------|---------|--------------------|
| Semgrep | `semgrep.py` | AVAILABLE (v0.19.0+) | check-security, check-reliability | SEC-01, SEC-03, SEC-04, SEC-05, SEC-06, DAT-03, INF-04 |
| Gitleaks | `gitleaks.py` | AVAILABLE (v0.19.0+) | check-security, check-build | SEC-07 (history), DAT-04, INF-02 |
| Trivy | `trivy.py` | AVAILABLE (v0.19.0+) | check-security, check-build | SC-01, SC-02, SC-03, SC-04, INF-01 (base image) |
| lizard | `lizard.py` | AVAILABLE (v0.19.0+) | check-readability | CQ-01 |
| jscpd | `jscpd.py` | AVAILABLE (v0.19.0+) | check-readability | CQ-03 |
| hadolint | `hadolint.py` | AVAILABLE (v0.19.0+) | check-build | INF-01 (Dockerfile) |
| testssl.sh | `testssl.py` | AVAILABLE (v0.19.0+) | check-security (when --url) | DAT-02 |
| curl | `curl_probe.py` | AVAILABLE (v0.19.0+) | check-security (when --url) | INF-03 |
| coverage tools | `coverage.py` | AVAILABLE (v0.19.0+; pytest-cov supported; vitest/jest follow-up) | check-tests | CQ-02 |

**Foundation files (this commit):**

- `__init__.py` — public exports
- `_detection.py` — `ToolMode`, `docker_available`, `native_available`, `tool_available`
- `_runner.py` — `ToolResult`, `run_tool`
- `REFERENCE.md` — this file

**Per-tool wrappers (built lazily — one per upsurge commit):**

Each per-tool wrapper is added in the commit that wires the first skill to
use it. Pattern: check-security upsurge → builds `semgrep.py` + `gitleaks.py`
+ `trivy.py`; check-readability upsurge → adds `lizard.py` + `jscpd.py`;
etc. The wrappers don't all need to exist before the upsurges begin —
they're built as each skill needs them.

## Adding a new wrapper

1. Pick the canonical tool name (lowercase, kebab-case if multi-word).
2. Create `{tool-name}.py` in this directory.
3. Implement `is_available()` and `run()` per the contract above.
4. Add unit tests (mocked subprocess) under `tests/_lib/tools/`.
5. Add degradation tests (NOT_AVAILABLE behaviour).
6. Update the catalogue table above with status: AVAILABLE.
7. Update the calling skill's `verification_spiral.custom_dimensions` to
   reference the new wrapper.

## Why this exists

The audit skills in `plugins/sulis/skills/check-*/` need to use real tools
(Semgrep, Gitleaks, Trivy, etc.) rather than regex pattern catalogues to
meet the depth bar set by `add-skill` v0.7.0. Centralising the tool-detection
+ invocation + degradation logic here means:

- One place to update when a tool changes invocation
- Consistent degradation across all skills (no skill silently falls back to
  regex while another reports NOT_ASSESSED)
- Codebase Referential Integrity scoring (SPIRAL_TEMPLATES Gate 4) has a
  canonical place to check existence
- New skills authoring against the same primitives reuse wrappers
