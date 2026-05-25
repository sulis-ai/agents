# Sources of Truth — Inbox Aggregator

Where each attention-item category lives on disk. The aggregator reads from
these paths; this document is the contract between inbox and the rest of
the marketplace.

If any source moves, update both this document AND
`scripts/aggregator.py`. Drift between them is the failure mode the
HD-008 doctor-check is meant to catch.

## Path conventions

All paths are project-scoped under `{repo_root}/.architecture/{project}/`
(per sulis-execution's `WpxPaths` class at
`plugins/sulis-execution/scripts/_wpxlib.py:35-94`).

| Concept | Path |
|---|---|
| Architecture root | `.architecture/{project}/` |
| Work-package directory | `.architecture/{project}/work-packages/` |
| Work-package index | `.architecture/{project}/work-packages/INDEX.md` |
| WP journal (per WP) | `.architecture/{project}/work-packages/.executor-{wp}.md` |
| BLOCKER file (per WP) | `.architecture/{project}/work-packages/BLOCKER-{wp}.md` |
| Train runs directory | `.architecture/{project}/train-runs/` |
| Train state (per run) | `.architecture/{project}/train-runs/{train_id}.state.json` |
| Security root | `.security/{project}/` |
| Findings directory | `.security/{project}/findings/` |
| Findings register | `.security/{project}/findings-register.md` |
| Concierge journey | `.sulis/{project}/JOURNEY.md` |

## Category sources

### Paused work

**Reads:** `.architecture/{project}/train-runs/*.state.json`

**Pause signal:** `phase` field equals `paused` (or `verifying_gates` if
awaiting external gate completion per HD-007).

**Per-train fields used:**
- `train_id` — for the operator-side reference
- `phase` — the current phase (paused / verifying_gates / etc.)
- `pause_reason` — written by sulis-execution when transitioning to paused
- `recovery_hint` — written by sulis-execution; passed through if plain English

**Founder name derivation:** `"Build run {train_id[-8:]}"` —
e.g., `"Build run a3f2c1d8"`. If the train state contains a WP list,
optionally append `" (batch of N tasks)"`.

**Action shortcut:** `wpx-train resume --train-id {train_id}` (safe; no
confirmation needed).

### Things to review

**Reads:**
- `.security/{project}/findings-register.md` — markdown table of findings
- `.security/{project}/findings/*.md` — individual finding files

**Review signal:** finding has no `triage:` line OR `triage: pending` OR
`triage: needs-decision`.

**Per-finding fields used:**
- `id` — the finding ID (e.g., `S-024`)
- `slug` — the human-readable slug
- `severity` — high / medium / low (drives ordering)
- `summary` — first sentence or top-line summary

**Founder name derivation:** translation table for common security/quality
jargon:

| Operator term | Founder term |
|---|---|
| "XSS vulnerability" | "site lets users see other users' data they shouldn't" |
| "SQL injection risk" | "input field could let someone change the database" |
| "Auth bypass" | "way to skip the login check" |
| "Race condition" | "two things can happen at the same time and step on each other" |

For findings outside this table, use the existing `summary` field if it
already reads in plain English; otherwise summarise in one sentence per
FE-06.

**Action shortcut:** `wpx-findings show --id {id}` (safe; opens for view).

### Blocked tasks

**Reads:**
- `.architecture/{project}/work-packages/BLOCKER-WP-*.md` — explicit
  blocker files
- `.architecture/{project}/work-packages/INDEX.md` — for WP names

**Blocked signal:** presence of BLOCKER-WP-NNN.md file.

**Per-blocker fields used:**
- `wp` — WP ID parsed from filename (`BLOCKER-WP-AUTO-018.md` → `WP-AUTO-018`)
- `reason` — first non-heading paragraph in the BLOCKER file
- `wp_name` — slug from the matching WP file
  (`WP-AUTO-018-observability-adapter.md` → "observability adapter")

**Founder name derivation:** `"{Slug as title case} (WP-NNN)"` —
e.g., `"Observability adapter (WP-AUTO-018)"`. Title-case the slug;
keep the WP ID in parens for operator reference.

**Action shortcut:** open the BLOCKER file for read (safe; no destructive
action available from inbox).

### Decisions waiting on you

**v1: not implemented.** No source-of-truth exists for "explicit founder
decisions awaiting input" — this is part of the planned founder-UX
evolution.

**v2 candidate sources** (when the concierge writes decisions explicitly):
- `.sulis/{project}/decisions-pending.md` — proposed format
- JOURNEY.md fields with `decision_pending: true`

For v1, this category is always empty. Document the placeholder so the
display template knows to omit it (rather than show a confusingly empty
section).

## Phase translation table

For the paused-work display, translate operator phase names to founder
English:

| Operator phase | Founder phrasing |
|---|---|
| `planning` | "planning the next batch" |
| `committing` | "saving changes" |
| `verifying` | "checking the build" |
| `verifying_gates` | "waiting for the review steps" |
| `paused` | "paused" |
| `aborted` | "stopped" |
| `success` | "finished" |

## Doctor checks

The aggregator's `--doctor` flag verifies:

1. `.architecture/{project}/` exists (otherwise the project is mis-named
   or hasn't been initialised yet — distinct from "no items waiting").
2. Each source-path either exists OR is documented as
   may-be-empty (train-runs/ may be empty if no train has run yet;
   findings/ may be empty if no security review has run).
3. The aggregator's parsing logic for each source type runs cleanly on
   any present file (no parse errors).

If doctor finds a source-path missing AND it's not in the
may-be-empty allow-list, it reports the missing source — usually a
sign that this document is stale relative to sulis-execution conventions.
