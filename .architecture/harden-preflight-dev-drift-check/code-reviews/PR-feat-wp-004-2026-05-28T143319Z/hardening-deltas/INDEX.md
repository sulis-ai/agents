# Hardening Deltas — code-review PR-feat-wp-004

No draft deltas. The single review finding (missing timeout on the new
`gh api` subprocess call in `wpx-preflight._protection_status`) was fixed
inline within WP-004, not deferred. The pre-existing ruff baseline items
(`_wpxlib.py` 1880 / 3531 / 3532) are on the Watch List in REVIEW.md and are
out of scope for this WP.
