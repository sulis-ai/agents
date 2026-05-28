---
id: HD-003
slug: distinguish-freeplan-403-protection
title: Distinguish private-free-plan 403 from genuine missing protection in the arrival-check probe
status: proposed
severity: medium
pillar: armor
gap_type: secrets
source: srd:lesson-52
change: CH-01KSQB
primitive: Refactor
group: reorganise
characterisation_test: tests/unit/test_wpx_arrival_check.py::test_rc02_freeplan_403_is_not_a_hard_error
depends_on: []
blocks: [HD-004]
files:
  - plugins/sulis/scripts/wpx-arrival-check
  - plugins/sulis/scripts/tests/unit/test_wpx_arrival_check.py
---

## Gap

`_check_rc02_protections(repo, rep)` (`wpx-arrival-check:128`) probes
`repos/{repo}/branches/dev/protection` and treats **any** non-zero `rc` as a
hard RC-02 error:

```python
rc, out, _ = _gh(["api", f"repos/{repo}/branches/dev/protection"])
if rc != 0:
    rep.error("RC-02", "dev branch protected", "no protection", "protected")
```

Two problems:

1. **stderr is discarded** (`_`). `_gh` (`wpx-arrival-check:57`) returns the full
   `(rc, stdout, stderr)` 3-tuple. On a **private repo on the free GitHub plan**,
   the protection API returns **403** with body "Upgrade to GitHub Pro or make
   this repository public to enable this feature." (on stderr via `gh`). That
   body is the only signal that distinguishes "protection is *unavailable* on
   this plan" from "protection is *available but not configured*".
2. **The two cases collapse to one error.** A free-plan repo (where protection
   *cannot* be enabled — not a misconfiguration) gets the same hard RC-02 error
   as a protection-capable repo that simply hasn't turned it on. The
   unprotected-repo warning (HD-004) needs the free-plan case isolated as a
   *non-error, warning-eligible* condition.

## Why it matters

Lesson #52's refined root cause: the typical Sulis founder builds a **private
product on a free plan**, where branch protection is unavailable, so branch-ci
runs but cannot gate merges — red reaches `dev` via a manual merge. Until the
probe can tell that case apart from a genuine misconfiguration, the system
either (a) hard-errors on every founder's correctly-configured-but-unprotectable
repo, or (b) stays silent about the real gating gap. Neither is right. This delta
produces the distinction that HD-004's one-time warning consumes.

## Characterisation test (Red — REORGANISE requires it, CLAUDE.md #3)

This is a Refactor of an existing function with existing behaviour to preserve
(public/protected repos must keep the exact RC-02 error semantics — spec
constraint). So a characterisation test pins current behaviour first, then a new
test drives the new branch. Both live in
`plugins/sulis/scripts/tests/unit/test_wpx_arrival_check.py`, using the existing
`mock_gh` fixture (substring dispatch + `exit_code` + `stderr` are already
supported — conftest `:226–234`).

```python
def test_rc02_genuine_missing_protection_still_errors(tmp_path, run_tool, mock_gh):
    """CHARACTERISATION: a protection-capable repo with no protection
    configured (rc!=0, NO 'Upgrade to GitHub Pro' body) still hard-errors
    RC-02. Pins the behaviour the refactor must preserve."""
    _write_contract(tmp_path, "profile: published-artifact\ncontribution_model: solo\n")
    _write_workflows(tmp_path, ["branch-ci", "promote-dev-to-main",
                                "deploy-staging", "health-and-smoke", "release-prod"])
    (tmp_path / ".github" / "CODEOWNERS").write_text("* @iainn\n")
    responses = _gh_base(queue_present=False)
    responses[1] = {"match": "branches/dev/protection", "exit_code": 1,
                    "stderr": "gh: Not Found (HTTP 404)"}
    mock_gh(responses)

    result = _run(run_tool, tmp_path)

    rc02 = [e for e in result.json["errors"] if e["rule"] == "RC-02"]
    assert rc02, "genuine missing protection must still hard-error RC-02"

def test_rc02_freeplan_403_is_not_a_hard_error(tmp_path, run_tool, mock_gh):
    """NEW: a private free-plan 403 ('Upgrade to GitHub Pro…') must NOT be a
    hard RC-02 error — it is reported as a warning-eligible
    unprotected-free-plan condition (a warning, surfaced for HD-004)."""
    _write_contract(tmp_path, "profile: published-artifact\ncontribution_model: solo\n")
    _write_workflows(tmp_path, ["branch-ci", "promote-dev-to-main",
                                "deploy-staging", "health-and-smoke", "release-prod"])
    (tmp_path / ".github" / "CODEOWNERS").write_text("* @iainn\n")
    responses = _gh_base(queue_present=False)
    responses[1] = {"match": "branches/dev/protection", "exit_code": 1,
        "stderr": ("gh: Upgrade to GitHub Pro or make this repository public "
                   "to enable this feature. (HTTP 403)")}
    # main/protection probe also 403 on a free-plan repo:
    responses.insert(0, {"match": "branches/main/protection", "exit_code": 1,
        "stderr": ("gh: Upgrade to GitHub Pro or make this repository public "
                   "to enable this feature. (HTTP 403)")})
    mock_gh(responses)

    result = _run(run_tool, tmp_path)

    rc02_errors = [e for e in result.json["errors"] if e["rule"] == "RC-02"]
    rc02_warns = [w for w in result.json["warnings"] if w["rule"] == "RC-02"]
    assert rc02_errors == [], "free-plan 403 must NOT be a hard RC-02 error"
    assert rc02_warns, "free-plan 403 should surface as an RC-02 warning"
    assert any("free" in (w.get("check","")+w.get("actual","")).lower()
               or "protection unavailable" in (w.get("actual","")+w.get("check","")).lower()
               for w in rc02_warns), "warning must name the unavailable-on-plan case"
```

The first test should pass against current code (it characterises today's
behaviour); confirm it green BEFORE the refactor. The second fails (no
free-plan branch exists yet).

## Changes

**MODIFIED** — `wpx-arrival-check`, `_check_rc02_protections`: capture stderr and
branch on the free-plan 403 body. A tiny module-level predicate makes the
detection testable and named:

```python
_FREEPLAN_403_MARKER = "upgrade to github pro"

def _is_freeplan_protection_403(rc: int, stderr: str) -> bool:
    """True when the protection API was unavailable because the repo is
    private on the free plan (403 'Upgrade to GitHub Pro…'), as opposed to
    a genuine missing/misconfigured protection on a capable repo."""
    return rc != 0 and _FREEPLAN_403_MARKER in (stderr or "").lower()
```

```python
def _check_rc02_protections(repo, rep):
    rc, out, err = _gh(["api", f"repos/{repo}/branches/dev/protection"])
    if _is_freeplan_protection_403(rc, err):
        rep.warn("RC-02", "dev branch protection unavailable on plan",
                 "private repo on free plan (protection API 403)",
                 "branch-ci gates only Sulis-routed merges; manual merges are not gated")
    elif rc != 0:
        rep.error("RC-02", "dev branch protected", "no protection", "protected")
    else:
        # ... existing required-status-checks parsing UNCHANGED ...
    rc, _out, err = _gh(["api", f"repos/{repo}/branches/main/protection"])
    if _is_freeplan_protection_403(rc, err):
        pass  # one RC-02 free-plan warning is enough; don't double-warn on main
    elif rc != 0:
        rep.error("RC-02", "main branch protected", "no protection", "protected")
```

**Preserved (spec constraint):** public/protected repos hit neither free-plan
branch — the existing required-status-checks parsing and the genuine-missing
error path are byte-for-byte unchanged. The characterisation test guards this.

## Definition of Done

- **Red:** characterisation test passes against current code; the new free-plan
  test fails.
- **Green:** the predicate + branch are added; both tests pass; every existing
  `test_wpx_arrival_check.py` test still passes (public-repo semantics intact).
- **Blue:** the `_FREEPLAN_403_MARKER` constant and `_is_freeplan_protection_403`
  predicate are named and documented; the warning text is plain-English and
  carries the gating-gap explanation (so HD-004 can surface it verbatim or
  reference it). No change to RC-01/03/05/07/10.

## Boring-code notes

- Detection is a substring match against a documented marker constant — explicit,
  greppable, no regex cleverness. GitHub's free-plan 403 body is stable enough to
  match on; if GitHub changes the wording the test pins the expectation and the
  failure is loud.
- The free-plan condition is a **warning**, never silently swallowed: arrival-check
  already separates `errors` from `warnings` (`_Report`, `wpx-arrival-check:91`),
  so the distinction rides the existing report channel with no new surface.
