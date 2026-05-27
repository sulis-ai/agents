# Code Intelligence — probe-stage3

> **Project:** probe-stage3
> **Generated:** 2026-05-14T20:24:28+00:00
> **Workspaces:** 1
> **Toolchain:** ast-grep=ast-grep 0.42.2, lizard=1.22.1, scc=scc version 3.7.0, git=git version 2.54.0, pytest=pytest 9.0.1, npx=11.12.1

## Summary

_LLM synthesis not yet written. Run `python probe.py --draft-synthesis` to write a template, then have the LLM fill it._

## Workspace: `.`

> **Path:** `/Users/iain/Documents/repos/standards`
> **Style:** single-repo

### Infrastructure & Stack
`[deterministic: scc]`

- **Primary language:** Markdown
- **Total files:** 260
- **Total LOC:** 53929
- **Total complexity:** 708

| Language | Files | Code | Complexity |
|---|---|---|---|
| Markdown | 187 | 42858 | 0 |
| Python | 31 | 5491 | 654 |
| JSON | 33 | 5089 | 0 |
| Shell | 4 | 426 | 54 |
| YAML | 4 | 48 | 0 |
| License | 1 | 17 | 0 |

### Capability Inventory
`[deterministic: ast-grep]`

**By kind:** class=73, function=166
**By language:** python=239

Total: **239** symbols.

Sample (first 20):

| Kind | Name | File | Line | Language |
|---|---|---|---|---|
| function | `fmt_money` | `plugins/idc/scripts/build_finance_html.py` | 36 | python |
| function | `fmt_pct` | `plugins/idc/scripts/build_finance_html.py` | 52 | python |
| function | `build_html` | `plugins/idc/scripts/build_finance_html.py` | 62 | python |
| function | `build` | `plugins/idc/scripts/build_finance_html.py` | 318 | python |
| function | `main` | `plugins/idc/scripts/build_finance_html.py` | 331 | python |
| class | `Slide` | `plugins/idc/scripts/build_html_deck.py` | 30 | python |
| function | `parse_slide` | `plugins/idc/scripts/build_html_deck.py` | 38 | python |
| function | `body_to_html` | `plugins/idc/scripts/build_html_deck.py` | 58 | python |
| function | `render_slide_html` | `plugins/idc/scripts/build_html_deck.py` | 94 | python |
| function | `build_html` | `plugins/idc/scripts/build_html_deck.py` | 125 | python |
| function | `build` | `plugins/idc/scripts/build_html_deck.py` | 194 | python |
| function | `main` | `plugins/idc/scripts/build_html_deck.py` | 225 | python |
| class | `Tokens` | `plugins/idc/scripts/build_pptx.py` | 55 | python |
| class | `Slide` | `plugins/idc/scripts/build_pptx.py` | 76 | python |
| function | `hex_to_rgb` | `plugins/idc/scripts/build_pptx.py` | 87 | python |
| function | `load_tokens` | `plugins/idc/scripts/build_pptx.py` | 95 | python |
| function | `get` | `plugins/idc/scripts/build_pptx.py` | 100 | python |
| function | `parse_slide` | `plugins/idc/scripts/build_pptx.py` | 128 | python |
| function | `contrast_ratio` | `plugins/idc/scripts/build_pptx.py` | 154 | python |
| function | `relative_luminance` | `plugins/idc/scripts/build_pptx.py` | 157 | python |

_Phases captured for this workspace: 1.1, 1.10, 1.11, 1.12, 1.13, 1.14, 1.15, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9_
