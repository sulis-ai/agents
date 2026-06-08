# Fixture: clinics-stub (interaction-flow-gate spike)

PATH-shim stub for the **clinics-scheme** interaction flow, used by the WP-004
end-to-end spike to exercise the flow over stand-ins instead of the live
Capsule operator connector / HubSpot. Mirrors the `gh-stubs` precedent at
`plugins/sulis/scripts/tests/fixtures/drift_check/gh-stubs/`.

## How it works

`clinics` is an executable bash shim. The spike test
(`plugins/sulis/scripts/tests/integration/test_interaction_gate_clinics_spike.py`)
runs each of the six flow steps through it:

```
clinics process-documents   # ingest submission docs
clinics find-business       # locate candidate businesses
clinics look-up-business    # pull the matched record
clinics score-risk          # RAG risk score
clinics rate-quote          # rate the quote
clinics push-indication     # push to HubSpot (stubbed — no live call)
```

Each call returns a canned JSON response on stdout and, if
`$CLINICS_STUB_CALL_LOG` is set, appends a `clinics <args>` line to that log.
**The log is the falsifiable `agent-observed` attestation** the interaction-flow
gate later trusts (ADR-001): it records that the flow *was* run, step by step,
over stubs.

`$STUB_MODE` selects the response set (`happy` is the only mode today; the
switch exists so a variant flow — e.g. a declined indication — can be added
without copy-pasting the shim).

## Stub-only guarantee

The spike prepends this directory to `$PATH`, so a bare-name `clinics` resolves
to this in-repo shim — never a live install. The test asserts this three ways
(invocation log, in-repo executable, PATH-prefix resolution), so **no live
third-party / Capsule / HubSpot call occurs** when the flow is exercised
(TDD §3).

## One source of stub logic

The shim lives here once and is reached via a `PATH` prefix, not copy-pasted
into the test — the same discipline as `gh-stubs`.
