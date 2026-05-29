# Step 10.5 + 11 Gate Review — train-2026-05-29T151927Z (WP-001, WP-002, WP-004)

Batch diff range: f9c4856..dde80c46 (change/feat-cockpit-contract-preview)

## Step 10.5 — cross-WP composition review
Mechanical floor: bundled-tip CI green (train) + renderer suite 40/40 green at merged tip.

Findings:
- **CONCERN — shared-manifest filename mismatch.** wpx-render-contract writes
  `CONTRACT.manifest.json` (WP-001); wpx-render-ui reads/merges `manifest.json`
  (WP-002, _render_ui.py MANIFEST_NAME). The two never see each other's file →
  data_contract + ui_contract keys split across two files instead of the single
  shared manifest WP-003 consumes. Not yet shipped-breaking (WP-003 not built).
  FIX before WP-003: align both renderers on ONE manifest filename + a
  composition test (render-contract then render-ui → single manifest carries
  BOTH keys). Pin the manifest as WP-003's input contract.
- ADVISORY — manifest key shape (`ui_contract: present|none`) not pinned by a TS
  type; resolve when WP-003 builds against the manifest contract.
- ADVISORY — HTML vs CSS escaping in the two renderers: justified (different
  contexts); no fix.
- ADVISORY — `.resolve()` on worktree path in render-contract but not render-ui;
  fold into the manifest fix.

## Step 11 — per-WP post-merge security (all PASS, no CRITICAL/CONCERN)
- WP-001 (wpx-render-contract): PASS_WITH_ADVISORIES. Injection/traversal/secrets
  clean (verified). ADVISORY: deeply-nested spec → RecursionError surfaces as a
  stderr traceback instead of a clean data-error/raw-fallback.
- WP-002 (wpx-render-ui): PASS. </style> breakout + @import injection closed.
  ADVISORY: url(javascript:)/expression() inert on modern browsers; symlinked
  token-file read (low). Optional CSP meta tag.
- WP-004 (recreate-on-demand): PASS_WITH_ADVISORIES. Read-only invariant sound;
  spawn discipline good (argv, shell:false, 30s timeout, recreate verb only).
  ADVISORY: shape-validate `handle` at the recreate boundary (fold into WP-003);
  no concurrency cap (loopback-only, fine).

## Verdict
No CRITICAL. One CONCERN (manifest mismatch) → remediate before WP-003.
Gates clean for finalisation; remediation tracked as a follow-up WP that WP-003 depends on.
