# Code Intelligence — probe-stage4

> **Project:** probe-stage4
> **Generated:** 2026-05-14T20:28:33+00:00
> **Workspaces:** 1
> **Toolchain:** ast-grep=ast-grep 0.42.2, lizard=1.22.1, scc=scc version 3.7.0, git=git version 2.54.0, pytest=pytest 9.0.1, npx=11.12.1

## Summary

_LLM synthesis not yet written. Run `python probe.py --draft-synthesis` to write a template, then fill it._

## Workspace: `.`

> **Path:** `/Users/iain/Documents/repos/standards`  ·  **Style:** single-repo

### Infrastructure & Stack
`[deterministic: scc]`  · phase 1.1  · duration 19ms

- **Primary language:** Markdown
- **Total files:** 263
- **Total LOC:** 54,920
- **Total complexity:** 910

| Language | Files | Code | Complexity |
|---|---|---|---|
| Markdown | 188 | 42,911 | 0 |
| Python | 31 | 6,123 | 839 |
| JSON | 33 | 5,089 | 0 |
| Shell | 4 | 426 | 54 |
| CSS | 1 | 216 | 0 |
| JavaScript | 1 | 90 | 17 |
| YAML | 4 | 48 | 0 |
| License | 1 | 17 | 0 |

### Capability Inventory
`[deterministic: ast-grep]`  · phase 1.2  · duration 106ms

**By kind:** class=73, function=231
**By language:** javascript=22, python=282

Total: **304** symbols.

Sample (first 20):

| Kind | Name | File | Line |
|---|---|---|---|
| function | `fmt_money` | `plugins/idc/scripts/build_finance_html.py` | 36 |
| function | `fmt_pct` | `plugins/idc/scripts/build_finance_html.py` | 52 |
| function | `build_html` | `plugins/idc/scripts/build_finance_html.py` | 62 |
| function | `build` | `plugins/idc/scripts/build_finance_html.py` | 318 |
| function | `main` | `plugins/idc/scripts/build_finance_html.py` | 331 |
| class | `Slide` | `plugins/idc/scripts/build_html_deck.py` | 30 |
| function | `parse_slide` | `plugins/idc/scripts/build_html_deck.py` | 38 |
| function | `body_to_html` | `plugins/idc/scripts/build_html_deck.py` | 58 |
| function | `render_slide_html` | `plugins/idc/scripts/build_html_deck.py` | 94 |
| function | `build_html` | `plugins/idc/scripts/build_html_deck.py` | 125 |
| function | `build` | `plugins/idc/scripts/build_html_deck.py` | 194 |
| function | `main` | `plugins/idc/scripts/build_html_deck.py` | 225 |
| class | `Tokens` | `plugins/idc/scripts/build_pptx.py` | 55 |
| class | `Slide` | `plugins/idc/scripts/build_pptx.py` | 76 |
| function | `hex_to_rgb` | `plugins/idc/scripts/build_pptx.py` | 87 |
| function | `load_tokens` | `plugins/idc/scripts/build_pptx.py` | 95 |
| function | `get` | `plugins/idc/scripts/build_pptx.py` | 100 |
| function | `parse_slide` | `plugins/idc/scripts/build_pptx.py` | 128 |
| function | `contrast_ratio` | `plugins/idc/scripts/build_pptx.py` | 154 |
| function | `relative_luminance` | `plugins/idc/scripts/build_pptx.py` | 157 |

### Extension Points
`[deterministic: ast-grep]`  · phase 1.3  · duration 0ms

_No extension points detected._

### Reusable Abstractions
`[deterministic: grep]`  · phase 1.4  · duration 85ms

Modules with consumer count ≥ threshold: **8**

| Module | Language | Consumer count | Kitchen-sink? |
|---|---|---|---|
| `__future__` | python | 29 | no |
| `..models` | python | 16 | no |
| `..config` | python | 15 | no |
| `.base` | python | 15 | no |
| `.config` | python | 5 | no |
| `yaml` | python | 4 | no |
| `.models` | python | 3 | no |
| `..filesystem` | python | 3 | no |

### Coupling & Cycles
`[deterministic: ast-grep+Tarjan]`  · phase 1.5  · duration 86ms

**Modules tracked:** 62
**Cycles:** 0
**High fan-in (>threshold):** 4
**High fan-out (>threshold):** 0

### Complexity Hotspots
`[deterministic: lizard]`  · phase 1.6  · duration 217ms

Functions over CCN 15: **15**
Files over module-fragility threshold: **14**

| Function | File | Line | CCN | NLOC |
|---|---|---|---|---|
| `_parse_lint_output` | `plugins/sea/skills/probe/scripts/probe/runners/lint_runner.py` | 118 | **35** | 77 |
| `walk_files` | `plugins/sea/skills/probe/scripts/probe/filesystem.py` | 107 | **28** | 46 |
| `run` | `plugins/sea/skills/probe/scripts/probe/runners/astgrep_extension.py` | 27 | **23** | 76 |
| `main` | `plugins/sea/skills/probe/scripts/probe.py` | 105 | **23** | 81 |
| `run` | `plugins/sea/skills/probe/scripts/probe/runners/wrapper_runner.py` | 32 | **20** | 80 |
| `render_html_doc` | `plugins/sea/skills/probe/scripts/probe/render.py` | 465 | **19** | 55 |
| `run` | `plugins/sea/skills/probe/scripts/probe/runners/architecture_runner.py` | 26 | **18** | 59 |
| `run` | `plugins/sea/skills/probe/scripts/probe/runners/coupling_runner.py` | 35 | **18** | 59 |
| `_parse_astgrep_stream` | `plugins/sea/skills/probe/scripts/probe/runners/astgrep_capability.py` | 120 | **17** | 44 |
| `run` | `plugins/sea/skills/probe/scripts/probe/runners/reuse_runner.py` | 66 | **16** | 57 |
| `_parse_enum_output` | `plugins/sea/skills/probe/scripts/probe/runners/test_runner.py` | 167 | **16** | 17 |
| `detect_tools` | `plugins/sea/skills/probe/scripts/probe/detection.py` | 113 | **16** | 51 |
| `run` | `plugins/sea/skills/probe/scripts/probe/runners/duplication_runner.py` | 22 | **14** | 76 |
| `_run_workspace` | `plugins/sea/skills/probe/scripts/probe/orchestrator.py` | 118 | **14** | 84 |
| `(anonymous)` | `plugins/sea/skills/probe/scripts/probe/render_templates/interactivity.js` | 4 | **2** | 13 |

### Wrapper-Rot Candidates
`[deterministic: ast-grep]`  · phase 1.7  · duration 0ms

_No wrapper-rot candidates detected._

### Conventions
`[deterministic: filesystem]`  · phase 1.8  · duration 79ms

- **Module layout:** per-feature
- **Error handling:** exceptions
- **File naming:** snake_case (confidence 66%)
- **Test naming:** snake_case (confidence 100%)

### Test Suite Health
`[deterministic: test-frameworks]`  · phase 1.9  · duration 18ms

- **Framework:** `none-detected`
- **Test files:** 0
- **Tests enumerated:** 0
- **Executed?** no (--run-tests not set)

### Lint Signal
`[deterministic: linters]`  · phase 1.10  · duration 0ms

- **Linters configured:** _none_
- **Warnings:** 0
- **Errors:** 0
- **Typecheck errors:** 0

### Git History
`[deterministic: git]`  · phase 1.11  · duration 75ms

- **Lookback window:** 365 days
- **Files tracked:** 390
- **High-churn files (>threshold):** 1
- **Bus factor = 1 files:** 380
- **Co-change pairs above threshold:** 2

**Top churn files:**

- `.claude-plugin/marketplace.json` — 21 commits, 2 author(s)
- `README.md` — 12 commits, 2 author(s)
- `marketplace.json` — 10 commits, 2 author(s)
- `plugins/sea/.claude-plugin/plugin.json` — 9 commits, 1 author(s)
- `plugins/sea/agents/engineering-architect.md` — 7 commits, 1 author(s)
- `plugins/srd/.claude-plugin/plugin.json` — 6 commits, 1 author(s)
- `plugins/srd/README.md` — 6 commits, 1 author(s)
- `plugins/srd/agents/requirements-analyst.md` — 5 commits, 1 author(s)
- `CLAUDE.md` — 5 commits, 1 author(s)
- `srd/.claude-plugin/plugin.json` — 5 commits, 1 author(s)

### Code Duplication
`[deterministic: jscpd]`  · phase 1.12  · duration 0ms

> ⚠ jscpd not installed; duplication detection skipped

- **Duplicated lines:** 0
- **Duplicated %:** 0.0%
- **Duplicate blocks:** 0

### Dead Code
`[deterministic: ts-prune/vulture/deadcode]`  · phase 1.13  · duration 0ms

> ⚠ vulture (for python) not installed; skipped
> ⚠ ts-prune (for javascript) not installed; skipped

- **Total dead symbols:** 0

### Architecture Rules
`[deterministic: dependency-cruiser/import-linter]`  · phase 1.14  · duration 0ms

> ⚠ No architecture-rule config found; phase skipped

- **Rules config:** _none detected_
- **Violations:** 0
- **Rules passed / failed:** 0 / 0

### Coverage
`[deterministic: coverage-reports]`  · phase 1.15  · duration 0ms

- **Source:** none
- **Overall coverage:** _not available_
- **Files with coverage data:** 0
- **Files below threshold:** 0
