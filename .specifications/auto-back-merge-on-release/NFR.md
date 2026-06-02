# NFR — auto-back-merge-on-release

Non-functional requirements. Every NFR here is measurable and falsifiable.
Several are derived from the adversarial sweep (MISUSE_CASES.md).

---

## NFR-001: Bounded race window

The reusable workflow MUST record dev's HEAD SHA at the time the release PR
is opened, and MUST verify against the current dev SHA at robot-run time.
The race window is therefore "release PR open → release robot back-merge
step." No race detection is required outside this window because no
back-merge attempt occurs outside it.

**Measurable target:** The release-PR body MUST contain a machine-readable
line of the form `dev-sha-at-open: <40-char SHA>`. The back-merge step MUST
fail-safely (fall through to PR path) if the line is absent or malformed.

**Verification:** Inspect the release PR body in CI; assert presence and
format.

---

## NFR-002: No force-push to dev

The reusable workflow MUST NEVER use `git push --force`, `--force-with-lease`,
or any equivalent operation against `origin/dev`. The only permitted update
mechanisms are (a) fast-forward `git push origin main:dev` when dev's SHA
matches the snapshot pin, and (b) opening a pull request with base=dev,
head=main.

**Measurable target:** Static scan of the reusable workflow YAML for the
strings `--force`, `--force-with-lease`, or `+main:dev` (the `+` is git's
force-push syntax). Zero occurrences targeting dev.

**Verification:** CI step `grep -nE '(\+main:dev|--force|--force-with-lease).*(dev)'`
against the workflow file; pre-commit hook in the standards repo.

---

## NFR-003: Backward compatibility for existing consumers

Fork-consumers who have NOT yet added the shim MUST continue to function
exactly as before. Their releases bump main; their dev stays drifted (the
current state). This NFR is intentionally weak: we are not auto-fixing
existing consumers — they must opt in by installing the shim.

**Measurable target:** The plugin update that ships this change does NOT
modify any consumer-side file. Consumer adoption is gated on the consumer
adding their own `.github/workflows/release-on-merge.yml` shim.

**Verification:** Inspect the plugin's installation behaviour; assert no
write to any path outside the plugin's own directory.

---

## NFR-004: Visibility of every back-integration

Every back-integration (clean OR raced) MUST produce a visible signal on
dev's git history.

- **Clean path:** Dev's HEAD advances to main's HEAD. `git log dev -1`
  shows the release commit by github-actions[bot].
- **Raced path:** A merge commit appears on dev with message `chore:
  back-integrate main → dev (post-release v<version>)`, authored by
  github-actions[bot], referencing the release tag.

**Measurable target:** After every release, `git log --author=github-actions
--grep='release\|back-integrate' dev -2` returns at least one matching
commit dated within the last 24 hours.

**Verification:** CI check on dev after release; manual spot-check via
`git log dev`.

---

## NFR-005: Fork-consumer opt-out is one file deletion

A fork-consumer MUST be able to opt out of auto-back-merge by deleting
exactly one file: `.github/workflows/release-on-merge.yml` (their shim).
After deletion, their release flow stops auto-back-merging; they accept
the drift and any consequent manual recovery burden.

**Measurable target:** Documented in HANDOFF_TO_SEA.md and in the plugin
README. No other file in the consumer's repo needs to be touched for opt-out.

**Verification:** Documentation review; n=1 dogfood by deleting the
marketplace's own shim and confirming the workflow stops firing on next
push to main.

---

## NFR-006: Atomicity of the release-and-back-merge unit

The release robot MUST NOT report success unless EITHER (a) dev has been
fast-forwarded to main AND main has been bumped+tagged, OR (b) a back-merge
PR is open AND main has been bumped+tagged. A bumped main with no
back-merge artifact (PR or fast-forwarded dev) is a workflow failure.

**Measurable target:** Workflow exit status is success iff a post-condition
check passes: `git rev-parse origin/dev` matches `origin/main` OR a PR
matching `head:main base:dev` exists in `open` state. Otherwise exit 1.

**Verification:** Final step of the reusable workflow runs the
post-condition check; chaos test simulates failure between bump and
back-merge and asserts workflow fails loudly.

---

## NFR-007: Drift detection is fast and deterministic

Both `/sulis:release-train` and `/sulis:change start` MUST run their drift
detection check in under 5 seconds (excluding network fetch time) and MUST
produce a deterministic result given the same git state.

**Measurable target:** The check is a single `git merge-base --is-ancestor
origin/main origin/dev` (O(log N) in commit count). Skill execution
measures and logs the check duration.

**Verification:** Local benchmark on the marketplace repo's current commit
count (~thousands); CI step asserts duration < 5s on a fresh checkout.

---

## NFR-008: Version-pin is the default, always-track is opt-in

The canonical shim documented in HANDOFF_TO_SEA.md and in the plugin's
README MUST reference the reusable workflow at a SemVer tag (e.g.,
`@sulis-v0.86.0`). The `@dev` always-track form is permitted and MUST be
documented, but flagged as opt-in with explicit risk language.

**Measurable target:** The canonical shim template in
`plugins/sulis/templates/shims/release-on-merge.yml` references a SemVer
tag. The README section on the shim documents both forms but recommends
the pinned form.

**Verification:** Template inspection; README review.
