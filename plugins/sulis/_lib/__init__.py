"""Shared helpers for sulis tier skills.

Modules:
- baseline: read/write tier-namespaced .checkup/{project}/baseline.json
- allowlist: load per-project + per-skill allowlists
- scope: auto-detect PR vs codebase scope from local git state

Extracted in sulis v0.9.0 from the per-skill implementations that
emerged organically in check-tests, check-build, check-security
(baseline + allowlist) and check-readability (scope). Each skill now
imports from here rather than reimplementing.
"""
