---
id: WP-009
title: Extend drift detector — HTML-comment annotation parser + --cross-tenant-refs-allowed-for flag
status: pending
kind: backend
primitive: extend
group: EXPAND
change_id: CH-01KT1W
sequence_id: WP-009
dependsOn: [WP-001]
blocks: [WP-008]
estimated_token_cost:
  input: 4k
  output: 3k
tdd_section: Armor §Cross-tenant drift semantics; ADR-001 (Path A annotation format); ADR-002 (cross-tenant boundary)
adrs: [ADR-001, ADR-002]
---

## Context

Two surgical extensions to the existing drift detector (commit
`7d666df extend: tighten-drift-gate`) — both are minimal additions to
existing extension points, no rewrites.

**Extension 1 — HTML-comment annotation parsing.** Today the detector
parses `# canonical:step:<name>` (YAML comments) from
`release-on-merge.yml`. discover-project's imperative is `SKILL.md`
(Markdown). Per ADR-001, the annotation format becomes
`<!-- canonical:step:<name> -->`. The detector needs a small
multi-format annotation parser — same matching logic, different
comment syntax.

**Extension 2 — `--cross-tenant-refs-allowed-for` CLI flag.** Per
ADR-002, a consumer Project carries `belongs_to_tenant: <consumer>`
while `release_workflow_ref: <marketplace>` — a recognised cross-tenant
boundary, not drift. The detector needs a flag that lists ref-types
treated as allowed cross-tenant.

Both extensions are **EXPAND-Extend** (the detector has obvious
extension points: the annotation-parser dispatch and the CLI
argparse). Per `references/change-primitives.md` priority order:
Reuse (entire detector) + Extend (parser + flag); no Wrap, no Replace,
no Strangle. The standing detector's invariants are unchanged.

## Contract

### Files modified

```
plugins/sulis/scripts/check-canonical-drift.py     # the detector entry point
plugins/sulis/scripts/_drift/                      # the package (if it exists; or files added inline)
└── annotation_parser.py                           # multi-format parser (extension 1)
plugins/sulis/scripts/tests/unit/
└── test_check_canonical_drift_discover.py        # the n=2 parity test (NEW)
```

3-4 files modified + 1 file added. Exact files depend on the
detector's current internal layout — the surgical principle is "no
rewrites; touch only the parser dispatch + the argparse + add the
test".

### Extension 1 — annotation parser

Today's parser (YAML comments):

```python
# Hypothesis: today's detector contains something like:
def parse_annotations_yaml(content: str) -> list[str]:
    return re.findall(r"^\s*#\s*canonical:step:([a-z][a-z0-9-]+)", content, re.MULTILINE)
```

The extension adds a sibling parser:

```python
def parse_annotations_markdown(content: str) -> list[str]:
    return re.findall(r"<!--\s*canonical:step:([a-z][a-z0-9-]+)\s*-->", content)


def parse_annotations(path: Path, content: str) -> list[str]:
    """Dispatch on file extension. Multi-format annotation parser."""
    if path.suffix in (".yml", ".yaml"):
        return parse_annotations_yaml(content)
    if path.suffix in (".md",):
        return parse_annotations_markdown(content)
    # Unknown extensions yield no annotations (silent — drift detector
    # treats them as nothing to check, not as a violation).
    return []
```

The downstream `compare_canonical_to_imperative(...)` logic that
matches annotation set vs canonical Step set is **unchanged** — only
the input parser is extended.

### Extension 2 — `--cross-tenant-refs-allowed-for` flag

```python
# In the detector's argparse setup:
parser.add_argument(
    "--cross-tenant-refs-allowed-for",
    type=lambda s: s.split(","),
    default=[],
    help="Comma-separated list of ref field names that may cross tenant boundaries "
         "without being treated as drift (e.g., 'release_workflow_ref,belongs_to_product_ref')."
)
```

The downstream cross-reference resolver gains a check:

```python
def check_tenant_consistency(entity, refs, allowed_cross_tenant_fields):
    for field_name, target_id in refs.items():
        target = resolve(target_id)
        if target.tenant != entity.tenant:
            if field_name in allowed_cross_tenant_fields:
                continue  # documented cross-tenant boundary; not drift
            yield DriftViolation(...)
```

Default flag value is `[]` — backward-compatible. Existing
release-train invocations of the detector see no behavioural change.

### New test file — `test_check_canonical_drift_discover.py`

Parity with the existing release-train test file. Three fixtures:

```
plugins/sulis/scripts/tests/fixtures/drift-discover/
├── pass/
│   ├── SKILL.md                 # fully annotated; all 9 canonical steps covered
│   ├── workflow.jsonld          # canonical with 9 Steps
│   └── steps.jsonld
├── drift_missing_step/
│   ├── SKILL.md                 # missing 1 annotation
│   └── steps.jsonld             # canonical with 9 Steps
└── drift_extra_annotation/
    ├── SKILL.md                 # has an extra annotation for a Step not in canonical
    └── steps.jsonld
```

## Definition of Done

### Red — Failing tests written

**Characterisation tests (existing detector behaviour preserved):**

- [ ] `test_check_canonical_drift.py::test_release_train_still_passes` — re-run the existing release-train conformance test against `release-on-merge.yml` after the extension lands; assert exit 0 (the existing YAML parser still works)
- [ ] `test_check_canonical_drift.py::test_default_cross_tenant_flag_empty_list_no_behaviour_change` — invoke detector against release-train fixtures without the flag; assert behaviour identical to pre-extension

**Annotation parser extension (extension 1):**

- [ ] `test_check_canonical_drift_discover.py::test_parses_html_comment_annotations` — given markdown content with `<!-- canonical:step:read-repo-root -->`, parser returns `['read-repo-root']`
- [ ] `test_check_canonical_drift_discover.py::test_parses_html_comment_with_extra_whitespace` — `<!--  canonical:step:foo  -->` parses to `['foo']`
- [ ] `test_check_canonical_drift_discover.py::test_yaml_parser_does_not_match_html_comments` — `parse_annotations_yaml` on markdown content returns `[]` (no false-positive cross-format)
- [ ] `test_check_canonical_drift_discover.py::test_markdown_parser_does_not_match_yaml_comments` — converse
- [ ] `test_check_canonical_drift_discover.py::test_dispatch_chooses_parser_by_extension` — `.md` → markdown parser; `.yml` → yaml parser; `.py` → empty list (no annotations expected)

**Cross-tenant flag extension (extension 2):**

- [ ] `test_check_canonical_drift_discover.py::test_cross_tenant_ref_without_flag_is_drift` — fixture entity with `belongs_to_tenant: <consumer>` + `release_workflow_ref: <marketplace>`; detector run WITHOUT the flag → exit non-zero (treats cross-tenant as drift)
- [ ] `test_check_canonical_drift_discover.py::test_cross_tenant_ref_with_flag_passes` — same fixture, detector run WITH `--cross-tenant-refs-allowed-for release_workflow_ref` → exit 0
- [ ] `test_check_canonical_drift_discover.py::test_cross_tenant_flag_accepts_multiple_fields` — `--cross-tenant-refs-allowed-for release_workflow_ref,belongs_to_product_ref` parses to a 2-element list

**Conformance fixtures (the n=2 parity tests):**

- [ ] `test_check_canonical_drift_discover.py::test_pass_fixture` — `fixtures/drift-discover/pass/` → exit 0
- [ ] `test_check_canonical_drift_discover.py::test_drift_missing_step` — `fixtures/drift-discover/drift_missing_step/` → exit 1; stderr names the missing Step
- [ ] `test_check_canonical_drift_discover.py::test_drift_extra_annotation` — `fixtures/drift-discover/drift_extra_annotation/` → exit 1; stderr names the unexpected annotation

### Green — Implementation makes tests pass

- [ ] Annotation parser dispatcher added (Markdown + YAML; future extension via file-extension dispatch)
- [ ] `--cross-tenant-refs-allowed-for` flag added to argparse with default `[]`
- [ ] Cross-reference resolver checks the flag before raising a tenant-mismatch DriftViolation
- [ ] All 14 Red tests pass (including the 2 characterisation tests for backward compatibility)
- [ ] No changes to public CLI behaviour OUTSIDE the new flag (release-train CI unchanged)

### Blue — Refactor complete

- [ ] Parser dispatcher is a small dict (`{'.md': parse_annotations_markdown, '.yml': parse_annotations_yaml, '.yaml': parse_annotations_yaml}`) — extension to a 3rd format (e.g., `.py` docstrings) is one line
- [ ] Cross-tenant check is a single helper invoked from the resolver — not duplicated across ref types
- [ ] CLI help text for the new flag is plain English (no internal IDs)
- [ ] Characterisation test file lives next to the new test (so both run in the same suite)

## Sequence

- **dependsOn:** WP-001 (the canonical entities + steps.jsonld are read by the parity fixtures — the `pass/` fixture's `steps.jsonld` is the same shape as WP-001's authored version)
- **blocks:** WP-008 (skill conformance test in WP-008's Red phase invokes the extended detector)
- **Parallelisable with:** WP-002, WP-003, WP-004, WP-005, WP-006, WP-007 (no shared files)

## Characterisation Test

Per the REORGANISE-discipline (`references/change-primitives.md`) —
this WP is **EXPAND-Extend**, not REORGANISE, so a formal
characterisation test isn't *required*. But because we're modifying an
existing detector, the two tests
`test_release_train_still_passes` and
`test_default_cross_tenant_flag_empty_list_no_behaviour_change`
function AS characterisation tests for the existing behaviour. They go
in Red first, run against the pre-extension detector to confirm
baseline (both pass before any code change), then re-run against the
post-extension detector (both still pass) — proving the extension is
non-breaking.

Characterisation test path: `plugins/sulis/scripts/tests/unit/test_check_canonical_drift.py`

## Estimated Token Cost

- **Input:** ~4k (existing drift detector source + WP-001's annotated SKILL.md draft + ADR-001/002 + foundation Project schema for the cross-tenant ref check)
- **Output:** ~3k (parser dispatcher ≈ 30 LOC + cross-tenant flag ≈ 20 LOC + new test file ≈ 200 LOC + 3 fixture dirs)
- **Total:** ~7k

## Notes

- This WP is `extend` (EXPAND group) because the existing detector has obvious extension points: the parser dispatch and the CLI. No Wrap, no Replace. The standing detector's invariants are unchanged.
- The characterisation tests are the safety net for backward compatibility — release-train CI MUST keep passing. If either pre-extension test fails post-extension, the WP is rejected at Red→Green.
- The annotation parser dispatcher is keyed by file extension so adding a 3rd format later (e.g., `.py` docstring annotations for a future Python-only Workflow) is one-line addition.
- The cross-tenant flag is a list with a comma-separated CLI value (no quoting issues; well-supported by argparse `type` callable). Default empty list preserves the existing detector's stricter-by-default behaviour for any invocation that doesn't opt in.
