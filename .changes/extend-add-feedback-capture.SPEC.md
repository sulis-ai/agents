---
founder_facing: false
---
# Spec — add /sulis:feedback + extract shared issue-capture engine

**Change:** CH-01KSNT · extend
**Closes:** [#20](https://github.com/sulis-ai/agents/issues/20) (the EP-03 extraction trigger)

## What this should do

Two things, **deliberately bundled** per #20 ("extract the type-agnostic
engine IN THE SAME change as the second type; never copy-paste
`_lessons.py`"):

### A. Extract the shared issue-capture engine (closes #20)

Today `plugins/sulis/scripts/_lessons.py` and
`plugins/sulis/scripts/sulis-lessons` together implement a complete
*item → GitHub issue* pipeline for one type (lessons). With feedback
landing as the **second consumer**, the right move is to split the
type-agnostic engine from the per-type configuration:

- **`_issues.py`** (new) — type-agnostic core. Functions:
  `partition_items(items, existing_titles, descriptor) -> {to_create,
  duplicates, skipped}`. The dedup-key normalisation and the
  prefix-strip logic become parameterised. No `lesson:`-specific strings
  remain in this module.
- **`_issue_descriptors.py`** (new) — descriptor registry. Each entry:
  `name`, `title_prefix`, `actionable_dispositions`, `label_set`,
  `extra_labels_for_disposition`, `format_title(item) -> str`,
  `format_body(item) -> str`. Two entries: `LESSON` and `FEEDBACK`.
- **`sulis-issues`** (new) — generic CLI. Replaces `sulis-lessons`.
  `capture --descriptor {lesson|feedback} --items-file <path.json>
  [--repo OWNER/NAME] [--dry-run]`. Dispatch picks the descriptor by
  name and calls the engine.
- **`_lessons.py`** — deleted; its content split between
  `_issues.py` (engine bits) and `_issue_descriptors.py` (lesson-
  specific bits).
- **`sulis-lessons`** — deleted; the one caller
  (`/sulis:capture-lessons` SKILL.md) is updated to call
  `sulis-issues capture --descriptor lesson`. Pure call-site update;
  no behavioural change.
- **Tests** — `test_lessons.py` split into `test_issues_engine.py`
  (parametrised over descriptors) and `test_issue_descriptors.py`
  (per-descriptor fixtures). Existing 25+ test assertions kept; only
  the import paths change.

**Why the engine is genuinely extractable:** the existing 101-line
`_lessons.py` already separates the pure triage/dedup logic (`partition_lessons`,
`dedup_key`, `_title_to_key`) from the type-specific bits
(`_TITLE_PREFIX`, `ACTIONABLE_DISPOSITIONS`, `lesson_issue_title`,
`lesson_issue_body`, `lesson_labels`). The extraction moves the type-
specific names into a descriptor and parameterises the engine — no
behaviour change for the lesson path.

### B. Add the `/sulis:feedback` skill

A founder-facing skill that captures session context and submits a
GitHub issue against the open-source plugin repo (`sulis-ai/agents`).

**Trigger:** on-demand via `/sulis:feedback`. (Not auto-suggested at
session end — that's a follow-up if useful.)

**Capture scope (per founder decision in this session):** the recent
conversation (assistant + user exchanges, last ~30 turns) + the current
change's `JOURNEY.md` / `SPEC.md` if any + recently-shipped changes
(last 3 from the global change store). Best signal for surfacing
patterns + bugs in context.

**Disposition vocabulary:** `pattern` / `issue` / `bug` / `feedback`.
(Mapped to GitHub labels `feedback` + `pattern` / `bug` / `issue` as
sub-labels.)

**Anonymisation policy (per founder decision in this session): default-
redact, founder opts back in.** Strings that look like they MIGHT be
sensitive get redacted to a placeholder; the founder previews the
redacted version and can untick specific redactions to keep them.
Trust-by-default; reveal-by-choice.

**What gets scrubbed by default:**

| Category | Pattern | Replacement |
|---|---|---|
| File paths | absolute paths matching `/(Users|home|repos)/...`, or any string with ≥ 2 path separators | `<path>` |
| Project-specific identifiers | the founder's repo name, top-level dir names of their projects, branch names matching `change/{primitive}-{slug}` | `<project>` / `<branch>` |
| Secret-shaped tokens | strings ≥ 20 chars matching `[A-Za-z0-9_\-]+` AND any string in env-var-named `*KEY*`/`*SECRET*`/`*TOKEN*`/`*PASSWORD*` | `<secret>` |
| Email addresses | RFC 5322 simplified pattern | `<email>` |
| Domain names | non-public-domain heuristic (anything not in a small list of well-known public domains: github.com, anthropic.com, claude.ai, openai.com, npmjs.com, pypi.org, ietf.org, etc.) | `<domain>` |
| GitHub PR / issue refs in OTHER repos | `org/repo#N` where org/repo is not `sulis-ai/agents` | `<other-pr>` |
| Code snippets (when the founder pastes one) | any fenced code block ≥ 5 lines | `<code-snippet-{N}-lines>` placeholder; preview lists each block with line count so founder can opt-in |

Public-domain allowlist (safe to keep): `github.com`, `anthropic.com`,
`claude.ai`, `claude.com`, `openai.com`, `npmjs.com`, `pypi.org`,
`ietf.org`, `w3.org`, `mozilla.org`, `python.org`, `nodejs.org`,
`docker.com`, `kubernetes.io`, `mobbin.com`.

**`sulis-ai/agents` references are PRESERVED** — those are public-repo
context maintainers need to triage the feedback.

**The preview gate is load-bearing.** Founder MUST see the redacted
version before submission, with each redaction listed + an opt-in
control. No `--auto-submit` flag. The skill shows:

```
Preview of feedback to be submitted (8 redactions, preview):

  Title: feedback: <user-supplied-summary>

  Body:
    <anonymised body>

  Redactions detected:
    [1] /Users/iain/Documents/repos/<project>/...  → <path>      [keep / let-stay-redacted]
    [2] my-saas-app                                → <project>   [keep / let-stay-redacted]
    [3] iain@llma.ai                              → <email>     [keep / let-stay-redacted]
    [4-8] ...

  Submit as `feedback: ...` to sulis-ai/agents? (yes / no / edit)
```

### C. Architecture — module structure

```
plugins/sulis/scripts/
├── _issues.py                  ← type-agnostic engine
├── _issue_descriptors.py       ← LESSON + FEEDBACK descriptors
├── _anonymiser.py              ← pure scrubber for feedback
├── sulis-issues                 ← generic CLI (replaces sulis-lessons)
└── tests/unit/
    ├── test_issues_engine.py   ← engine tests, parametrised over descriptors
    ├── test_issue_descriptors.py ← per-descriptor expectations
    ├── test_anonymiser.py      ← scrubber tests
    └── test_sulis_issues.py    ← CLI integration tests (renamed from test_sulis_lessons.py)

plugins/sulis/skills/
├── capture-lessons/SKILL.md    ← updated: calls sulis-issues capture --descriptor lesson
└── feedback/SKILL.md           ← NEW: gather, anonymise, preview, submit
```

## How we'll know it's done

### Engine extraction (A)

- `_issues.py` exists; pure functions; no I/O; no `lesson:`-specific strings.
- `_issue_descriptors.py` registers `LESSON` and `FEEDBACK` entries.
- `sulis-issues capture --descriptor lesson --items-file <path>` produces
  byte-equivalent output to the old `sulis-lessons capture` (per the
  same input fixture — integration test pins parity).
- `_lessons.py` and `sulis-lessons` files are deleted.
- `/sulis:capture-lessons` SKILL.md updated to invoke the new CLI.
- All existing lesson-path tests pass (renamed but unchanged).

### Feedback skill (B)

- `_anonymiser.py` exists with a default-redact `anonymise(text) ->
  AnonymisationResult` pure function. Unit tests cover each redaction
  category + the keep-list.
- `_issue_descriptors.FEEDBACK` produces correct title/body/labels.
- `sulis-issues capture --descriptor feedback --items-file <path>`
  posts a `feedback`-labelled issue (dry-run pinned via integration).
- `/sulis:feedback` SKILL.md gathers context, presents the preview,
  honours the keep/redact choices, and submits.

### Integration

- Full unit + integration suite green; no regression on lesson path.
- Step 4.5 review gate (#30) PASS.
- A live dry-run of `/sulis:feedback` in this session against a small
  hand-built feedback item produces a clean preview that scrubs the
  documented categories.

## What to avoid

- **No copy-paste.** Per #20, copy-pasting `_lessons.py` into
  `_feedback.py` is the EP-03 anti-pattern this change explicitly
  exists to prevent. The engine must be shared.
- **No `--auto-submit` on feedback.** The preview gate is non-optional;
  this is a public-repo write that includes founder context. Always
  gate.
- **Do not scrub `sulis-ai/agents` references.** Those are the public
  triage context.
- **Do not break the existing lesson submission flow.** Migration must
  be byte-equivalent at the CLI surface for lessons.

## Verification plan

Each stage gets its own commit and its own test green:

1. **Stage 1: Engine extraction.** Move `_lessons.py` into
   `_issues.py` + `_issue_descriptors.LESSON`; create `sulis-issues`;
   delete `sulis-lessons`; update `/sulis:capture-lessons` SKILL.md;
   move + rename tests. Run full unit + integration suite — green.
2. **Stage 2: Feedback descriptor.** Add
   `_issue_descriptors.FEEDBACK`; tests for the descriptor (title
   prefix, label set, disposition mapping); integration test for
   `sulis-issues capture --descriptor feedback` end-to-end.
3. **Stage 3: Anonymiser.** Add `_anonymiser.py`; unit tests cover
   path / project / secret / email / domain / code-block scrubbing
   plus the keep-list. Default-redact policy enforced.
4. **Stage 4: Feedback skill.** Add `/sulis:feedback` SKILL.md
   orchestrating gather → anonymise → preview → submit. Skill
   integration: a hand-built scenario in this session previews and
   submits cleanly.

Each stage's tests stay green when the next stage adds code; the four
commits land as one PR.

## References

- `plugins/sulis/scripts/_lessons.py` — current pure core (101 lines)
- `plugins/sulis/scripts/sulis-lessons` — current gh-backed CLI
- `plugins/sulis/scripts/tests/unit/test_lessons.py` — existing tests
- `plugins/sulis/skills/capture-lessons/SKILL.md` — sole production
  caller of `sulis-lessons`
- Issue [#20](https://github.com/sulis-ai/agents/issues/20) — the
  extraction trigger
- `plugins/sulis/references/engineering-principles.md` EP-03 —
  "Extract on the 2nd consumer, not before, not after"
