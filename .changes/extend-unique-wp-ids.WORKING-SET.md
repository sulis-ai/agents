# Working Set — extend-unique-wp-ids

> Live reasoning state for this change/session. **Read at the START of every turn;
> update as a side-effect of each decision** (never as a separate chore — that's
> how it dies). Sections 1–5 are current-state (overwritten as thinking moves);
> section 6 is append-only (never edited). Crystallizes into Opportunity / Design
> / Decision at the session boundary; if a session ends abruptly, this file IS
> the handoff to the next. Spec: plugins/sulis/docs/working-set-and-session-chain.md.

## 1. Problem  (→ Opportunity)
WP ids collide across changes (bare WP-NNN); mint globally-unique {CH-HANDLE}-WP-NNN while keeping per-change 1/2/3 sequence, with one-release back-compat for legacy bare ids

## 2. Current best solution  (→ Design)
Define the widened WP-id recognition ONCE in `_wpxlib.py` — a single regex
`_WP_ID_RE` + two thin readers `is_wp_id(s)` / `wp_nnn_suffix(s)` — sited next to
the existing `_WP_TABLE_HEADER_RE` shared matcher. Rewire all FIVE open-coded
sites to consume it: parse_index_md row-filter (L1801, the silent-drop seam),
_normalise_wp_reference full-id detection (L1730), _branch_name NNN extraction
(L1990), resolve_wp_branch NNN extraction (L2218), and _p_ver_rubric.py filename
filter (L111 — NOT in original recon seam list; found in design, inherits same
rule). Matcher accepts 3 shapes for one release: CH-<HANDLE>-WP-NNN (new mint),
WP-NNN (legacy bare), WP-<SOURCE>-NNN (existing). Strictly additive: no
migration, legacy ids stay parseable. Removal = future change.

Decomposed into 3 independent WPs: WP-001 (code, atomic — matcher + all 5
rewires + fixtures), WP-002 (docs — mint surfaces), WP-003 (docs — standards +
supersede parked). All parallelisable; no dependsOn edges.

TDD + ADR-001 + ADR-002 on disk at `.architecture/extend-unique-wp-ids/`.

## 3. Decisions in flight  (→ Decision; status: accepted)
- **D1 (accepted, ADR-001): single id-matcher, defined once.** Choice: one
  regex + `is_wp_id`/`wp_nnn_suffix` readers, all 5 sites consume it. Rejected:
  widen each `startswith` independently (drift — the #60/EP-03 failure mode); a
  regex-per-concern (still multi-source); a full `WPId` dataclass (YAGNI —
  callers only need predicate + suffix).
- **D2 (accepted, ADR-002): strictly additive, one-release back-compat +
  supersede parked.** Choice: new ids prefixed, legacy bare stay parseable, no
  migration, removal deferred to tracked follow-up; `canonicalise-cross-wp-ids`
  (empty stub) superseded/retired. Rejected: migrate in-flight INDEX files (big
  blast radius, zero benefit); mint THIS change's WPs prefixed (would be
  invisible to run-all — chicken-and-egg); drop legacy now (breaks in-flight
  changes); resurrect the parked effort (no design to continue).
- **D3 (accepted): the `wp_nnn_suffix` extractor is load-bearing for branch
  cleanliness.** Found in design (not recon): `removeprefix("wp-")` is a NO-OP
  on a lowercased prefixed id (`ch-5dmb1n-wp-001`), so without the shared
  extractor the branch leaks a doubled id `wp/{scope}/wp-ch-5dmb1n-wp-001-...`.
  The extractor strips the handle prefix, keeping the #283 per-change branch
  scheme clean. Pinned by a branch-resolution test.

## 4. Open questions / unknowns
- WP-003 retirement form of the parked `canonicalise-cross-wp-ids` stub:
  hard-delete the dir vs leave a `SUPERSEDED.md` — executor confirms against
  repo convention. Not load-bearing for the design.

## 5. Rejected so far  (→ Decision.rejected_alternatives)
- Per-site independent widening — rejected (matcher/validator drift, EP-03).
- Migrating in-flight INDEX ids — rejected (blast radius, no benefit).
- Prefixing this change's own WP ids — rejected (chicken-and-egg: invisible to
  the very run-all loop that executes them; this change's WPs are bare WP-001/2/3).
- `WPId` dataclass / full id parse — rejected (YAGNI; predicate + suffix suffice).

## NFRs surfaced
- **NFR-1 (back-compat invariant, MUST):** the parser MUST return both a
  prefixed and a legacy bare row from the SAME parse for one release — else
  in-flight changes carrying committed bare ids break mid-run. Verified by the
  load-bearing parametrised both-shapes regression guard (WP-001).
- **NFR-2 (single-source-of-truth, MUST, EP-03):** exactly one id-matcher
  definition; zero residual open-coded `startswith("WP-")`/`removeprefix("wp-")`
  for WP ids outside it. Verified by a grep-clean hygiene check in WP-001 Blue.
- **NFR-3 (#283 preservation, MUST):** NNN sequencing and per-change branch
  namespacing are byte-for-byte unchanged; only the rendered label gains a
  prefix and the NNN extraction routes through the shared extractor. Verified by
  retained branch-resolution + sequencing tests staying green.

## 6. Working log  (append-only)
- 2026-06-10T06:25:01Z — Working Set created.
- 2026-06-10T06:26:55Z — Recon: seam mapped. Key back-compat point = parse_index_md row-filter startswith('WP-') would drop prefixed ids. Branch refs already per-change (#283); this extends the id label only.
- 2026-06-10T06:29:04Z — Spec (standard, inferred from brief): strictly additive (new ids prefixed, legacy bare stay readable), one-release back-compat, removal deferred to future change, supersede parked canonicalise-cross-wp-ids. Single-source id matcher per EP-03.
- 2026-06-10T07:40:00Z — Design pass complete. TDD + ADR-001 (single matcher) + ADR-002 (additive back-compat + supersession) + 3 WPs + INDEX on disk at .architecture/extend-unique-wp-ids/. Tier S. Seam confirmed = 5 sites (4 in _wpxlib.py + 1 in _p_ver_rubric.py:111 — the 5th found in design, not recon). New finding: wp_nnn_suffix extractor is load-bearing for branch cleanliness (removeprefix("wp-") no-ops on prefixed ids → doubled-prefix branch leak). INDEX passes validate_wp_index_header + parse_index_md; all 3 WP frontmatter valid. Parked effort = empty stub (only a stray .executor journal), no design to fold — superseded.
- 2026-06-10T08:33:12Z — Implemented + merged to change branch (train-2026-06-10T081954Z): 3 WPs shipped, CI green, gate review PASS (no critical/concern). Found+fixed blocking #283 follow-up: branch-ci didn't trigger on wp/** namespace. 3 follow-ups captured: drop legacy back-compat, executor branch-mint alignment, regex \Z anchor.
