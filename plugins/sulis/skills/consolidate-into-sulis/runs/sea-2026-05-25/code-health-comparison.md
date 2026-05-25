# Code-health comparison — baseline vs final

**Baseline:** `plugins/sulis/skills/consolidate-into-sulis/runs/sea-2026-05-25/code-health-baseline.json`
**Final:** `plugins/sulis/skills/consolidate-into-sulis/runs/sea-2026-05-25/code-health-final.json`

## Verdict

**REGRESSION** — 5 NEW finding(s) introduced. Investigate and fix forward.

## Counts

- NEW (introduced by consolidation): **5**
- PRE-EXISTING (also in baseline): **5**
- RESOLVED (in baseline, gone in final): **73**

## NEW findings (consolidation-attributed)

Investigate each. Classify as **regression-grade** (fix forward in Commit 6)
or **pre-existing in disguise** (document, don't gate). See
`references/code-health-gating.md` for the rubric.

- `plugins/sea/skills/probe/tests/unit/test_credential_runner.py:180` — `?` [critical]
- `plugins/sea/skills/probe/tests/unit/test_credential_runner.py:46` — `?` [critical]
- `plugins/sea/skills/probe/tests/unit/test_credential_runner.py:59` — `?` [critical]
- `plugins/sulis/skills/analyse-codebase/scripts/probe/workspace.py:269` — `?` [critical]
- `plugins/sulis/skills/analyse-codebase/scripts/probe/workspace.py:40` — `?` [critical]

## RESOLVED findings (improvement from consolidation)

- `plugins/idc/scripts/build_finance_html.py:63` — `?` [high]
- `plugins/idc/scripts/build_investor_financials.py:73` — `?` [high]
- `plugins/idc/scripts/build_pptx.py:206` — `?` [high]
- `plugins/idc/scripts/build_review_html.py:59` — `?` [concern]
- `plugins/idc/scripts/build_web_pitch.py:123` — `?` [concern]
- `plugins/sulis-execution/sdk/typescript/dist/transport.js:75` — `?` [concern]
- `plugins/sulis-execution/sdk/typescript/src/transport.ts:32` — `?` [high]
- `plugins/sulis/_lib/wp_index.py:107` — `?` [concern]
- `plugins/sulis/skills/add-skill/scripts/inventory.py:297` — `?` [concern]
- `plugins/sulis/skills/analyse-codebase/scripts/probe.py:113` — `?` [concern]
- `plugins/sulis/skills/analyse-codebase/scripts/probe.py:179` — `?` [concern]
- `plugins/sulis/skills/analyse-codebase/scripts/probe/detection.py:113` — `?` [concern]
- `plugins/sulis/skills/analyse-codebase/scripts/probe/filesystem.py:107` — `?` [high]
- `plugins/sulis/skills/analyse-codebase/scripts/probe/render.py:211` — `?` [concern]
- `plugins/sulis/skills/analyse-codebase/scripts/probe/render.py:536` — `?` [concern]
- `plugins/sulis/skills/analyse-codebase/scripts/probe/render.py:657` — `?` [high]
- `plugins/sulis/skills/analyse-codebase/scripts/probe/render.py:830` — `?` [high]
- `plugins/sulis/skills/analyse-codebase/scripts/probe/runners/architecture_runner.py:101` — `?` [concern]
- `plugins/sulis/skills/analyse-codebase/scripts/probe/runners/architecture_runner.py:136` — `?` [concern]
- `plugins/sulis/skills/analyse-codebase/scripts/probe/runners/architecture_runner.py:26` — `?` [concern]
- `plugins/sulis/skills/analyse-codebase/scripts/probe/runners/astgrep_capability.py:120` — `?` [concern]
- `plugins/sulis/skills/analyse-codebase/scripts/probe/runners/astgrep_extension.py:27` — `?` [concern]
- `plugins/sulis/skills/analyse-codebase/scripts/probe/runners/coupling_runner.py:35` — `?` [concern]
- `plugins/sulis/skills/analyse-codebase/scripts/probe/runners/credential_runner.py:137` — `?` [concern]
- `plugins/sulis/skills/analyse-codebase/scripts/probe/runners/deadcode_runner.py:72` — `?` [concern]
- `plugins/sulis/skills/analyse-codebase/scripts/probe/runners/deadcode_runner.py:82` — `?` [concern]
- `plugins/sulis/skills/analyse-codebase/scripts/probe/runners/deadcode_runner.py:91` — `?` [concern]
- `plugins/sulis/skills/analyse-codebase/scripts/probe/runners/deployment_runner.py:205` — `?` [high]
- `plugins/sulis/skills/analyse-codebase/scripts/probe/runners/deployment_runner.py:330` — `?` [high]
- `plugins/sulis/skills/analyse-codebase/scripts/probe/runners/deployment_runner.py:337` — `?` [concern]
- `plugins/sulis/skills/analyse-codebase/scripts/probe/runners/deployment_runner.py:436` — `?` [high]
- `plugins/sulis/skills/analyse-codebase/scripts/probe/runners/duplication_runner.py:55` — `?` [concern]
- `plugins/sulis/skills/analyse-codebase/scripts/probe/runners/lint_runner.py:112` — `?` [concern]
- `plugins/sulis/skills/analyse-codebase/scripts/probe/runners/lint_runner.py:118` — `?` [high]
- `plugins/sulis/skills/analyse-codebase/scripts/probe/runners/reuse_runner.py:66` — `?` [concern]
- `plugins/sulis/skills/analyse-codebase/scripts/probe/runners/test_runner.py:158` — `?` [concern]
- `plugins/sulis/skills/analyse-codebase/scripts/probe/runners/test_runner.py:167` — `?` [concern]
- `plugins/sulis/skills/analyse-codebase/scripts/probe/runners/test_runner.py:211` — `?` [concern]
- `plugins/sulis/skills/analyse-codebase/scripts/probe/runners/wrapper_runner.py:32` — `?` [concern]
- `plugins/sulis/skills/analyse-codebase/scripts/probe/workspace.py:137` — `?` [concern]
- `plugins/sulis/skills/analyse-codebase/tests/fixtures/ts_simple/src/PaymentProcessor.ts:2` — `?` [concern]
- `plugins/sulis/skills/check-build/scripts/builder.py:158` — `?` [concern]
- `plugins/sulis/skills/check-build/scripts/builder.py:538` — `?` [concern]
- `plugins/sulis/skills/check-build/scripts/builder.py:607` — `?` [concern]
- `plugins/sulis/skills/check-build/scripts/builder.py:88` — `?` [concern]
- `plugins/sulis/skills/check-maintainability/scripts/scanner.py:122` — `?` [concern]
- `plugins/sulis/skills/check-maintainability/scripts/scanner.py:226` — `?` [high]
- `plugins/sulis/skills/check-maintainability/scripts/scanner.py:325` — `?` [concern]
- `plugins/sulis/skills/check-maintainability/scripts/scanner.py:534` — `?` [high]
- `plugins/sulis/skills/check-polish/scripts/scanner.py:356` — `?` [concern]
- `plugins/sulis/skills/check-polish/scripts/scanner.py:97` — `?` [concern]
- `plugins/sulis/skills/check-readability/scripts/audit.py:466` — `?` [concern]
- `plugins/sulis/skills/check-readability/scripts/audit.py:669` — `?` [concern]
- `plugins/sulis/skills/check-reliability/scripts/scanner.py:168` — `?` [high]
- `plugins/sulis/skills/check-reliability/scripts/scanner.py:448` — `?` [concern]
- `plugins/sulis/skills/check-security/scripts/scanner.py:229` — `?` [concern]
- `plugins/sulis/skills/check-security/scripts/scanner.py:446` — `?` [concern]
- `plugins/sulis/skills/check-security/scripts/scanner.py:523` — `?` [concern]
- `plugins/sulis/skills/check-tests/scripts/regression.py:127` — `?` [concern]
- `plugins/sulis/skills/check-tests/scripts/regression.py:250` — `?` [concern]
- `plugins/sulis/skills/check-tests/scripts/regression.py:529` — `?` [concern]
- `plugins/sulis/skills/check-tests/scripts/regression.py:612` — `?` [high]
- `plugins/sulis/skills/check-tests/scripts/regression.py:728` — `?` [high]
- `plugins/sulis/skills/code-health/scripts/aggregator.py:114` — `?` [concern]
- `plugins/sulis/skills/code-health/scripts/aggregator.py:192` — `?` [high]
- `plugins/sulis/skills/code-health/scripts/aggregator.py:77` — `?` [concern]
- `plugins/sulis/skills/code-health/scripts/orchestrator.py:313` — `?` [concern]
- `plugins/sulis/skills/code-health/scripts/orchestrator.py:472` — `?` [concern]
- `plugins/sulis/skills/consolidate-into-sulis/scripts/compare_baseline.py:64` — `?` [concern]
- `plugins/sulis/skills/consolidate-into-sulis/scripts/detect_collisions.py:114` — `?` [concern]
- `plugins/sulis/skills/consolidate-into-sulis/scripts/find_external_refs.py:29` — `?` [high]
- `plugins/sulis/skills/consolidate-into-sulis/scripts/find_external_refs.py:45` — `?` [high]
- `plugins/sulis/skills/consolidate-into-sulis/scripts/inventory.py:22` — `?` [concern]

## PRE-EXISTING findings (carried over)

5 pre-existing finding(s) carried over from baseline.
These are unrelated to the consolidation; not gating.

