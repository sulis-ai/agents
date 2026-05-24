# Agent prompt — check-build (tier 1 Exists)

You are an independent runner for tier 1 (Exists) of code-health.
Read `_shared-contract.md` for the output contract every tier agent
must follow.

## Your scope

Tier 1 — Exists — covers:
- Build artifact production (multi-system: pip / npm / go / cargo / docker / make)
- Manifest hygiene (plugin.json / marketplace.json / package.json)
- INF-01 container security (hadolint + Trivy on base image)
- INF-02 deploy-config secrets (Gitleaks scope expanded to yaml/k8s/CI)
- Tests are runnable (actual test-pass is tier 3)

## Run the scanner

```bash
cd {repo_root}
python3 plugins/sulis/skills/check-build/scripts/builder.py \
  --repo-root {repo_root} \
  --project {project} \
  --raw
```

The scanner emits JSON to stdout including:
- `hygiene_findings[]` — manifest issues
- `findings[]` — full findings array (includes hadolint + gitleaks deploy-config)
- `primitive_status` — INF-01 / INF-02 status
- `errors[]` — tool invocation errors

## Apply interpretation lenses

Per `_shared-contract.md`:
- If there are NO Dockerfiles anywhere in the repo, mark INF-01 NOT_APPLICABLE
- Manifest description-length warnings (MM-104) are ADVISORY; cap to ≤ 5 in
  findings output
- If `errors[]` contains "tool not available" entries, note the tool unavailability
  in primitive_status and don't downgrade verdict for missing-tool reasons

## Verdict assignment

- PASS — 0 critical / high findings
- NEEDS_ATTENTION — 1+ concern / advisory finding
- FAILED — 1+ critical / high finding
- NOT_YET_CHECKED — scanner failed to run

## Return per the shared contract format
