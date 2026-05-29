# harden: frontend local-verify must build workspace deps before typecheck

Closes #78.

## Problem

In the agent-journey frontend wave, executors ran `pnpm run typecheck` BEFORE
building the `@sulis-ai/*` workspace packages whose `exports` resolve to
`./dist/*`. With `dist/` absent, `tsc` failed fast on module resolution and
NEVER REACHED the rest of the file — masking genuine downstream type errors
(`m[1]` is `string | undefined` under `noUncheckedIndexedAccess`). The
executors honestly reported "typecheck clean" because `tsc` bailed before
finding the real error. Only the deps-built CI surfaced it. "typecheck clean"
was a false green (L-02).

## Fix

Add **WPF-14 (MUST)** to `WP_FRONTEND_STANDARD.md`: when the app imports
`workspace:*` packages whose exports resolve to a built `./dist/*`, the
executor's local typecheck / test / lint MUST first build those workspace
dependencies, reproducing the CI build order:

```bash
pnpm --filter "<app-package>..." build      # repo root, topo order
cd <app-dir> && pnpm run typecheck && pnpm run test && pnpm run lint
```

The "typecheck clean" DoD claim (WPF-11) is only valid when the imported
`workspace:*` deps are built. The Verification-gates section now notes the
dependency, and the version history records v0.2.0.

The corresponding CI-infra half (branch-ci frontend jobs needing the dep-build
step) is the producer's responsibility and was fixed inline on the platform
repo during the build; this change governs the durable executor/standard half.

## Tests

Documentation-only standard amendment — no executable test. Verification is
review + branch-ci's doc/reference checks.
