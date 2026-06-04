"""Working Set — the live reasoning-state artifact for a change/session.

The Working Set is the staging area that carries *current thinking* (problem /
solution / decisions) — and crucially the **why** (rejected alternatives +
rationale) — across a session boundary, so a chain of short sessions doesn't
drift or lose context. Spec: ../docs/working-set-and-session-chain.md.

This module owns only the MECHANICAL, deterministic parts so they're reliable
and testable:
  - the six-section template (`render_initial`),
  - the append-only Working log (`append_log_line`),
  - the conventional on-disk path (`working_set_path`).

The JUDGEMENT parts — *what* goes in each section — are the agent's, done by
editing the file per the `working-set` SKILL. Sections 1–5 are current-state
(overwritten as thinking moves); section 6 is append-only (never edited).

Stdlib only. Python 3.11-safe.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

_LOG_HEADING = "## 6. Working log"


def working_set_path(repo_root: Path | str, stem: str) -> Path:
    """The conventional path: `{repo_root}/.changes/{stem}.WORKING-SET.md`.

    `stem` is the change's `{primitive}-{slug}` (matching the sibling
    `.changes/{stem}.SPEC.md` / `.RECON.md` / `.scenarios.jsonld`).
    """
    return Path(repo_root) / ".changes" / f"{stem}.WORKING-SET.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def render_initial(stem: str, *, intent: str = "", at: str | None = None) -> str:
    """The six-section Working Set template, seeded for a fresh change/session."""
    at = at or _now_iso()
    problem = intent.strip() if intent.strip() else "_(not yet framed — state the situation / complication / question)_"
    return f"""# Working Set — {stem}

> Live reasoning state for this change/session. **Read at the START of every turn;
> update as a side-effect of each decision** (never as a separate chore — that's
> how it dies). Sections 1–5 are current-state (overwritten as thinking moves);
> section 6 is append-only (never edited). Crystallizes into Opportunity / Design
> / Decision at the session boundary; if a session ends abruptly, this file IS
> the handoff to the next. Spec: plugins/sulis/docs/working-set-and-session-chain.md.

## 1. Problem  (→ Opportunity)
{problem}

## 2. Current best solution  (→ Design)
_(not yet established)_

## 3. Decisions in flight  (→ Decision; status: proposed)
_(none yet — one entry per non-trivial choice being weighed: the choice, options
considered, rejected alternatives + rationale, status proposed→accepted on lock)_

## 4. Open questions / unknowns
_(none yet — the live "what we still don't know" parking lot)_

## 5. Rejected so far  (→ Decision.rejected_alternatives)
_(none yet — paths tried and abandoned, **with the why**)_

{_LOG_HEADING}  (append-only)
- {at} — Working Set created.
"""


def append_log_line(content: str, message: str, *, at: str | None = None) -> str:
    """Append a timestamped one-liner to the append-only Working log (section 6).

    The log is the last section, so the line appends at end-of-file. Returns the
    new content. Raises if the Working log heading is absent (a malformed file).
    """
    if _LOG_HEADING not in content:
        raise ValueError(
            f"Working Set is malformed — no '{_LOG_HEADING}' section to append to"
        )
    at = at or _now_iso()
    line = f"- {at} — {message.strip()}"
    body = content.rstrip("\n")
    return f"{body}\n{line}\n"
