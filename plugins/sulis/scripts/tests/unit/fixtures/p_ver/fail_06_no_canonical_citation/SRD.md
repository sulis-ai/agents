<!-- fixture: triggers P-VER 9.06 — Verification Plan section present but missing the canonical citation. -->

# Synthetic SRD — fail_06_no_canonical_citation

## Verification Plan

### Q1. Posture
Behavioural API test against a running service plus persistence assertion on the orders table seam.

### Q2. Integrations
- Postgres: shared dev cluster, idempotency assertion on the upsert path.

### Q3. Adapter
backend adapter applies; no additional adapters required.

### Q4. Infrastructure
- existing: infra/placeholder.py
