<!-- fixture: triggers P-VER 9.04 — `existing:` cites a path that does not resolve. -->
<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->

# Synthetic SRD — fail_04_hallucinated_infrastructure

## Verification Plan

### Q1. Posture
Behavioural API test against a running service plus persistence assertion on the canonical seam.

### Q2. Integrations
- Redis: shared dev cluster, idempotency assertion on the dedupe path.

### Q3. Adapter
backend adapter applies; no additional adapters required.

### Q4. Infrastructure
- existing: this/path/does/not/exist.py
