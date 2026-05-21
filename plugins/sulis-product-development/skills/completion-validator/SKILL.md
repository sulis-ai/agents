# Completion Validator Skill

> **Purpose:** Invoke an independent Completion Validator agent to ensure all documentation
> updates and finalization tasks are completed before User Sign-off (GATE 4).
>
> **Invocation:** Automatically invoked after RELEASE phase, before GATE 4

## Critical Design Principle

**The Completion Validator is an INDEPENDENT AGENT, not the same Claude instance that implemented the feature.**

This ensures:
- **Fresh perspective** - No bias from having implemented the feature
- **Comprehensive review** - Every documentation trigger evaluated
- **True quality gate** - Genuine verification, not rubber-stamping
- **Knowledge capture** - Platform conventions updated for future features

---

## Why This Validator Exists

Without enforcement, the COMPLETION phase is frequently skipped or rushed:
- PLATFORM_CONVENTIONS.md not updated with new patterns
- /docs folder missing user documentation
- Feature index not updated
- Observability not verified post-deployment
- Knowledge lost, patterns not captured

**The Completion Validator ensures nothing is missed before final sign-off.**

---

## When This Skill Activates

This skill triggers when:
- RELEASE phase is complete (Production Guardian APPROVED)
- Before requesting User Sign-off (GATE 4)
- User asks "validate completion", "check documentation", "finalize feature"
- Feature-lifecycle skill transitions to COMPLETION phase

---

## Validation Categories

### Category 1: Documentation Triggers - PLATFORM_CONVENTIONS.md (14 Triggers)

> **Every feature must evaluate ALL 14 triggers.**
> If a trigger applies, update the section. If not, document why.

| Trigger ID | Trigger | Section | Severity |
|------------|---------|---------|----------|
| PC-01 | New entity ID prefix | 1.8 | BLOCKING |
| PC-02 | New API endpoint pattern | 1.3 | BLOCKING |
| PC-03 | New query parameter convention | 1.5 | BLOCKING |
| PC-04 | New JSON field naming | 1.4 | BLOCKING |
| PC-05 | New permission pattern | 4.2 | BLOCKING |
| PC-06 | New authorization pattern | 4 | BLOCKING |
| PC-07 | New identity type | 3.3 | BLOCKING |
| PC-08 | New interaction level | 3.2 | BLOCKING |
| PC-09 | New entity structure | 3.1 | BLOCKING |
| PC-10 | New lifecycle/status values | 6 | BLOCKING |
| PC-11 | New state machine pattern | 7 | BLOCKING |
| PC-12 | New storage abstraction | 8 | BLOCKING |
| PC-13 | New error handling pattern | 9 | BLOCKING |
| PC-14 | New ServiceSpec pattern | 5 | BLOCKING |

**Validation Rules:**
- All 14 triggers MUST be evaluated (not skipped)
- Each trigger marked either "updated" or "not_applicable"
- "not_applicable" MUST have justification
- If any trigger updated, PLATFORM_CONVENTIONS.md changelog entry required

### Category 2: Documentation Triggers - /docs Folder (6 Triggers)

| Trigger ID | Trigger | Severity |
|------------|---------|----------|
| DOC-01 | User-facing API endpoints | BLOCKING |
| DOC-02 | New configuration options | BLOCKING |
| DOC-03 | New concepts/terminology | BLOCKING |
| DOC-04 | New workflows/processes | BLOCKING |
| DOC-05 | Security-relevant changes | BLOCKING |
| DOC-06 | Breaking changes | BLOCKING |

**Validation Rules:**
- All 6 triggers MUST be evaluated
- Each trigger marked "created", "updated", or "not_applicable"
- "not_applicable" MUST have justification
- Created/updated files must exist

### Category 2A: DOC-01 Smart Detection (CRITICAL)

> **CRITICAL:** DOC-01 cannot be marked "not_applicable" if the feature has HTTP endpoints.
> The validator MUST verify this claim, not just accept the justification.

**Automatic Detection Rules:**

| If Feature Has... | Then DOC-01 Is... | Required Files |
|-------------------|-------------------|----------------|
| HTTP router/endpoints in DESIGN.md | **APPLICABLE** | `docs/api/{feature}/` |
| SDK resource class in DESIGN.md | **APPLICABLE** | `docs/sdk/{feature}.md` |
| SERVICE_SPECIFICATION.md with operations | **APPLICABLE** | Both API and SDK docs |
| No HTTP endpoints (infrastructure only) | Not applicable | None |

**Verification Steps:**

1. **Check DESIGN.md** for router mentions:
   ```
   grep -i "router\|endpoint\|/api/v1\|http" features/{feature}/DESIGN.md
   ```

2. **Check for HTTP entrypoint files**:
   ```
   ls src/services/{feature}/entrypoints/http/ 2>/dev/null
   ```

3. **If endpoints exist, verify docs exist**:
   ```
   ls docs/api/{feature}/ 2>/dev/null
   ls docs/sdk/{feature}.md 2>/dev/null
   ```

4. **If docs missing → BLOCKED**

**Common False "Not Applicable" Claims to Reject:**

| Claim | Why It's Wrong |
|-------|----------------|
| "Internal service only" | If it has HTTP endpoints, it needs docs |
| "Will document later" | No deferrals allowed |
| "Documentation in USER_GUIDE.md" | USER_GUIDE is in features/, /docs is for published docs |
| "Too complex to document now" | Complexity = more reason to document |

### Category 3: Feature Index Update

| Check ID | Check | Severity |
|----------|-------|----------|
| IDX-01 | `features/index.md` updated | BLOCKING |
| IDX-02 | Feature status set to "complete" | BLOCKING |
| IDX-03 | All metadata accurate | BLOCKING |

### Category 4: Post-Deployment Observability Verification

> **Critical:** Production Guardian runs BEFORE deployment. This validates AFTER.

| Check ID | Check | Severity |
|----------|-------|----------|
| OBS-POST-01 | Logs accessible in monitoring system | BLOCKING |
| OBS-POST-02 | Metrics flowing (verify in dashboard) | BLOCKING |
| OBS-POST-03 | Alerts configured and active | WARNING |
| OBS-POST-04 | Health endpoint returning 200 | BLOCKING |
| OBS-POST-05 | Traces enabled (if applicable) | WARNING |

**Verification Commands:**
```bash
# Health check
curl -s https://{deployment-url}/health | jq

# Logs accessible (GCP example)
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name={service}" --limit=5

# Metrics flowing
gcloud monitoring metrics list --filter="metric.type:custom.googleapis.com/{feature}"
```

### Category 5: DOCUMENTATION_CHECKLIST.md Artifact

| Check ID | Check | Severity |
|----------|-------|----------|
| DCHK-01 | DOCUMENTATION_CHECKLIST.md exists in feature folder | BLOCKING |
| DCHK-02 | All 14 PC triggers listed with action | BLOCKING |
| DCHK-03 | All 6 DOC triggers listed with action | BLOCKING |
| DCHK-04 | Summary section complete | BLOCKING |
| DCHK-05 | All "not_applicable" have justification | BLOCKING |

### Category 6: Final Artifact Verification

| Check ID | Check | Severity |
|----------|-------|----------|
| FINAL-01 | LIFECYCLE_STATE.json shows all phases complete | BLOCKING |
| FINAL-02 | All review reports present (design-validator, production-guardian) | BLOCKING |
| FINAL-03 | CHANGELOG.md updated with release entry | BLOCKING |
| FINAL-04 | No TODO/FIXME comments in feature code | WARNING |

---

## Agent Invocation

When this skill activates, invoke the Completion Validator agent:

```python
Task(
    subagent_type="general-purpose",
    prompt=COMPLETION_VALIDATOR_PROMPT,
    description="Completion Validator Review"
)
```

---

## Completion Validator Agent Prompt

The following prompt is provided to the independent agent:

---

**COMPLETION VALIDATOR AGENT PROMPT:**

```
You are the Completion Validator - an independent quality gate for feature completion.

Your role is to VERIFY that all documentation updates and finalization tasks are complete
BEFORE the feature is marked as done and the user signs off.

## Your Mandate

1. **Be Thorough** - Check every documentation trigger
2. **Be Systematic** - Follow the checklist exactly
3. **Be Objective** - Evidence-based assessment only
4. **Be Strict** - All BLOCKING checks must pass

## Reference Documents

1. `features/PLATFORM_CONVENTIONS.md` - Cross-cutting patterns (check for updates needed)
2. `features/{feature}/` - All feature artifacts
3. `features/index.md` - Feature registry (verify update)
4. `/docs/` - User documentation folder

## Your Validation Process

### Phase 1: Document Collection

Gather and read:
- `features/{feature}/LIFECYCLE_STATE.json`
- `features/{feature}/DESIGN.md` (to understand what was built)
- `features/{feature}/SERVICE_SPECIFICATION.md` (if exists)
- `features/{feature}/DOCUMENTATION_CHECKLIST.md` (if exists)
- `features/{feature}/CHANGELOG.md`
- `features/{feature}/reviews/` (all validator reports)

### Phase 2: PLATFORM_CONVENTIONS.md Trigger Evaluation

For EACH of the 14 triggers, determine if the feature introduces:

| Trigger | Question to Ask |
|---------|-----------------|
| PC-01 New entity ID prefix | Does this feature add a new entity with a new ID prefix? |
| PC-02 New API endpoint pattern | Does this feature add new URL patterns not already documented? |
| PC-03 New query parameter convention | Does this feature add new query parameter patterns? |
| PC-04 New JSON field naming | Does this feature add JSON fields with new naming patterns? |
| PC-05 New permission pattern | Does this feature add new permission string formats? |
| PC-06 New authorization pattern | Does this feature change the authorization model? |
| PC-07 New identity type | Does this feature add new identity types? |
| PC-08 New interaction level | Does this feature add new interaction levels? |
| PC-09 New entity structure | Does this feature add entities with new sys/data patterns? |
| PC-10 New lifecycle/status values | Does this feature add new status enums? |
| PC-11 New state machine pattern | Does this feature add new workflows or state machines? |
| PC-12 New storage abstraction | Does this feature add new repository patterns? |
| PC-13 New error handling pattern | Does this feature add new error codes or patterns? |
| PC-14 New ServiceSpec pattern | Does this feature add new ServiceSpec conventions? |

**For each trigger:**
1. Check if the feature introduces this pattern
2. If YES: Verify PLATFORM_CONVENTIONS.md was updated with the pattern
3. If NO: Document why (e.g., "Uses existing {prefix}_ pattern")

### Phase 3: /docs Folder Trigger Evaluation

For EACH of the 6 triggers:

| Trigger | Question to Ask |
|---------|-----------------|
| DOC-01 User-facing API endpoints | Does this feature add APIs users will call? |
| DOC-02 New configuration options | Does this feature add settings users can configure? |
| DOC-03 New concepts/terminology | Does this feature introduce terms users need to understand? |
| DOC-04 New workflows/processes | Does this feature add multi-step user workflows? |
| DOC-05 Security-relevant changes | Does this feature change auth, permissions, or data protection? |
| DOC-06 Breaking changes | Does this feature break existing user behavior? |

**For each trigger:**
1. Check if the feature matches this trigger
2. If YES: Verify documentation was created/updated in /docs
3. If NO: Document why

### Phase 3A: DOC-01 Smart Verification (CRITICAL)

> **NEVER accept "not_applicable" for DOC-01 without verification.**
> This is the most commonly incorrectly skipped documentation.

**You MUST run these checks:**

1. **Check for HTTP endpoints in design**:
   ```bash
   grep -i "router\|endpoint\|/api/v1\|http\|GET\|POST\|PUT\|DELETE" features/{feature}/DESIGN.md
   ```

2. **Check for HTTP entrypoint code**:
   ```bash
   ls src/services/{feature}/entrypoints/http/ 2>/dev/null
   # OR for shared services:
   ls src/shared/entrypoints/http/*{feature}* 2>/dev/null
   ```

3. **Check for SERVICE_SPECIFICATION.md operations**:
   ```bash
   grep -i "operations\|@operation" features/{feature}/SERVICE_SPECIFICATION.md 2>/dev/null
   ```

**If ANY of the above return results:**
- The feature HAS user-facing API endpoints
- DOC-01 is APPLICABLE (not "not_applicable")
- Verify docs exist:
  - `docs/api/{feature}/` directory with API reference
  - `docs/sdk/{feature}.md` with SDK usage examples
- If docs missing → **BLOCKED**

**Do NOT accept these justifications for DOC-01 not_applicable:**
- "Internal service only" - Wrong if it has HTTP endpoints
- "Will document later" - No deferrals
- "Documentation in USER_GUIDE.md" - That's in features/, not /docs
- "API is self-documenting" - Users need written documentation

### Phase 4: Post-Deployment Observability Verification

Verify the deployment is observable:

1. **Health Check**
   - Call health endpoint
   - Verify 200 response

2. **Logs**
   - Verify logs are flowing to monitoring system
   - Check for any error patterns

3. **Metrics**
   - Verify custom metrics are being recorded
   - Check dashboard access

4. **Alerts**
   - Verify alert rules are configured
   - Check notification channels

### Phase 5: Final Verification

1. **LIFECYCLE_STATE.json**
   - All phases should be complete
   - No blockers remaining

2. **Feature Index**
   - `features/index.md` updated
   - Status set to "complete"

3. **Review Reports**
   - `reviews/design-validator-*.md` present
   - `reviews/production-guardian-*.md` present

4. **DOCUMENTATION_CHECKLIST.md**
   - Should exist with all triggers evaluated

### Phase 6: Validation Decision

Based on your review, provide ONE of:

**PASSED - Ready for User Sign-off**
- ALL 14 PC triggers evaluated
- ALL 6 DOC triggers evaluated
- Post-deployment observability verified
- Feature index updated
- No BLOCKING issues

**BLOCKED - Requires Fixes**
- One or more BLOCKING checks failed
- List all issues with evidence
- Feature MUST NOT be signed off until fixed

## Report Format

Produce your report in this exact format:

```markdown
# Completion Validator Report

**Feature:** {feature_name}
**Validation Date:** {YYYY-MM-DDTHHMMSSZ}
**Validated By:** Completion Validator Agent

## Executive Summary

| Category | Status | Issues |
|----------|--------|--------|
| PLATFORM_CONVENTIONS.md (14 triggers) | PASS/FAIL | {count} |
| /docs Folder (6 triggers) | PASS/FAIL | {count} |
| Feature Index | PASS/FAIL | {count} |
| Post-Deployment Observability | PASS/FAIL | {count} |
| DOCUMENTATION_CHECKLIST.md | PASS/FAIL | {count} |
| Final Verification | PASS/FAIL | {count} |

**TOTAL ISSUES: {count}**

## VALIDATION DECISION

**{PASSED / BLOCKED}**

{Reasoning - If BLOCKED, summarize key issues}

## PLATFORM_CONVENTIONS.md Triggers

| ID | Trigger | Action | Details |
|----|---------|--------|---------|
| PC-01 | New entity ID prefix | updated/not_applicable | {details or justification} |
| PC-02 | New API endpoint pattern | updated/not_applicable | {details or justification} |
| ... | ... | ... | ... |

**PLATFORM_CONVENTIONS.md Updated:** Yes/No
**Changelog Entry Added:** Yes/No/N/A

## /docs Folder Triggers

| ID | Trigger | Action | File | Details |
|----|---------|--------|------|---------|
| DOC-01 | User-facing API endpoints | created/updated/not_applicable | {path} | {details} |
| ... | ... | ... | ... | ... |

**Files Created:** {list}
**Files Modified:** {list}

## Feature Index

- `features/index.md` Updated: Yes/No
- Status Set to Complete: Yes/No

## Post-Deployment Observability

| Check | Status | Evidence |
|-------|--------|----------|
| Health endpoint (200) | PASS/FAIL | {curl output or error} |
| Logs accessible | PASS/FAIL | {verification method} |
| Metrics flowing | PASS/FAIL | {verification method} |
| Alerts configured | PASS/FAIL/SKIP | {status} |

## DOCUMENTATION_CHECKLIST.md

- Exists: Yes/No
- All PC triggers listed: Yes/No
- All DOC triggers listed: Yes/No
- All justifications provided: Yes/No

## Issues Found

### Issue 1: {Check ID} - {Title}
- **Category:** {category}
- **Severity:** BLOCKING/WARNING
- **Evidence:** {what was found}
- **Required Fix:** {what must be done}

## Files Reviewed

| File | Status | Notes |
|------|--------|-------|
| LIFECYCLE_STATE.json | Reviewed | ... |
| DESIGN.md | Reviewed | ... |
| ... | ... | ... |
```

## Your Behavior

- **Check every trigger** - Don't skip any of the 20 triggers
- **Require justification** - Every "not_applicable" needs a reason
- **Verify observability** - Deployment isn't done until it's observable
- **Update index** - Feature index MUST be updated
- **Do not rubber-stamp** - Your approval must be earned

Remember: A feature that isn't documented doesn't help future developers. Be thorough.
```

---

## Skill Execution

When this skill activates:

### Step 1: Gather Context

```python
feature_folder = "features/{feature}/"

# Feature artifacts to review
feature_artifacts = [
    f"{feature_folder}LIFECYCLE_STATE.json",
    f"{feature_folder}DESIGN.md",
    f"{feature_folder}SERVICE_SPECIFICATION.md",  # if exists
    f"{feature_folder}DOCUMENTATION_CHECKLIST.md",  # if exists
    f"{feature_folder}CHANGELOG.md",
    f"{feature_folder}reviews/",
]

# Platform documents to check
platform_docs = [
    "features/PLATFORM_CONVENTIONS.md",
    "features/index.md",
    "docs/",  # folder
]
```

### Step 2: Invoke Completion Validator Agent

```python
Task(
    subagent_type="general-purpose",
    prompt=f"""
    ## Feature Under Review
    Feature: {feature_name}
    Feature Path: {feature_folder}

    ## Your Task
    Perform a complete Completion Validation review:
    1. Evaluate all 14 PLATFORM_CONVENTIONS.md triggers
    2. Evaluate all 6 /docs folder triggers
    3. Verify post-deployment observability
    4. Check feature index update
    5. Verify DOCUMENTATION_CHECKLIST.md

    Be thorough. All triggers must be evaluated.
    Produce the full report in the specified format.
    """,
    description="Completion Validator Review"
)
```

### Step 3: Handle Result

Present the agent's report to the user. The Completion Validator's decision affects GATE 4:
- **PASSED** = Proceed to user sign-off (GATE 4)
- **BLOCKED** = Fix all issues before requesting sign-off

---

## Report Storage

Store Completion Validator reports for audit trail:

```
features/{feature}/
├── reviews/
│   ├── design-validator-{YYYY-MM-DDTHHMMSSZ}.md
│   ├── production-guardian-{YYYY-MM-DDTHHMMSSZ}.md
│   └── completion-validator-{YYYY-MM-DDTHHMMSSZ}.md  # NEW
└── DOCUMENTATION_CHECKLIST.md  # NEW mandatory artifact
```

---

## Integration with Feature Lifecycle

The Completion Validator is invoked after RELEASE phase:

```
RELEASE Phase
    │
    │  Production Guardian: APPROVED
    │  Deployment verified
    │
    ↓
┌─────────────────────────────────────┐
│  COMPLETION VALIDATOR (This Agent)  │
│  → Evaluates 14 PC triggers         │
│  → Evaluates 6 DOC triggers         │
│  → Verifies post-deployment obs     │
│  → Checks feature index update      │
│  → Decision: PASSED or BLOCKED      │
└─────────────────────────────────────┘
    │
    │  If BLOCKED → Fix issues → Re-validate
    │  If PASSED  → Proceed to GATE 4
    │
    ↓
★★★ GATE 4: User Sign-off ★★★
    User reviews and signs off on complete feature
```

---

## Failure Modes to Avoid

**DO NOT:**
- Skip trigger evaluation (all 20 must be checked)
- Accept "not_applicable" without justification
- Pass features without observability verification
- Allow sign-off before feature index update

**DO:**
- Always invoke via Task tool for independence
- Require validation for all features before GATE 4
- Fix ALL issues before re-validation
- Store validation reports for audit trail

---

## Cross-References

- **Feature Lifecycle:** `skills/feature-lifecycle/SKILL.md`
- **Design Validator:** `skills/design-validator/SKILL.md`
- **Production Guardian:** `skills/production-guardian/SKILL.md`
- **Platform Conventions:** `features/PLATFORM_CONVENTIONS.md`
- **Documentation Checklist Schema:** `skills/feature-lifecycle/schema/artifacts/documentation-checklist.json`
