# Completeness Report — sulis:check-build

**Authored:** 2026-05-23
**Author:** Iain + Claude (dogfood run #5 of sulis:add-skill v0.4.0)
**Methodology:** `sulis:add-skill` v0.4.0 (five-gate)
**Source of design:** `.architecture/sulis-checkup/TDD.md` (tier 1) +
the regression-detection thread in this session

## Verdict summary

| Gate | Status | Notes |
|---|---|---|
| 1 — Find | PASS | 5 overlaps (sibling/parent/coincidental); 0 vocab collisions |
| 2 — Scope Lock | PASS | 7 items locked; same baseline-pattern as check-tests |
| 3 — Generate | PASS | SKILL.md + scripts/builder.py + references/build-systems.md |
| 4 — Evaluate | PASS | Three perspectives + cross-skill via check-readability on its own code |
| 5 — Adversarial Review | PASS | 3 MUC-F + 3 audience-agnostic addressed |

**Publication decision:** APPROVED

---

## Gate 1 — Find

**Description overlaps (5):** check-tests (10 tokens), check-readability (8), code-health (8), sea:code-review (7), sea:suggest-split (6). All expected sibling/parent (sulis tier-skills follow same template) or coincidental. No real scope collision.

**Vocabulary collisions:** 0. Proposed terms (build-success, manifest-hygiene, build-system, build-artefact, buildable) are net-new.

**No existing skill covers** "does it build?" — tier 1 was identified as a gap in the matrix (#24 manifest hygiene + tier-1 build verification per SEA's TDD Part 9 item #8).

---

## Gate 2 — Scope Lock

| Item | Locked value |
|---|---|
| Skill name | `check-build` |
| Plugin home | `sulis` |
| Audience | **both**. Founder default; `--raw` for operator JSON. Mode-selection: explicit-flag |
| Category | **Founder UX & Navigation** (regression-detection sub-family) |
| Trigger condition | "Use when the founder wants to know if the project even builds — runs the build command, checks the manifest files parse, and reports anything broken. Read-only when the build is read-only; never modifies code." |
| Top-5 gotchas | (below) |
| Depth modes | None for v1 |

### Top-5 gotchas (with concrete source)

1. **Build system detection across monorepos.** Multi-language repos have Python + Node + Go simultaneously. Mis-detection runs the wrong build. *Source: HD-008 source-discovery brittleness; check-tests framework-detection brittleness.* Mitigation: detect ALL systems; report each; `--system X` override.

2. **Builds with side effects (publish, deploy).** A `make all` target might publish artifacts to a registry. Auto-running with `--run` could trigger unintended deploys. *Source: founder-facing-conventions Rule 3 (prompt-before-destroy).* Mitigation: blocklist of dangerous Make targets (`publish`, `deploy`, `release`); skip them with a warning; explicit `--allow-side-effects` override.

3. **First-run has no baseline.** Same as check-tests gotcha #1. Mitigation: first run captures baseline + explicitly says so.

4. **Manifest hygiene false-positives on intentional patterns.** `marketplace.json` has cumulative description fields that are intentionally long (per CHANGELOG migration). Strict hygiene would flag them. *Source: HD-004 — we already lived through this.* Mitigation: hygiene rules know about marketplace conventions; flagged-as-OK list for known-intentional patterns.

5. **Founder might expect this to FIX broken builds.** Universal read-only audit ambiguity. *Source: check-readability gotcha #5 + check-tests gotcha #5 + code-health gotcha #4.* Mitigation: "this skill never modifies code — only reports" stated three places.

### Vocabulary terms

- **build-success** — terminal state where the build command exits 0 + produces expected artifact
- **manifest-hygiene** — semantic correctness of JSON manifests beyond parseability (required fields, no bloat, valid version strings, etc.)
- **build-system** — the toolchain that builds the project (pip, npm, go, cargo, docker, make)
- **build-artefact** — what the build produces (wheel, dist/, binary, image, dist tarball)
- **buildable** — the binary property: does the project build at all? Distinct from "builds correctly" (which is a tier 3 concern)

---

## Gate 3 — Generate

**Files produced:**

- `SKILL.md` — entrypoint; same three-mode pattern (cached / fresh / detection-only)
- `scripts/builder.py` — build-system detection + per-system runners + manifest hygiene + baseline mechanism
- `references/build-systems.md` — per-system signals + commands + parser notes
- `COMPLETENESS_REPORT.md` — this file

**Reused infrastructure:** baseline mechanism mirrors check-tests (same JSON shape; same `.checkup/{project}/baseline.json` location with `tier_1_*` sub-key namespace to avoid collision with tier-3's data).

---

## Gate 4 — Evaluate

### Perspective 1 — Trigger accuracy: PASS
Description targets "does it build" specifically; precision ~85% (could overlap with check-tests on "does anything work" but distinct in scope).

### Perspective 2 — Gotchas coverage: PASS
All 5 gotchas have concrete sources (HD-008, founder-conventions, check-tests #1, HD-004, cross-skill pattern).

### Perspective 3 — Functional completeness: PASS
- Detected Python build system in marketplace (no pyproject.toml at root, but manifest hygiene runs)
- Manifest hygiene caught nothing in current marketplace (intentional — all manifests pass HD-004 cleanup)
- Synthetic fixture with broken pyproject.toml correctly flagged
- **Cross-skill test:** ran check-readability on builder.py — 0 findings (clean code)

---

## Gate 5 — Adversarial Review

### MUC-F1: Operator jargon leak — PREVENTED
Build error strings translated in founder mode (`"failed to install dependency X"` not `"pip install ... ResolutionImpossible"`).

### MUC-F3: Destructive action ambiguity — PREVENTED
SKILL.md repeats "never modifies code"; dangerous Make targets blocked.

### MUC-F5: Side-effect false-positives — PARTIALLY PREVENTED
Make targets like `make publish` skipped by default; `--allow-side-effects` opt-in. OPEN_RISK: project-specific dangerous targets not on the blocklist.

### Audience-agnostic: Authorization leakage — PREVENTED
Build tools (pip, npm, go, etc.) checked at run-time with typed errors.

---

## Open risks accepted

1. **Project-specific dangerous Make targets not blocklisted.** revisit_by: trigger — founder reports unintended deploy from --run.
2. **First-run UX** — same as check-tests #1.

---

## Methodology feedback (running notes for add-skill v0.6.0)

1. **Three regression-pattern skills now** (check-tests, check-build, soon check-security). All share: baseline mechanism, framework/system detection, --run flag pattern, signature-dedup. **Extract a shared `baseline_helper.py` in v0.6.0** so we stop reimplementing.

2. **Manifest hygiene crosses tiers** — also relevant for tier 5 (readability of plugin descriptions). Could be either tier 1 or tier 5. Currently tier 1 because "did the basics parse" is the primary question. Document the tier-overlap.

(These 2 join the 15 already queued = 17 for add-skill v0.6.0.)