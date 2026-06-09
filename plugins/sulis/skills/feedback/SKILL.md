---
name: feedback
description: "Sends a redacted feedback issue to the open-source Sulis repo so the maintainers hear what's working and what isn't."
---

# /sulis:feedback — send feedback to the marketplace maintainers

## Conclusion (lead with the answer)

Sometimes you notice something using Sulis that the maintainers should know
about — a recurring pattern that bites you, a corner where the docs are wrong,
an outright bug, or just product feedback. This skill **captures that into a
GitHub issue against the open-source plugin repo** (`sulis-ai/agents`) so the
maintainers can see it on their backlog — with **personal + proprietary
context scrubbed by default**, and a preview you confirm before anything is
submitted.

It is an orchestrator: the anonymisation lives in
`../../scripts/_anonymiser.py` (pure, deterministic, default-redact) and the
gh issue creation in `../../scripts/sulis-issues` (parameterised on the
`feedback` descriptor). The skill gathers session context, runs the redaction
pipeline, presents the preview, honours your keep/redact choices, and submits.

## Disposition — what kind of feedback?

You pick one when you start the skill. All four become GitHub issues — the
disposition becomes a sub-label so the maintainers can triage by class:

| Disposition | What it means | Labels |
|---|---|---|
| `pattern` | A recurring thing you've noticed across changes | `feedback`, `pattern` |
| `issue` | Something not quite right (UX, docs, naming, ordering) | `feedback`, `issue` |
| `bug` | Something outright broken | `feedback`, `bug` |
| `feedback` | General comments / suggestions / praise / criticism | `feedback` |

## Anonymisation — default-redact, you opt back in

The privacy contract is **trust-by-default, reveal-by-choice**. Eight
categories are scrubbed automatically; you see the preview with each
redaction listed; you can untick specific ones (move them to the
keep-list) before submission.

| Category | Triggers | Becomes |
|---|---|---|
| Code blocks ≥ 5 lines | fenced ` ``` ` blocks | `<code-snippet:N-lines>` |
| URLs | `https?://...` | preserved if host is allowlisted (github.com, anthropic.com, claude.ai, python.org, mobbin.com, stripe.com, etc.), else `<url>` |
| Secrets | env-var-named assignments + JWTs + opaque tokens with known prefixes (sk_, ghp_, AKIA, AIza, …) | `<secret>` (env-var name preserved) |
| Emails | `user@host.tld` | `<email>` |
| Other-repo refs | `org/repo#N` where org/repo ≠ sulis-ai/agents | `<other-repo>#N` (number preserved) |
| File paths | absolute (`/Users/`, `/home/`, `/private/`, `/var/`, `/tmp/`) + relative paths ≥ 2 separators | `<path>` |
| Domains | not in the public allowlist | `<domain>` |
| Project context | your project names (auto-detected) + change-branch refs | `<project>` / `<branch>` |

`sulis-ai/agents` references are **always preserved** — they're the
maintainer's own triage context. The complete allowlist + scrub policy
lives in `../../scripts/_anonymiser.py` (pinned in
`../../scripts/tests/unit/test_anonymiser.py`).

## Resolving the tool path (MUST — first action)

```bash
# Resolve from the ACTIVE plugin version (its bin/ is on PATH) — avoids the
# lexical-sort cache pick that mis-ranks 0.98.0 above 0.126.0 (#49).
SCRIPTS_DIR=""
_sulis_bin=$(printf '%s\n' "$PATH" | tr ':' '\n' | grep -E 'sulis-ai-agents/sulis/[^/]+/bin$' | head -1)
[ -n "$_sulis_bin" ] && [ -d "$(dirname "$_sulis_bin")/scripts" ] \
  && SCRIPTS_DIR="$(dirname "$_sulis_bin")/scripts"
# Dev fallback: marketplace repo cwd.
if [ -z "$SCRIPTS_DIR" ] && [ -f "plugins/sulis/scripts/sulis-issues" ]; then
  SCRIPTS_DIR="$(pwd)/plugins/sulis/scripts"
fi
# Last-resort: PORTABLE numeric (NOT lexical, NOT `sort -V`) cache pick.
[ -z "$SCRIPTS_DIR" ] && SCRIPTS_DIR=$(find ~/.claude/plugins/cache -name sulis-issues -type f \
  -path '*/sulis/*/scripts/*' 2>/dev/null \
  | sed -E 's#(.*/sulis/)([^/]+)(/scripts/.*)#\2 &#' \
  | sort -t. -k1,1n -k2,2n -k3,3n | tail -1 | cut -d' ' -f2- | xargs -I{} dirname {} 2>/dev/null)
[ -z "$SCRIPTS_DIR" ] && { echo "ERROR: cannot find sulis-issues" >&2; exit 1; }
```

## When invoked

**1. Ask the founder one short question to pick the disposition.** Show the
four options as the table above; let them pick by name or number. Do NOT
proceed with a default; the disposition shapes the labels and the maintainer
triage.

**2. Ask for the headline + the body.** Two short messages:

> *Headline — one sentence (becomes the issue title):*
>
> *Details — what should the maintainers know? Walk me through what
> happened or what you noticed.*

Keep the headline ≤ ~10 words; it becomes the dedup anchor.

**3. Gather session context** (per the capture scope decision):

- The recent conversation — last ~30 turns of assistant + user exchange.
- The active change's `JOURNEY.md` / `.changes/{primitive}-{slug}.SPEC.md`
  if any (resolve via `SULIS_CHANGE_ID` env var if set; otherwise skip).
- The 3 most recently shipped changes from
  `~/.sulis/changes/*/change.json` (read via `list_all_changes()` in
  `_change_state.py`; cap at 3 most recent by `created_at`).

Compose into a single blob (founder body + context, separated by clear
headings). The blob is what gets anonymised + becomes the GitHub issue body.

**4. Detect the project name(s)** so the anonymiser can scrub them:

- The current repo's basename (`git rev-parse --show-toplevel | xargs
  basename`).
- The change worktree's project component if `SULIS_CHANGE_ID` is set
  (`git rev-parse --show-toplevel`).

Pass these to the anonymiser via `AnonymisationContext.project_names`.

**5. Run the anonymisation pipeline** (Python one-liner using `_anonymiser`):

```bash
python3 -c "
import sys; sys.path.insert(0, '$SCRIPTS_DIR')
from _anonymiser import anonymise, AnonymisationContext
import json
context = AnonymisationContext(
    project_names=['<detected-project-name>', ...],
    keep_strings=[],  # extends per founder choices in step 6
)
r = anonymise(open('/tmp/feedback-raw.txt').read(), context)
print(json.dumps({
    'redacted_text': r.redacted_text,
    'redactions': [
        {'category': red.category, 'original': red.original,
         'placeholder': red.placeholder}
        for red in r.redactions
    ],
}))
"
```

**6. Present the preview + redaction list to the founder.** Plain English,
numbered redactions:

> *Preview — what'll be submitted to `sulis-ai/agents`:*
>
> *Title:* `feedback: <headline>`
>
> *Body (after {N} redactions):*
> ```
> <redacted-text>
> ```
>
> *Redactions detected:*
> *  [1] `/Users/iain/Documents/...`     → `<path>`*
> *  [2] `my-saas-app`                   → `<project>`*
> *  [3] `iain@llma.ai`                  → `<email>`*
> *  ...*
>
> *Anything you want to keep instead of redacting? Tell me a number ("keep
> #2") or the value ("keep iain@llma.ai"). Or "looks good" to send.*

If the founder asks to keep some, **re-run anonymise with the chosen strings
added to `keep_strings`** and re-present the preview. Loop until they say
"looks good" (or "cancel").

**7. Submit when the founder confirms.** Write the items array to a temp
file then call `sulis-issues capture`:

```bash
python3 -c "
import json
items = [{
    'id': 'FB-' + '$change_id'[-6:].upper() if '$change_id' else 'FB-001',
    'title': '<headline>',
    'body': '<final-redacted-body>',
    'disposition': '<pattern|issue|bug|feedback>',
    'redactions_applied': <N>,
}]
open('/tmp/feedback-items.json', 'w').write(json.dumps(items))
"

python3 "$SCRIPTS_DIR/sulis-issues" capture --descriptor feedback \
  --items-file /tmp/feedback-items.json --repo sulis-ai/agents
```

The `--repo sulis-ai/agents` is **hardcoded**: this skill always submits
upstream to the open-source plugin repo (the founder's own repo is never the
target).

**8. Report.** Parse the JSON output. If `created` is non-empty:

> *Sent. Tracking issue: `<URL>`. The maintainers will see it with the
> `feedback` + `<disposition>` labels on their backlog. Thanks.*

If `degraded: true` (no gh on PATH, or not authenticated):

> *I couldn't reach GitHub right now ({reason}), so I haven't sent
> anything. Your redacted feedback is saved at `/tmp/feedback-items.json`
> — you can submit it manually later, or paste the body into
> `sulis-ai/agents` issues yourself.*

If `duplicates` is non-empty (your feedback matches an open one):

> *That feedback is already open as `<URL>` — I haven't created a duplicate.
> Want to add a comment to the existing one instead?*

## Gotchas

- **No `--auto-submit` flag.** The preview gate is the privacy contract.
  Every submission goes through founder review. If a future caller asks
  for an unattended path, the answer is "no" — change the gate, change the
  trust model. (MUC: privacy)
- **The repo is hardcoded to `sulis-ai/agents`.** This skill is for
  upstream maintainer feedback only — never the founder's own repo. If
  the founder wants to file something in their own repo, that's a regular
  `gh issue create`. (MUC: target)
- **Anonymisation isn't a guarantee.** It's a best-effort scrub plus a
  founder-review gate. The combination is the contract; either alone would
  be insufficient. If the founder confirms a redaction-preserved value
  that's actually sensitive, that's their call — say so plainly before
  submission.
- **The `sulis-ai/agents` reference is preserved by design.** Linking back
  to the maintainer's own repo issues + PRs is essential context for
  triage; the anonymiser explicitly skips it. Don't "fix" this.
- **Code blocks ≥ 5 lines are placeholders.** Short snippets (≤ 4 lines —
  the error line, the two-line repro) survive intact because they're
  signal-dense + low-risk. Founders can keep a longer block via the
  preview opt-in if they need to. (See test fixture in
  `test_anonymiser.py::test_long_code_block_is_replaced_with_line_count_placeholder`.)
- **The disposition is the founder's call.** Don't auto-classify their
  feedback as a "bug" if they said "issue" — the maintainer triage
  depends on the human-tagged class.

## See also

- `../../scripts/_anonymiser.py` — the pure scrubber (pass-by-pass)
- `../../scripts/_issue_descriptors.py` — `FEEDBACK` descriptor
- `../../scripts/sulis-issues` — the gh-backed capture CLI
- `../capture-lessons/SKILL.md` — the cousin skill (same engine, different
  descriptor, different audience: lessons capture is the agent's
  retrospective; feedback capture is the founder's voice)
