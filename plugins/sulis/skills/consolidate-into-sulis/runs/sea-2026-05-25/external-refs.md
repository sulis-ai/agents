# External references to `sea`

All file paths and agent dispatch points that mention `plugins/sea/` or the source plugin's agents.
Every line below needs updating during Commits 2–4 of the consolidation.

## 1. Files citing source-plugin paths

### `.architecture/sulis-checkup/TDD.md`

- L9: `> mostly net-new; partial coverage of `/sea:probe`, `/sea:codebase-audit`,`
- L10: `> `/sea:verify`, `/sulis-security:codebase-assess`, `/sea:code-review`.`
- L78: `each of which fires the right downstream skill (`/sea:harden`,`
- L79: ``/sea:suggest-split`, manual escalation).`
- L100: `| `plugins/sea/references/mece-3-architecture.md` | Form/Armor/Proof pillars; MEA-01..10. Tier-4 (Survives) and tier-6 (…`
- L101: `| `plugins/sea/references/boring-code.md` | The Green-stage standard. Any code that lands as part of `sulis-checkup` fol…`
- L102: `| `plugins/sea/references/change-primitives.md` (inferred from agent.md citations) | Cross-group decision priority; info…`
- L108: `at `.context/sulis-checkup/`. The agent ran `/sea:blueprint` in early-handoff /`
- L111: ``srd:requirements-analyst` is run before any `/sea:decompose` step.`
- L124: `| **1** | **Exists** — does it run? | Builds without error. Typecheck passes (mechanical baseline). Container image / de…`
- L125: `| **2** | **Safe** — could anyone be harmed? | Hardcoded secrets in source/history. SQL/command/SSRF injection. Broken a…`
- L126: `| **3** | **Works** — does it do what it should? | Tests pass. Functional spec met (if a spec exists). Smoke tests green…`
- L127: `| **4** | **Survives** — does it handle failure? | Every external call has timeout + retry + circuit breaker (MEA-04). S…`
- L128: `| **5** | **Understandable** — can a new person read this? | Names are descriptive (no `wpx/wp/lib` jargon-density probl…`
- L129: `| **6** | **Evolves cleanly** — can we change it without breaking it? | Test coverage is real (not just count — coverage…`
- L172: `| 1 | Per-change correctness | 3 (Works) | `/sea:code-review` already lives at the PR layer; checkup runs it on a branch…`
- L173: `| 2 | PR hygiene + sizing | 3 (Works) | Same — composes from `/sea:code-review` + `/sea:suggest-split` outputs. |`
- L174: `| 3 | Architecture primitive gaps | 4 (Survives) | `/sea:codebase-audit` is the tier-4 backbone. |`
- L175: `| 4 | Post-WP completeness | 6 (Evolves) | `/sea:verify` is tier-6 because it asks "is the architecture coherent enough …`
- L176: `| 5 | Cyclomatic complexity | 5 (Understandable) | Coverage overlap between `/sea:probe` and `sulis-security:CQ-01` reso…`
- L195: `| 24 | Manifest hygiene | 1 (Exists) — for parseability; 3 (Works) — for semantic correctness | **PARTIAL** — extend `/s…`
- L212: `| **Auto-fix** | `/sea:harden` | When the fix is well-bounded and the failing characterisation test can be constructed d…`
- L217: `| **Defer / accept-as-known** | `/sea:verify` OPEN_RISK pattern | When the risk is acknowledged but not fixed now. Recor…`
- L224: `| **2 — Safe** | **Auto-fix** for known-shape findings (secret in source → replace with vault lookup; missing CSP header…`
- L226: `| **4 — Survives** | **Auto-fix** via `/sea:harden` for HD-NNN deltas with `subject_ownership: external` (timeouts on HT…`
- L524: `- `/sulis:review` — collides with `/sea:code-review` mental model. Rejected.`
- L544: `**Two tiers per the `/sea:code-review` pattern.** Founder tier on top, technical`
- L629: `participant Audit as /sea:codebase-audit`
- L630: `participant Harden as /sea:harden`
- L671: `| 8 | Build/deploy-artefact verification | 1 | Tier-1 gap surfaced in Part 3 — "does the Dockerfile build?" not directly…`
- L672: `| 9 | Spec-less test-execution mode | 3 | Tier-3 only fully covered by `/sea:verify` which requires SRD+TDD+WPs. Need a …`
- L673: `| 10 | Observability/diagnosability per-PR check | 3-4 | Coverage matrix #17 — extend `/sea:code-review` quality lens wi…`
- L674: `| 11 | Manifest hygiene check | 1 | Coverage matrix #24 — `plugin.json`, `marketplace.json` semantic correctness beyond …`
- L684: `These need a founder/maintainer decision before `/sea:decompose` runs. Each`
- L689: ``/sea:harden` currently auto-fixes hardcoded-secret findings by replacing the`
- L717: `If the project has no SRD/TDD/WPs, `/sea:verify` doesn't apply. Tier 3 then reduces to "tests pass + smoke green". But a…`
- L766: `| Reserved-Vocabulary Sweep formal | DEFERRED — to be run when probe v0.9.1+ output exists for the marketplace and durin…`
- L777: `| Future SEA author running `/sea:decompose` after SRD lands | Parts 3, 7, 8 + all ADRs. |`

### `.architecture/sulis-checkup/adrs/ADR-002-tier-gating-semantics.md`

- L70: `Running `/sea:codebase-audit` against a non-compiling codebase`

### `.architecture/sulis-checkup/adrs/ADR-003-healing-prototype-taxonomy.md`

- L14: `1. **Auto-fix** (`/sea:harden`)`
- L19: `6. **Defer / accept-as-known** (`/sea:verify` OPEN_RISK)`
- L30: `auto-fix-heavy because `/sea:harden` is tier-4-shaped) but every tier can`
- L64: `- Loses the auto-fix wins at tier 4 (`/sea:harden`'s reason for existing).`
- L100: `| 4 | Auto-fix via `/sea:harden` (timeouts, OTel) | Auto-draft WP (per-call-site judgement) |`
- L107: `Each source primitive (e.g. `/sea:codebase-audit`) tags each finding with`
- L154: `| `auto_fix` | Target HD-NNN-{slug}.md drafted at `status: accepted` (skips proposed → accepted promotion). Runs `/sea:h…`
- L155: `| `draft_wp` | HD-NNN-{slug}.md drafted at `status: proposed`. Promotion to `accepted` is a founder action. Then `/sea:h…`

### `.architecture/sulis-checkup/adrs/ADR-005-two-tier-report-format.md`

- L21: ``## Technical detail` heading. The pattern `/sea:code-review` validated.`
- L25: `**Adopt the two-tiers-in-one-file pattern from `/sea:code-review`.** Founder`
- L27: `heading; downstream agents (`/sea:harden`, future `/code-review` re-runs)`
- L37: `- Engineers lose the precise taxonomy they need to act (e.g. `/sea:harden``
- L64: `**Rejected because:** the `/sea:code-review` decision document explicitly`
- L75: `- Calibrated pattern in `/sea:code-review`'s `SKILL.md` — already proven`
- L80: `Mitigated by the existing `/sea:code-review` pattern serving as the`
- L123: `## Translation table (mirrors /sea:code-review)`
- L153: `- Pattern reuses an already-validated convention from `/sea:code-review`.`
- L161: `The `/sea:code-review` SKILL.md is the canonical example to imitate.`

### `.architecture/sulis-checkup/adrs/ADR-006-srd-gap.md`

- L11: ``/sea:blueprint`'s standard gotcha is "No SRD, no TDD". The skill should`
- L35: ``/sea:decompose` step, using the TDD's Part 9 (gap list) and Part 10`
- L64: `3. An SRD is authored before any `/sea:decompose` step, using the TDD`
- L89: `5. **Then run `/sea:decompose`** against this TDD + the new SRD.`
- L119: `- Skill scope creep. `/sea:blueprint` is not `requirements-analyst`.`
- L121: `clarifications); doing it inside `/sea:blueprint` would have blocked`

### `.checkup/agents/baseline.json`

- L3: `"dead-class::plugins/sea/skills/probe/scripts/probe/models.py::413::SulisWorkloadExtras",`
- L4: `"dead-class::plugins/sea/skills/probe/scripts/probe/models.py::525::SynthesisPayload",`
- L5: `"dead-class::plugins/sea/skills/probe/scripts/probe/runners/base.py::54::ToolVersionError",`
- L6: `"dead-constant::plugins/sea/skills/probe/scripts/probe/config.py::567::HIGH_LINT_WARNINGS_PER_FILE",`
- L7: `"dead-constant::plugins/sea/skills/probe/scripts/probe/config.py::599::REPO_WIDE_PHASES",`
- L8: `"dead-constant::plugins/sea/skills/probe/scripts/probe/runners/deployment_runner.py::61::_METADATA_NAME_RE",`
- L9: `"dead-constant::plugins/sea/skills/probe/scripts/probe/runners/scc_runner.py::26::_SCC_LANGUAGE_MAP",`
- L10: `"dead-function::plugins/sea/skills/probe/scripts/probe/filesystem.py::184::find_first_manifest",`
- L11: `"dead-function::plugins/sea/skills/probe/scripts/probe/filesystem.py::200::files_for_language",`
- L12: `"dead-function::plugins/sea/skills/probe/scripts/probe/models.py::559::read_json",`
- L13: `"dead-function::plugins/sea/skills/probe/scripts/probe/render.py::1369::render_markdown_only",`
- L14: `"dead-import::plugins/sea/skills/probe/scripts/probe/orchestrator.py::17::Sequence"`
- L19: `"broad-except::plugins/sea/skills/probe/scripts/probe.py::179",`
- L20: `"broad-except::plugins/sea/skills/probe/scripts/probe/runners/architecture_runner.py::101",`
- L21: `"broad-except::plugins/sea/skills/probe/scripts/probe/runners/architecture_runner.py::136",`
- L22: `"broad-except::plugins/sea/skills/probe/scripts/probe/runners/deadcode_runner.py::72",`
- L23: `"broad-except::plugins/sea/skills/probe/scripts/probe/runners/deadcode_runner.py::82",`
- L24: `"broad-except::plugins/sea/skills/probe/scripts/probe/runners/deadcode_runner.py::91",`
- L25: `"broad-except::plugins/sea/skills/probe/scripts/probe/runners/deployment_runner.py::337",`
- L26: `"broad-except::plugins/sea/skills/probe/scripts/probe/runners/duplication_runner.py::55",`
- L27: `"broad-except::plugins/sea/skills/probe/scripts/probe/runners/lint_runner.py::112",`
- L28: `"broad-except::plugins/sea/skills/probe/scripts/probe/runners/test_runner.py::158",`
- L29: `"broad-except::plugins/sea/skills/probe/scripts/probe/runners/test_runner.py::211",`
- L30: `"broad-except::plugins/sea/skills/probe/scripts/probe/workspace.py::137",`
- L36: `"gitleaks::generic-api-key::plugins/sea/skills/probe/tests/unit/__pycache__/test_credential_runner.cpython-312-pytest-9.…`
- L37: `"gitleaks::generic-api-key::plugins/sea/skills/probe/tests/unit/test_credential_runner.py::180",`
- L38: `"gitleaks::generic-api-key::plugins/sea/skills/probe/tests/unit/test_credential_runner.py::46",`
- L39: `"gitleaks::generic-api-key::plugins/sea/skills/probe/tests/unit/test_credential_runner.py::59",`
- L43: `"semgrep::python.lang.security.use-defused-xml-parse.use-defused-xml-parse::plugins/sea/skills/probe/scripts/probe/works…`
- L44: `"semgrep::python.lang.security.use-defused-xml.use-defused-xml::plugins/sea/skills/probe/scripts/probe/workspace.py::40"`

### `.checkup/agents/check-maintainability-allowlist.md`

- L16: `dead-constant::plugins/sea/skills/probe/scripts/probe/config.py::567::HIGH_LINT_WARNINGS_PER_FILE: documented threshold;…`
- L17: `dead-constant::plugins/sea/skills/probe/scripts/probe/config.py::599::REPO_WIDE_PHASES: orchestrator config; reviewed vi…`
- L18: `dead-function::plugins/sea/skills/probe/scripts/probe/filesystem.py::184::find_first_manifest: public helper for probe l…`
- L19: `dead-function::plugins/sea/skills/probe/scripts/probe/filesystem.py::200::files_for_language: public helper`
- L20: `dead-class::plugins/sea/skills/probe/scripts/probe/models.py::413::SulisWorkloadExtras: pydantic-style dataclass; framew…`
- L21: `dead-class::plugins/sea/skills/probe/scripts/probe/models.py::525::SynthesisPayload: pydantic-style dataclass; framework…`
- L22: `dead-function::plugins/sea/skills/probe/scripts/probe/models.py::559::read_json: public helper`
- L23: `dead-import::plugins/sea/skills/probe/scripts/probe/orchestrator.py::17::Sequence: typing import; may be used in stub an…`
- L24: `dead-function::plugins/sea/skills/probe/scripts/probe/render.py::1369::render_markdown_only: public-API alternative rend…`
- L25: `dead-class::plugins/sea/skills/probe/scripts/probe/runners/base.py::54::ToolVersionError: exception class for external t…`
- L26: `dead-constant::plugins/sea/skills/probe/scripts/probe/runners/deployment_runner.py::61::_METADATA_NAME_RE: internal rege…`
- L27: `dead-constant::plugins/sea/skills/probe/scripts/probe/runners/scc_runner.py::26::_SCC_LANGUAGE_MAP: internal lookup; fal…`

### `.checkup/agents/check-readability-allowlist.md`

- L10: `naming-clarity::plugins/sea/skills/probe/scripts/probe/orchestrator.py::334: probe orchestrator entry-point convention`
- L11: `naming-clarity::plugins/sea/skills/probe/scripts/probe/render_templates/interactivity.js::85: interactivity.js JS entry …`
- L12: `naming-clarity::plugins/sea/skills/probe/scripts/probe/render_templates/interactivity.js::107: interactivity.js JS entry…`

### `.checkup/agents/check-reliability-allowlist.md`

- L10: `broad-except::plugins/sea/skills/probe/scripts/probe.py::179: probe orchestrator pattern (partial-success expected)`
- L11: `broad-except::plugins/sea/skills/probe/scripts/probe/runners/architecture_runner.py::101: probe runner pattern`
- L12: `broad-except::plugins/sea/skills/probe/scripts/probe/runners/architecture_runner.py::136: probe runner pattern`
- L13: `broad-except::plugins/sea/skills/probe/scripts/probe/runners/deadcode_runner.py::72: probe runner pattern`
- L14: `broad-except::plugins/sea/skills/probe/scripts/probe/runners/deadcode_runner.py::82: probe runner pattern`
- L15: `broad-except::plugins/sea/skills/probe/scripts/probe/runners/deadcode_runner.py::91: probe runner pattern`
- L16: `broad-except::plugins/sea/skills/probe/scripts/probe/runners/deployment_runner.py::337: probe runner pattern`
- L17: `broad-except::plugins/sea/skills/probe/scripts/probe/runners/duplication_runner.py::55: probe runner pattern`
- L18: `broad-except::plugins/sea/skills/probe/scripts/probe/runners/lint_runner.py::112: probe runner pattern`
- L19: `broad-except::plugins/sea/skills/probe/scripts/probe/runners/test_runner.py::158: probe runner pattern`
- L20: `broad-except::plugins/sea/skills/probe/scripts/probe/runners/test_runner.py::211: probe runner pattern`
- L21: `broad-except::plugins/sea/skills/probe/scripts/probe/workspace.py::137: probe workspace setup; partial-failure tolerance`

### `.checkup/agents/security-allowlist.md`

- L8: `AWS Access Key ID::plugins/sea/skills/probe/tests/integration/test_end_to_end_polyglot.py::144::AKIA1234…: sea:probe tes…`
- L9: `AWS Access Key ID::plugins/sea/skills/probe/tests/unit/test_credential_runner.py::180::AKIA1234…: sea:probe test fixture`
- L10: `AWS Access Key ID::plugins/sea/skills/probe/tests/unit/test_credential_runner.py::193::AKIA1234…: sea:probe test fixture`
- L11: `AWS Access Key ID::plugins/sea/skills/probe/tests/unit/test_credential_runner.py::205::AKIA9999…: sea:probe test fixture`
- L14: `gitleaks::generic-api-key::plugins/sea/skills/probe/tests/unit/test_credential_runner.py::46: sea:probe test fixture`
- L15: `gitleaks::generic-api-key::plugins/sea/skills/probe/tests/unit/test_credential_runner.py::59: sea:probe test fixture`
- L16: `gitleaks::generic-api-key::plugins/sea/skills/probe/tests/unit/test_credential_runner.py::180: sea:probe test fixture`
- L25: `# semgrep::python.lang.security.use-defused-xml.use-defused-xml::plugins/sea/skills/probe/scripts/probe/workspace.py::40…`
- L26: `# semgrep::python.lang.security.use-defused-xml-parse.use-defused-xml-parse::plugins/sea/skills/probe/scripts/probe/work…`

### `README.md`

- L54: `| **[sea](plugins/sea/)** | Senior Engineering Architect — designs hardened architectures and decomposes them into atomi…`
- L74: `- `.architecture/{project}/TDD.md` + Work Packages — produced by `/sea:blueprint``
- L91: `/sea:blueprint <project-slug>`

### `plugins/sulis-execution/.architecture/hardening-deltas/HD-004-plugin-manifest-description-bloat.md`

- L36: `- `plugins/sea/CHANGELOG.md` — same migration`
- L44: `- `plugins/sea/.claude-plugin/plugin.json` — 10,841 → 305 chars`
- L94: `'plugins/sea/.claude-plugin/plugin.json',`

### `plugins/sulis-execution/.architecture/hardening-deltas/HD-007-gates-inside-verify-phase.md`

- L21: `1. **Step 10.5** — `/sea:code-review` against the batch diff range,`

### `plugins/sulis-execution/.architecture/hardening-deltas/HD-008-index-as-computed-view.md`

- L341: `Splitting lets `/sea:code-review` run twice with focused diffs each`

### `plugins/sulis-execution/sdk/docs/recipes/backfill-code-review.md`

- L7: ``/sea:code-review` invocation. The historical record shows`
- L66: `- Invokes `/sea:code-review <parent>..<merge_sha> <slug>``
- L145: `# /sea:code-review is a top-level skill (not an SDK operation);`
- L188: `- `plugins/sea/skills/code-review/SKILL.md` — the skill this`

### `plugins/sulis-execution/sdk/python/tests/test_resources_smoke.py`

- L137: `"Dispatch /sea:code-review against diff_range; "`

### `plugins/sulis-execution/sdk/sulis-execution.openapi.yaml`

- L1168: `for `git diff` / `gh pr diff` / `/sea:code-review`.`

### `plugins/sulis-security/README.md`

- L157: `Hardening Deltas via `/sea:harden`. The report cross-references existing`

### `plugins/sulis-security/agents/security-reviewer.md`

- L287: `When your report is produced, recommend `/sea:codebase-audit` and then`
- L288: ``/sea:harden` for any project that also wants a structural hardening pass on`

### `plugins/sulis-security/skills/codebase-assess/SKILL.md`

- L304: `delta, recommend `/sea:harden` to convert them into deltas; for findings`
- L398: `{Critical and high-severity items. If SEA is installed, recommend `/sea:harden` to convert to Hardening Deltas.}`
- L430: `7. If applicable, suggest `/sea:harden` as the next step.`

### `plugins/sulis/agents/context-cartographer.md`

- L209: `out of scope. Refer them to `/sea:codebase-audit` or `/sulis-security:codebase-assess`.`
- L211: `you don't author. Refer them to `/sea:blueprint`.`

### `plugins/sulis/agents/executor.md`

- L68: `10. **`plugins/sea/references/red-green-blue.md`** — RGB-01..03: the`

### `plugins/sulis/agents/requirements-analyst.md`

- L312: `| `.architecture/{project}/probe-raw/1_2_capabilities.json` (when `/sea:probe` has run, v0.9.0+) | The capability invent…`
- L414: ``/sea:blueprint` or `/sea:codebase-audit`.`
- L999: ``/sea:blueprint` and `/sea:harden`.`
- L1095: `SEA's `/sea:harden` does the deeper work.`
- L1375: `/sea:blueprint .specifications/{name}/`
- L1450: `> /sea:blueprint .specifications/{name}/`
- L1505: `| Designing something new / "how would I build X" | `/sea:blueprint` |`
- L1506: `| Existing code / "where do I make the change" / "audit the codebase" | `/sea:codebase-audit` |`
- L1507: `| Production-readiness / resilience / "make this robust" | `/sea:harden` |`
- L1541: `> /sea:blueprint .specifications/{name}/HANDOFF_TO_SEA.md`
- L1542: `> /sea:codebase-audit .specifications/{name}/HANDOFF_TO_SEA.md`
- L1543: `> /sea:harden .specifications/{name}/HANDOFF_TO_SEA.md`
- L1552: `- Predominantly *new system / new feature* architecture intent → `/sea:blueprint``
- L1554: ``/sea:codebase-audit``
- L1555: `- Predominantly *resilience / hardening / production-readiness* intent → `/sea:harden``
- L1623: `> ✗ *"PASS confirmed. Three small things still outstanding: (a) fix the line-count drift; (b) record the feedback memory…`
- L1629: `> ✓ *"PASS confirmed. Fixed the line-count drift in TDD §9. Recorded the pre-write check-in observation as a feedback me…`
- L2412: `Those are real questions, but they belong with the engineering architect (`/sea:blueprint``
- L2413: `or `/sea:harden`), not with requirements. Can I park those and come back to [open`

### `plugins/sulis/agents/sulis.VERIFICATION_REPORT.md`

- L157: `| engineering-architect | `plugins/sea/agents/engineering-architect.md` | YES |`

### `plugins/sulis/agents/sulis.md`

- L89: `skill: ../../sea/agents/engineering-architect`
- L778: `done. Starting design — recommending you run `/sea:blueprint` next."*`
- L1104: `> 4. Start building — kick off /sea:harden or /sulis:run-all.`
- L1148: `| 4 | **Design** | TDD, ADRs, Work Packages | `sea:engineering-architect` — recommend `/sea:blueprint` then `/sea:decomp…`
- L1150: `| 6 | **Verify** | Completeness, contracts, chaos tests | `sea:engineering-architect` — recommend `/sea:verify` (v0.2: s…`
- L1172: `22-primitive vocabulary (see `plugins/sea/references/change-primitives.md`).`
- L1402: `> *`/sea:blueprint`*`
- L1407: `> *`/sea:decompose`*`
- L1603: `> *`/sea:verify`*`
- L1724: `- *"Now we move to design. Run `/sea:blueprint` when you're ready. I'll`

### `plugins/sulis/docs/executor-research/cicd-batching-analysis.md`

- L60: `I read `plugins/sea/agents/engineering-architect.md`,`
- L61: ``plugins/sea/skills/decompose/SKILL.md`, and`
- L62: ``plugins/sea/references/change-primitives.md` end-to-end.`
- L330: `- `plugins/sea/agents/engineering-architect.md``
- L331: `- `plugins/sea/skills/decompose/SKILL.md` (lines 206-288 INDEX.md structure;`
- L333: `- `plugins/sea/references/change-primitives.md` (22 primitives, 5 groups)`

### `plugins/sulis/docs/executor-research/integration-change-review-prompt.md`

- L281: `For repeated use, save it as a skill (e.g., `/sea:integration-review`) that`
- L425: `- [`plugins/sea/references/code-review-standard.md`](../../../sea/references/code-review-standard.md) — CR-NN (related b…`

### `plugins/sulis/docs/executor-research/sdk-implementation-validation-rubric.md`

- L593: `- [`plugins/sea/references/code-review-standard.md`](../../../sea/references/code-review-standard.md) — CR-01..CR-09 (re…`

### `plugins/sulis/references/change-work-standard.md`

- L39: `| **SEA Change Primitives** (`plugins/sea/references/change-primitives.md`) | This marketplace | The 22-primitive catalo…`
- L143: ``plugins/sea/references/change-primitives.md`, lowercased: `create`,`
- L355: `### With change primitives (`plugins/sea/references/change-primitives.md`)`

### `plugins/sulis/references/convention-preference-standard.md`

- L69: `inventory (produced by `/sea:probe`)`

### `plugins/sulis/references/founder-english.md`

- L540: `### Primitive-Name Translation (per `plugins/sea/references/change-primitives.md`)`
- L823: `permission gates. Just announce: *"Run `/sea:blueprint` next."*`
- L828: `*"Now we design how it'll work. Run `/sea:blueprint`."*`

### `plugins/sulis/references/git-workflow-standard.md`

- L427: ``plugins/sulis/references/` or `plugins/sea/references/` follow the`

### `plugins/sulis/references/journey-model.md`

- L118: `- Recommend `/sea:blueprint` (produces TDD + ADRs).`
- L120: `- Recommend `/sea:decompose` (produces Work Packages with INDEX).`
- L173: `- Recommend `/sea:verify` to the founder.`
- L246: `> `/sea:blueprint` next."*`

### `plugins/sulis/references/lifecycle.md`

- L23: `| 10.5 | **Train-batch code-review (IMPLEMENTED v0.21.1+ as post-merge variant; folded into `_verify_phase` boundary at …`
- L1672: ``outcome: success`, the `run-all` skill dispatches `/sea:code-review``

### `plugins/sulis/references/self-heal-budget.md`

- L21: `| **Code-review inline fix loop** (v0.20.1+) | 6.5 | 3 | `/sea:code-review` produces findings → inline fix → re-run `/co…`

### `plugins/sulis/references/standards/WORK_PACKAGE_STANDARD.md`

- L309: `- `plugins/sea/skills/probe/scripts/probe/workspace.py` line 40 (import)`
- L310: `- `plugins/sea/skills/probe/scripts/probe/workspace.py` line 269 (parse call site)`
- L311: `- `plugins/sea/skills/probe/requirements.txt` — add `defusedxml>=0.7.1``

### `plugins/sulis/references/subagent-dispatch.md`

- L47: `- *"Run `/sea:blueprint` next."* ✓`
- L59: `| sea:blueprint | `/sea:blueprint` | recommend | recommend (always; long conversation) |`
- L60: `| sea:decompose | `/sea:decompose` | recommend | spawn (short, autonomous) |`
- L61: `| sea:verify | `/sea:verify` | recommend | spawn (short, returns COMPLETENESS_REPORT) |`

### `plugins/sulis/scripts/tests/README.md`

- L4: `established pattern at `plugins/sea/skills/probe/tests/`.`

### `plugins/sulis/scripts/tests/integration/test_wpx_journal.py`

- L56: `judgement rather than invoke /sea:code-review at all.`

### `plugins/sulis/scripts/wpx-train`

- L151: `context={"hint": "Has /sea:decompose been run for this project?"},`
- L1662: `"Calling session: dispatch /sea:code-review against the diff "`

### `plugins/sulis/skills/add-agent/VERIFICATION_REPORT.md`

- L165: `| engineering-architect (example cited) | `plugins/sea/agents/engineering-architect.md` | YES | |`

### `plugins/sulis/skills/add-agent/references/agent-shape-conventions.md`

- L247: `| Specialist analytical | `plugins/sea/agents/engineering-architect.md` |`

### `plugins/sulis/skills/add-agent/templates/agent.md.template`

- L17: `skill: {{e.g., ../skills/run-wp, ../../sea/agents/engineering-architect}}`

### `plugins/sulis/skills/add-skill/references/kinds-and-tools-learnings.md`

- L39: `specific new skill (e.g., authoring `/sea:code-hygiene`) is the`

### `plugins/sulis/skills/address-findings/SKILL.md`

- L198: `- SP-001 — /sea:split-kitchen-sink — 4 of 6 kitchen-sink findings have mechanically-identical`
- L256: `- A `/sea:code-review` run produced draft Hardening Deltas the founder wants to operationalise`

### `plugins/sulis/skills/address-findings/iterations/1/VERIFICATION_REPORT.md`

- L115: `| sea:engineering-architect | `plugins/sea/agents/engineering-architect.md` | (assumed exists; SEA plugin) — to verify i…`
- L119: `| sea:decompose | `plugins/sea/skills/decompose/` | YES |`
- L120: `| sea:harden | `plugins/sea/skills/harden/` | YES |`

### `plugins/sulis/skills/backfill-code-review/SKILL.md`

- L4: `Retroactive /sea:code-review for WPs that shipped without bundles`
- L8: `invokes /sea:code-review with the commit range, registers findings`
- L22: `invoking `/sea:code-review` — no bundle file on disk; no audit`
- L46: `- Invoke `/sea:code-review <parent>..<merge_sha> <project>`.`
- L151: `# Invoke /sea:code-review against the historical range`
- L173: `Findings in /sea:code-review's PH-06 signal table have severity`
- L308: `top-level skill invocations (`/sea:code-review`), parsing free-form`
- L330: `- `plugins/sea/skills/code-review/SKILL.md` — the skill this`

### `plugins/sulis/skills/backfill-code-review/recipes/post-rollout.md`

- L6: `invoking `/sea:code-review` — no bundle on disk; no audit trail.`
- L62: `2. For each (default: all 9): invoke `/sea:code-review <parent>..<merge_sha> agent-applications``

### `plugins/sulis/skills/check-polish/SKILL.md`

- L89: `• `plugins/sea/scripts/probe/runner.py` has 23 TODO markers`

### `plugins/sulis/skills/check-polish/references/polish-rules.md`

- L59: `- `tech-debt-density::{file}::{rule}` (e.g., `tech-debt-density::plugins/sea/scripts/probe.py::TD-001`)`

### `plugins/sulis/skills/check-readability/COMPLETENESS_REPORT.md`

- L41: `- `plugins/sea/references/boring-code.md` (8K) — Boring Code Standard. Defines simple-over-clever; directly relevant to …`

### `plugins/sulis/skills/check-readability/references/founder-translation.md`

- L66: `- Terms in `plugins/sea/references/boring-code.md``

### `plugins/sulis/skills/check-security/COMPLETENESS_REPORT.md`

- L82: `- Real-state test against marketplace: ran scanner; **caught the test-fixture AWS key in `plugins/sea/skills/probe/tests…`

### `plugins/sulis/skills/check-security/iterations/2/VERIFICATION_REPORT.md`

- L61: `1. `plugins/sea/skills/probe/scripts/probe/workspace.py:40` — XXE vulnerability (use defusedxml)`
- L62: `2. `plugins/sea/skills/probe/scripts/probe/workspace.py:269` — XXE vulnerability (use defusedxml)`

### `plugins/sulis/skills/code-health/SKILL.md`

- L187: `1. `plugins/sea/skills/probe/scripts/probe/workspace.py:40` — XXE`

### `plugins/sulis/skills/code-health/agent_prompts/check-readability.md`

- L32: ``plugins/sea/skills/probe/` — candidate for refactor."`

### `plugins/sulis/skills/consolidate-into-sulis/references/conflict-resolution.md`

- L101: `description: Use after /sea:blueprint has produced a TDD. Decomposes the TDD into atomic Work Packages (WP-NNN-*.md) tha…`

### `plugins/sulis/skills/consolidate-into-sulis/references/external-ref-sweep.md`

- L28: `Pattern: descriptions sometimes cite `/sea:blueprint`, `/srd:critical-thinking`, etc. These break on consolidation.`

### `plugins/sulis/skills/consolidate-into-sulis/runs/srd-2026-05-25/VERIFICATION_REPORT.md`

- L92: `| Additional manual edits (skill-authoring guides + sea README) | 5 substitutions across 4 files (CLAUDE.md L41, CONTRIB…`
- L95: `| Live `(../)+srd/` refs after sweep | 1 intentional DEPRECATED pointer in plugins/sea/README.md |`

### `plugins/sulis/skills/consolidate-into-sulis/runs/srd-2026-05-25/code-health-baseline.json`

- L95: `"file": "plugins/sea/skills/probe/scripts/probe/workspace.py",`
- L102: `"signature": "semgrep::python.lang.security.use-defused-xml.use-defused-xml::plugins/sea/skills/probe/scripts/probe/work…`
- L108: `"file": "plugins/sea/skills/probe/scripts/probe/workspace.py",`
- L115: `"signature": "semgrep::python.lang.security.use-defused-xml-parse.use-defused-xml-parse::plugins/sea/skills/probe/script…`

### `plugins/sulis/skills/consolidate-into-sulis/runs/srd-2026-05-25/code-health-final.json`

- L108: `"file": "plugins/sea/skills/probe/scripts/probe/workspace.py",`
- L115: `"signature": "semgrep::python.lang.security.use-defused-xml.use-defused-xml::plugins/sea/skills/probe/scripts/probe/work…`
- L121: `"file": "plugins/sea/skills/probe/scripts/probe/workspace.py",`
- L128: `"signature": "semgrep::python.lang.security.use-defused-xml-parse.use-defused-xml-parse::plugins/sea/skills/probe/script…`

### `plugins/sulis/skills/consolidate-into-sulis/runs/srd-2026-05-25/external-refs-post-commit3.md`

- L21: `- L119: `- Skill scope creep. `/sea:blueprint` is not `/srd:requirements-analyst`.``
- L71: `### `plugins/sea/CHANGELOG.md``
- L75: `### `plugins/sea/README.md``
- L82: `### `plugins/sea/agents/engineering-architect.md``
- L91: `### `plugins/sea/references/code-review-standard.md``
- L96: `### `plugins/sea/skills/blueprint/SKILL.md``
- L100: `### `plugins/sea/skills/code-review/SKILL.md``
- L106: `### `plugins/sea/skills/suggest-split/SKILL.md``
- L289: `- L427: ``plugins/srd/references/` or `plugins/sea/references/` follow the``
- L339: `- L28: `Pattern: descriptions sometimes cite `/sea:blueprint`, `/srd:critical-thinking`, etc. These break on consolidati…`
- L381: `- L21: `- L119: `- Skill scope creep. `/sea:blueprint` is not `/srd:requirements-analyst`.```
- L507: `- L313: `- L28: `Pattern: descriptions sometimes cite `/sea:blueprint`, `/srd:critical-thinking`, etc. These break on co…`
- L508: `- L317: `- L103: `| Plus: `plugins/sea/agents/*.md`, `plugins/sea/skills/*/SKILL.md`, `plugins/srd/agents/*.md` (4 slash…`
- L509: `- L321: `- L21: `command being recommended (e.g. `/srd:start`, `/sea:blueprint`,```
- L512: `- L334: `- L57: ``/srd:requirements-analyst` or `/sea:blueprint` to fill them```
- L517: `- L103: `| Plus: `plugins/sea/agents/*.md`, `plugins/sea/skills/*/SKILL.md`, `plugins/srd/agents/*.md` (4 slash-command …`
- L521: `- L21: `command being recommended (e.g. `/srd:start`, `/sea:blueprint`,``
- L534: `- L57: ``/srd:requirements-analyst` or `/sea:blueprint` to fill them``

### `plugins/sulis/skills/consolidate-into-sulis/runs/srd-2026-05-25/external-refs.md`

- L21: `- L119: `- Skill scope creep. `/sea:blueprint` is not `/srd:requirements-analyst`.``
- L71: `### `plugins/sea/CHANGELOG.md``
- L75: `### `plugins/sea/README.md``
- L82: `### `plugins/sea/agents/engineering-architect.md``
- L91: `### `plugins/sea/references/code-review-standard.md``
- L96: `### `plugins/sea/skills/blueprint/SKILL.md``
- L100: `### `plugins/sea/skills/code-review/SKILL.md``
- L106: `### `plugins/sea/skills/suggest-split/SKILL.md``
- L313: `- L28: `Pattern: descriptions sometimes cite `/sea:blueprint`, `/srd:critical-thinking`, etc. These break on consolidati…`
- L317: `- L103: `| Plus: `plugins/sea/agents/*.md`, `plugins/sea/skills/*/SKILL.md`, `plugins/srd/agents/*.md` (4 slash-command …`
- L321: `- L21: `command being recommended (e.g. `/srd:start`, `/sea:blueprint`,``
- L334: `- L57: ``/srd:requirements-analyst` or `/sea:blueprint` to fill them``

### `plugins/sulis/skills/consolidate-into-sulis/runs/sulis-context-2026-05-25/VERIFICATION_REPORT.md`

- L103: `| Plus: `plugins/sea/agents/*.md`, `plugins/sea/skills/*/SKILL.md`, `plugins/srd/agents/*.md` (4 slash-command hits) | —…`

### `plugins/sulis/skills/consolidate-into-sulis/runs/sulis-context-2026-05-25/code-health-baseline.json`

- L95: `"file": "plugins/sea/skills/probe/scripts/probe/workspace.py",`
- L102: `"signature": "semgrep::python.lang.security.use-defused-xml.use-defused-xml::plugins/sea/skills/probe/scripts/probe/work…`
- L108: `"file": "plugins/sea/skills/probe/scripts/probe/workspace.py",`
- L115: `"signature": "semgrep::python.lang.security.use-defused-xml-parse.use-defused-xml-parse::plugins/sea/skills/probe/script…`

### `plugins/sulis/skills/consolidate-into-sulis/runs/sulis-context-2026-05-25/code-health-final.json`

- L95: `"file": "plugins/sea/skills/probe/scripts/probe/workspace.py",`
- L102: `"signature": "semgrep::python.lang.security.use-defused-xml.use-defused-xml::plugins/sea/skills/probe/scripts/probe/work…`
- L108: `"file": "plugins/sea/skills/probe/scripts/probe/workspace.py",`
- L115: `"signature": "semgrep::python.lang.security.use-defused-xml-parse.use-defused-xml-parse::plugins/sea/skills/probe/script…`

### `plugins/sulis/skills/handoff/SKILL.md`

- L21: `command being recommended (e.g. `claude --agent requirements-analyst`, `/sea:blueprint`,`

### `plugins/sulis/skills/requirements-validation/SKILL.md`

- L73: `(`/sea:blueprint .specifications/{name}/`) is surfaced in the **action-then-report`
- L77: `> ready. Starting `/sea:blueprint`."*`
- L81: `> ✗ *"PASS. Recommend `/sea:blueprint` as the natural next step. Want me to proceed?"*`
- L705: `| 2026-05-15 | Rewrote PASS exit prose to use action-then-report shape per AAF-08 (Decided Actions Are Not Questions). T…`

### `plugins/sulis/skills/retry/SKILL.md`

- L122: ``/sea:decompose` to re-classify.`

### `plugins/sulis/skills/run-all/SKILL.md`

- L36: `dispatches `/sea:code-review` against the BATCH DIFF RANGE`
- L403: `composition of all WPs in the batch via `/sea:code-review` against`
- L434: `Invoke `/sea:code-review` against the range:`
- L462: `--root-cause "Cross-WP composition issue surfaced by /sea:code-review against batch diff <range>" \`
- L929: `surface: *"INDEX is empty. Run `/sea:decompose` first."*`

### `plugins/sulis/skills/show-context/SKILL.md`

- L57: ``requirements-analyst` or `/sea:blueprint` to fill them`

## 2. Subagent_type dispatch references

None.

## 3. Sweep checklist (apply during Commits 2–4)

For each line above:
- Replace `plugins/{source}/` with `plugins/sulis/`
- Apply any skill / agent / reference renames from CONSOLIDATION_PLAN.md
- For subagent_type references: update to the new agent location after Commit 3 lands

After Commit 4:
```bash
git grep "plugins/sea/" .
# Expected: zero hits outside the source plugin's own DEPRECATED shell
```

## Summary

- Path references: **308** across **71** files
- Subagent_type references: **0** across **0** files

