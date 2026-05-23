# Dead-Code Detection Patterns

How the scanner identifies symbols + counts references.

## Symbol definition patterns (Python v1)

| Symbol kind | AST pattern | Example |
|---|---|---|
| Function | `^def\s+(\w+)` at module level (no indent) | `def process_payment():` |
| Class | `^class\s+(\w+)` | `class PaymentProcessor:` |
| Top-level constant | `^([A-Z_][A-Z0-9_]+)\s*=` | `MAX_RETRIES = 5` |
| Import (whole module) | `^import\s+(\w+)` | `import json` |
| Import (named symbol) | `^from\s+\w[\w.]*\s+import\s+(\w+)` (per name) | `from datetime import timedelta` |

NOT detected as definitions (skipped):
- Indented `def`/`class` (methods, nested functions, closures — assume used by enclosing)
- Dunder methods (`__init__`, `__repr__`, etc. — used by Python protocol)
- Names starting with `_` ≥ 5 chars (private; if unused, founder knows)
- Anything in `if __name__ == "__main__":` blocks

## Reference detection

For each defined symbol, count occurrences in OTHER files:
- Whole-word match: `\b{symbol}\b`
- Excludes the file where it's defined (self-references don't count)
- Excludes comments (`# foo` doesn't count as a reference to `foo`)
- Excludes docstrings (rough heuristic — lines inside `"""..."""` blocks)

If count == 0 across all other files, flag as dead.

## Exemptions (don't flag)

### Test infrastructure
- Files matching `tests/`, `__tests__/`, `_test\.py$`, `conftest.py`
- Functions named `test_*` (pytest convention)
- Functions decorated with `@pytest.fixture`, `@pytest.fixture(...)`,
  `@fixture`

### Plugin convention loading
- Files inside `plugins/*/skills/` and `plugins/*/agents/` (Claude
  Code marketplace convention — discovered via SKILL.md / agent.md)

### Public API
- Names listed in module's `__all__` (regex-based detection)
- Names starting with `main` (`main`, `main_loop`, etc. — CLI entry
  conventions)

### CLI entry points
- Functions named exactly the filename stem (per check-readability's
  same heuristic — `def build()` in `build_pptx.py` is the entry)

### Special protocol names
- Dunder methods (`__init__`, etc.)
- Pydantic / dataclass / TypedDict field assignments (assume used by
  framework)

## Allowlist mechanism

Per-project allowlist at
`.checkup/{project}/check-maintainability-allowlist.md`:

```
# This function is loaded dynamically by the X framework
process_payment: framework loads by name via getattr()

# Public API consumed by external clients
format_date
```

Format: `signature: reason` (signature contains `:` so reason
separator is `: ` — same as other allowlists).

## Why advisory-only severity

Dead-code detection is FP-prone because:

1. **Reflection** — `getattr(module, name)`, `globals()[name]` reference
   symbols by string; static scan can't see it
2. **Framework discovery** — Django views, FastAPI routes, click
   commands, pytest tests all use convention-based discovery
3. **Plugin/extension systems** — load symbols at runtime from
   configuration
4. **External consumers** — if you're a library, your "unused" function
   may have 1000 external callers
5. **Indirect call paths** — `event_handlers["click"] = handle_click`
   then `dispatch(name)`

vulture, ts-prune, deadcode, and every other dead-code tool wrestles
with these. Industry standard is to flag advisory + require manual
review. v1 inherits this.

## Adding a new exemption pattern

To extend the exemption list:

1. Add pattern to `EXEMPT_PATTERNS` or `EXEMPT_FILE_PATTERNS` in
   `scripts/scanner.py`
2. Document the pattern + the framework/convention it serves
3. Test against the marketplace + a fixture

## What this skill does NOT detect

Per SKILL.md "What this skill catches vs misses":
- Migration completion (is a deprecated API still being used?)
- Surface drift (CLI ↔ SDK ↔ MCP ↔ OpenAPI sync)
- Test quality beyond coverage
- Cyclomatic complexity hotspots
- Duplication
- Coupling metrics

For these, use `sulis-security:codebase-assess` (Code Quality category
CQ-01..05).
