<!-- fixture: PASS shape A — fully populated methodology Verification Plan. -->
<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->

# Synthetic SRD — pass_a_complete_methodology

## Verification Plan

### Q1. Posture
Structural assertions on the rubric file plus an integration test where a fresh design dispatch produces output matching the new shape — the methodology adapter row from the canonical.

### Q2. Integrations
- Decompose validation rubric: shared markdown file, structural-assertion test against the live file.

### Q3. Adapter
methodology adapter applies; no additional adapters needed for this change.

### Q4. Infrastructure
- existing: infra/placeholder.py
