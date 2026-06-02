<!-- fixture-companion SRD; the failure under test lives in WP-FIX008.md. -->
<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->

# Synthetic SRD — fail_08_adapter_mismatch

## Verification Plan

### Q1. Posture
Behavioural API test against a running service plus persistence assertion on the orders table seam.

### Q2. Integrations
- Postgres: shared dev cluster, idempotency assertion on the upsert path.

### Q3. Adapter
backend adapter applies; no additional adapters required.

### Q4. Infrastructure
- existing: infra/placeholder.py
