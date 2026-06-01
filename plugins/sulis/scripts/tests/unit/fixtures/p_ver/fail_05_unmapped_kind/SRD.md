<!-- fixture: triggers P-VER 9.05 — change `kind: data-migration` is not in the 7-row adapter table. -->
<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->

# Synthetic SRD — fail_05_unmapped_kind

## Verification Plan

### Q1. Posture
A backfill migration script with idempotency on the row dedupe key and a dry-run/apply split.

### Q2. Integrations
- Postgres: production read replica during the dry-run, primary during apply.

### Q3. Adapter
no adapter row exists for `kind: data-migration`; this fixture exists to prove 9.05 fires before any per-artifact check runs.

### Q4. Infrastructure
- existing: infra/placeholder.py
