#!/usr/bin/env python3
"""_assert_no_depth_doc_gate.py — assert no skill/agent file conditions
document-section existence on depth (SC-04, FR-03).

The load-bearing decoupling (ADR-001): depth sizes the interview, never which
document sections exist. The bypass this catches is a branch that reads the
depth decision and *skips a section* when the change is "small" — e.g.
``if depth == 'lite': skip the nfr section``. This static inspector greps the
given skill/agent files for such a branch and exits non-zero if it finds one.

The detection is deliberately conservative: it fires only when a depth token
(``depth`` or ``classify_depth``) appears in a *conditional* line whose branch
also carries a section-emission verb (``skip``, ``omit``, ``drop``, ``emit``,
``include``, ``write``, …) near a section/doc noun — either on the same line or
in the conditional's body. Plain prose that *describes* depth (e.g. "depth
sizes only the interview, never which sections exist") does not fire, because
it carries no conditional keyword.

This is a text inspector over source files, not a markdown-section parser, so
it does not use ``_doc_section_parse`` — there are no document sections to
parse here, only source lines to scan.

Usage:
    _assert_no_depth_doc_gate.py <skill/agent file> [<file> ...]

Exit codes:
  0 — no depth→doc-emission branch found in any file
  1 — at least one suspect branch found (file:line + the line on stderr)
  2 — bad input (a file unreadable, or no files given)

Pure inspector — reads the files, no other I/O. Stdlib only. Python 3.11-safe.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# A line is "conditional" if it carries a branch keyword.
_CONDITIONAL_RE = re.compile(r"\b(if|elif|unless|when|case|switch|\?)\b", re.IGNORECASE)

# A depth token: the variable/function, or a depth *value* used as one.
_DEPTH_RE = re.compile(r"\b(classify_depth|depth)\b", re.IGNORECASE)

# A section-emission verb paired with a section/doc noun on the same line.
_EMISSION_RE = re.compile(
    r"\b(skip|omit|drop|exclude|emit|include|write|render|add|produce|generate)\b"
    r".{0,40}?"
    r"\b(section|nfr|doc|document|threat\s*model|use\s*cases?|persona|contract)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class DepthGateFinding:
    """One suspect line that conditions section emission on depth."""

    path: str
    line_no: int
    line: str


# How many following lines after a conditional-on-depth header to scan for a
# section-emission verb. A gating branch's body is normally the next statement;
# a small window keeps the match local without over-reaching into unrelated
# prose further down the file.
_BODY_WINDOW = 3


def find_depth_doc_gates(path: str, text: str) -> list[DepthGateFinding]:
    """Return a finding per line in ``text`` that conditions document-section
    existence on depth. Two shapes are caught:

    1. **Single-line:** a conditional line that mentions a depth token AND
       pairs a section-emission verb with a section/doc noun, e.g.
       ``emit the nfr section only if depth is deep``.
    2. **Header + body:** a conditional line mentioning a depth token (e.g.
       ``if depth == 'lite':``) whose following block (within a small window)
       carries the section-emission verb + noun, e.g. a next line
       ``skip the nfr section``.

    Plain prose that only *describes* depth never fires: it carries no
    conditional keyword, so neither shape matches."""
    lines = text.splitlines()
    findings: list[DepthGateFinding] = []
    for i, line in enumerate(lines):
        if not (_CONDITIONAL_RE.search(line) and _DEPTH_RE.search(line)):
            continue
        # Shape 1: everything on this one line.
        if _EMISSION_RE.search(line):
            findings.append(
                DepthGateFinding(path=path, line_no=i + 1, line=line.strip())
            )
            continue
        # Shape 2: the conditional header is on this line; look for the
        # section-emission verb in the body that follows.
        for body_line in lines[i + 1 : i + 1 + _BODY_WINDOW]:
            if _EMISSION_RE.search(body_line):
                findings.append(
                    DepthGateFinding(
                        path=path,
                        line_no=i + 1,
                        line=f"{line.strip()} … {body_line.strip()}",
                    )
                )
                break
    return findings


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="_assert_no_depth_doc_gate.py",
        description="Exit 0 iff no file conditions document-section existence on depth.",
    )
    parser.add_argument("files", nargs="+", help="Skill/agent files to scan.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    all_findings: list[DepthGateFinding] = []
    for path in args.files:
        try:
            text = Path(path).read_text(encoding="utf-8")
        except OSError as exc:
            print(f"error: cannot read {path}: {exc}", file=sys.stderr)
            return 2
        all_findings.extend(find_depth_doc_gates(path, text))

    if all_findings:
        for f in all_findings:
            print(
                f"{f.path}:{f.line_no}: section emission appears to branch on depth: "
                f"{f.line}",
                file=sys.stderr,
            )
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
