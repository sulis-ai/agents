# Gate review — train-2026-06-10T081954Z (CH-5DMB1N unique-wp-ids)

Range: 802b376b..1110fe5c (change/extend-unique-wp-ids). WPs: WP-001, WP-002, WP-003.

## Verdict: PASS-WITH-FOLLOW-UPS — no CRITICAL, no CONCERN

Combined cross-WP composition + security gate (proportionate single pass — small,
low-surface internal tooling: no user input, no auth, no network, no secrets).

### Correctness / composition — PASS
- Single-source id matcher (EP-03): tree-wide grep finds zero residual ad-hoc
  `startswith("WP-")` / `removeprefix("wp-")` in production code; all five callers
  route through `is_wp_id` / `wp_nnn_suffix` / `is_wp_id_filename`.
- Back-compat seam proven: one `parse_index_md` returns prefixed + legacy bare +
  source-tagged rows together (test_parse_index_both_shapes_in_one_parse).
- `wp_nnn_suffix`: doubled-prefix branch bug fixed; byte-for-byte legacy parity for
  non-prefixed ids; regex linear (no ReDoS).
- Docs (WP-002) + standards (WP-003) match code (WP-001), incl. chicken-and-egg caveat.
- 99 wpx unit tests pass on merged state.

### Security — PASS (negligible)
- id gate `[0-9A-Za-z-]` admits no shell metachars / path separators / null bytes;
  injection payloads rejected by is_wp_id before reaching branch resolution.
- Input is non-network, from the team's own committed INDEX.md.

### ADVISORY follow-ups (non-blocking)
1. `_WP_ID_RE` uses `$` (matches before a trailing newline); prefer `\Z`. Latent only
   (callers .strip() first). Captured as a follow-up.
2. (resolved in this finalise) Design artifacts / ADRs were uncommitted on the change
   branch, leaving the standards' ADR-002 reference dangling — committed as part of
   change finalisation.
