# Non-Functional Requirements: Adaptive Coaching Annotations

## Summary

Non-functional requirements for the adaptive coaching system. Because this enhancement
is implemented as prompt instructions (not software), NFRs focus on output quality,
cognitive load, consistency, and session scalability rather than traditional
infrastructure concerns.

---

### Cognitive Load

| ID | Requirement | Metric | Target | Measurement Method |
|----|-------------|--------|--------|-------------------|
| NFR-CL01 | Each coaching annotation adds minimal text to the response | Word count of annotation body | 30 words maximum | Count words in annotation body (excluding blockquote marker and italic markers) |
| NFR-CL02 | No more than one coaching annotation per agent turn | Annotation count per turn | Exactly 0 or 1 | Count blockquote coaching annotations in each agent response |
| NFR-CL03 | Coaching annotations do not appear during reflection checkpoints | Annotation presence at reflection turns | 0 annotations at reflection turns | Verify that turns containing "Let me make sure I've got this right" have no coaching annotations |
| NFR-CL04 | Pattern naming and coaching annotations are independently limited | Count of each per turn | Max 1 pattern naming AND max 1 coaching annotation | Count each type separately in every agent response |

### Consistency

| ID | Requirement | Metric | Target | Measurement Method |
|----|-------------|--------|--------|-------------------|
| NFR-CON01 | Same gap pattern produces same coaching decision regardless of session | Decision consistency across identical scenarios | Identical gap + identical user model state = identical coach/skip decision | Scenario testing with controlled inputs across multiple sessions |
| NFR-CON02 | Annotation format matches specification exactly | Format compliance | 100% of annotations match `> *Label -- explanation.*` | Parse every annotation for format compliance |
| NFR-CON03 | Turn ordering is consistent across all facilitated turns | Position compliance | Acknowledgement before pattern naming before annotation before question, in 100% of turns | Structural analysis of turn content |

### Session Scalability

| ID | Requirement | Metric | Target | Measurement Method |
|----|-------------|--------|--------|-------------------|
| NFR-S01 | Coaching quality does not degrade over long sessions | Relevance of annotations in turns 40-60 vs turns 5-20 | Annotations remain domain-relevant and non-repetitive through turn 60 | Review annotations at late-session turns for relevance and freshness |
| NFR-S02 | Journal entries for coaching do not consume excessive context | Lines added to journal per turn for coaching | 2 lines maximum per turn | Count coaching-related journal lines per turn |
| NFR-S03 | User model transitions occur at appropriate points | Transition timing | Level transitions happen within 2 turns of threshold being met | Track primitive demonstration counts against level transition points |

### Pedagogical Effectiveness

| ID | Requirement | Metric | Target | Measurement Method |
|----|-------------|--------|--------|-------------------|
| NFR-PE01 | Coaching annotations are contextually grounded, not generic | Percentage of annotations referencing the user's specific answer | 100% | Review each annotation for specific reference to user's content |
| NFR-PE02 | Coaching tone complies with coaching tenets | Percentage of annotations free of prohibited phrases | 100% -- no "you need to," "you forgot," "you missed," "you should" | Search annotations for prohibited phrases |
| NFR-PE03 | Mindset skill coaching fires at appropriate pattern thresholds | Threshold accuracy | Mindset skill annotation fires only after 3+ absences of associated primitives | Track absence counts against mindset skill trigger points |

### Rendering

| ID | Requirement | Metric | Target | Measurement Method |
|----|-------------|--------|--------|-------------------|
| NFR-R01 | Annotations render with visual distinction in markdown environments | Rendering correctness | Blockquote with italic renders correctly in GitHub, VS Code, and mermaid.live | Manual rendering verification in each environment |
| NFR-R02 | Annotations remain structurally separated in non-markdown environments | Structural separation in raw text | Blockquote character (`>`) provides line-level separation even without rich rendering | Visual inspection in raw terminal output |
