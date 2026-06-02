<!-- fixture: PASS shape B — fully populated backend Verification Plan + deferred follow-on. -->
<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->

# Synthetic SRD — pass_b_complete_backend

## Verification Plan

### Q1. Posture
Behavioural API test against a running service, persistence assertion on the orders table seam, and an idempotency / replay check on the POST endpoint per the backend adapter shape.

### Q2. Integrations
- Postgres: shared dev cluster, idempotency assertion on the upsert path.
- SendGrid: deferred to a follow-on (recording-mock-sendgrid) per ADR-003 Shape 2.

### Q3. Adapter
backend adapter applies; no additional adapters needed.

### Q4. Infrastructure
- existing: infra/placeholder.py
