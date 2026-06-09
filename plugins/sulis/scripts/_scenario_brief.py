"""Dispatch-brief assembler — read-only, change-scoped (WP-005, ADR-004).

Produces an ephemeral, right-sized context brief that seeds a fresh subagent
context for one scenario-RUN's dispatch. The brief is assembled from:

  1. a READ-ONLY slice of the CHANGE-scoped working-set — sections 1-3 only
     (problem / current-best-solution / decisions-so-far); and
  2. the scoped contract — the seam's I/O + the scenario definition (its
     verdict_invariant + isolation, the WP-001 fields) + the relevant SPEC
     slice.

NOT the whole session history (that is the context-drift failure this closes),
NOT the append-only working log (§6), NOT the whole SPEC.

Two hard scope-guards, both pure consequences of this module's design:

  - #91 — the working-set stays CHANGE-scoped and UNMUTATED. The assembler opens
    the working-set for READ ONLY (no "w"/"a"/temp-then-replace). A unit test
    asserts the working-set file's bytes are byte-for-byte unchanged after
    assembly.
  - The brief is DERIVED and EPHEMERAL: returned as an in-memory dict, never
    persisted into the working-set, never written under .changes/ at run
    granularity. Per-run durable state stays on TestRun/TestResult (the existing
    ledger).

Contract: contracts/dispatch-brief.contract.md. Consumer: the subagent-dispatch
entrypoint (adapter layer, exercised by WP-006 — out of this module's scope).

Stdlib only. Python 3.11-safe.
"""

from __future__ import annotations

import re
from pathlib import Path

# Working-set section headings are `## N. Title …`. We capture the numbered
# section bodies and use sections 1-3 only; everything else (4, 5, the
# append-only working log §6) is deliberately excluded so a large working-set
# never bloats the fresh context.
_SECTION_HEADING = re.compile(r"^##\s+(\d+)\.\s", re.MULTILINE)

# A decision line in §3 is a top-level bullet (`- …`). We keep the bullet text,
# stripping the leading marker; nested/continuation lines are folded onto their
# parent bullet.
_BULLET = re.compile(r"^-\s+(.*)$")


def _split_sections(text: str) -> dict[int, str]:
    """Return {section_number: body_text} for every `## N. …` heading.

    Pure text parsing — the input string is never mutated and the source file is
    never reopened. A heading with no body yields an empty-string body.
    """
    sections: dict[int, str] = {}
    matches = list(_SECTION_HEADING.finditer(text))
    for idx, match in enumerate(matches):
        number = int(match.group(1))
        body_start = match.end()
        # Body runs from the end of this heading line to the start of the next
        # numbered heading (or end-of-file for the last section).
        body_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        # Drop the remainder of the heading line itself (the title text after
        # `## N.`), keeping only the lines below it.
        body = text[body_start:body_end]
        newline = body.find("\n")
        body = body[newline + 1 :] if newline != -1 else ""
        sections[number] = body.strip()
    return sections


def _prose(body: str) -> str:
    """Collapse a section body to single-spaced prose (drop blank lines)."""
    lines = [line.strip() for line in body.splitlines()]
    return " ".join(line for line in lines if line)


def _decisions(body: str) -> list[str]:
    """Extract top-level decision bullets from §3.

    Each `- …` bullet becomes one entry; continuation/indented lines are folded
    onto the bullet they belong to so a multi-line decision stays one item.
    """
    decisions: list[str] = []
    for raw in body.splitlines():
        bullet = _BULLET.match(raw.strip())
        if bullet:
            decisions.append(bullet.group(1).strip())
        elif raw.strip() and decisions:
            # Continuation of the current decision — fold onto it.
            decisions[-1] = f"{decisions[-1]} {raw.strip()}"
    return decisions


def assemble_brief(*, working_set_path: Path | str, scoped_contract: dict) -> dict:
    """Assemble the read-only dispatch brief for one scenario-run.

    Reads the change-scoped working-set (sections 1-3 ONLY) and pairs it with the
    caller-supplied scoped contract (seam I/O + scenario definition + spec
    slice). The working-set file is opened READ-ONLY and never modified; the
    returned brief is an ephemeral in-memory dict — it is not persisted and no
    per-run working-set is created.

    Args:
        working_set_path: path to the CHANGE working-set markdown file.
        scoped_contract: the seam's I/O + scenario def + relevant spec slice,
            passed through into the brief's ``scoped_contract`` unchanged.

    Returns:
        The dispatch-brief dict per contracts/dispatch-brief.contract.md.
    """
    text = Path(working_set_path).read_text(encoding="utf-8")
    sections = _split_sections(text)

    working_set_slice = {
        "problem": _prose(sections.get(1, "")),
        "current_solution": _prose(sections.get(2, "")),
        "decisions_so_far": _decisions(sections.get(3, "")),
    }

    return {
        "working_set_slice": working_set_slice,
        "scoped_contract": {
            "seam_io": scoped_contract.get("seam_io", {}),
            "scenario": scoped_contract.get("scenario", {}),
            "spec_slice": scoped_contract.get("spec_slice", ""),
        },
    }
