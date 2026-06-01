<!-- fixture: PASS shape C — fully populated infrastructure Verification Plan. -->
<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->

# Synthetic SRD — pass_c_complete_infrastructure

## Verification Plan

### Q1. Posture
Apply-and-rollback integration test against an ephemeral target environment plus a drift-check after apply and a cost / quota guardrail on the resources provisioned.

### Q2. Integrations
- Terraform Cloud: shared dev workspace, apply-and-rollback assertion on the test workspace.

### Q3. Adapter
infrastructure adapter applies; no additional adapters required.

### Q4. Infrastructure
- existing: infra/placeholder.py
