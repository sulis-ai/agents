# Non-Functional Requirements: Auto Codebase Mapping

## Performance

| ID | Requirement | Metric | Target | Measurement Method |
|----|-------------|--------|--------|-------------------|
| NFR-P01 | Staleness check must not noticeably delay session start | Wall clock time for staleness check | < 2 seconds for projects with up to 10,000 source files | Time from session start to first user-facing question |
| NFR-P02 | Background mapping must not degrade facilitation responsiveness | Agent response latency during mapping | No measurable increase vs. sessions without mapping | Compare response times with and without background mapping |

## Reliability

| ID | Requirement | Metric | Target | Measurement Method |
|----|-------------|--------|--------|-------------------|
| NFR-R01 | Mapping failure must not disrupt facilitation | Session continuation after mapping error | 100% — facilitation proceeds with no index | Induce mapping failure, verify facilitation continues |
| NFR-R02 | Staleness check must detect uncommitted work | Detection of new/modified files not yet committed | Files with mtime > mapped_at are detected regardless of git status | Modify a file without committing, verify rescan triggers |

## Usability

| ID | Requirement | Metric | Target | Measurement Method |
|----|-------------|--------|--------|-------------------|
| NFR-U01 | Greenfield skip must be invisible to the user | User awareness of mapping absence | Zero messages about missing codebase | Review session transcript for any mapping-related output |
| NFR-U02 | Overlay must feel natural, not mechanical | User perception of context introduction | Context woven into reflection, not announced separately | Review session transcript for standalone "mapping complete" messages |

**NFR Quality Criteria:** Every NFR above is measurable (specific threshold), testable
(pass/fail against threshold), and traceable (linked to a functional requirement).
