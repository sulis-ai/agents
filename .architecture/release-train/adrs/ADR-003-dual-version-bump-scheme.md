---
id: ADR-003
title: The bump touches three version values at one tier; tag = v<marketplace metadata.version>
status: accepted
change_id: 01KSQNPBPN7W74QVAZ25F79RNH
date: 2026-05-28
---

# ADR-003 — Dual-version bump scheme + tag derivation

## Decision

A release bump applies the cumulative tier to **three version values in
lockstep**, then tags from the marketplace umbrella version:

| # | File | JSON path | Series (today) |
|---|---|---|---|
| 1 | `plugins/sulis/.claude-plugin/plugin.json` | `.version` | sulis plugin — `0.77.x` |
| 2 | `.claude-plugin/marketplace.json` | `.plugins[] | select(.name=="sulis").version` | sulis entry — `0.77.x` (same as #1) |
| 3 | `.claude-plugin/marketplace.json` | `.metadata.version` | marketplace umbrella — `1.122.x` |

- The **same tier** is applied to all three (a `minor` bump moves
  `0.77.0 → 0.78.0` for #1 and #2, and `1.122.0 → 1.123.0` for #3).
- The git **tag** is **`v<metadata.version>`** — e.g. `v1.123.0`. (Confirmed
  from repo state: tags are `v1.119.0 … v1.122.0`; there is **no** `v0.77.0`
  tag. The umbrella version is the tagged one.)
- The **CHANGELOG header** uses the **plugin** version: `## v0.78.0 — <date>`.
- Other plugins in the marketplace (e.g. `investor-coach`) are **not** bumped by
  this change's releases — only the sulis entry + the umbrella metadata move.
  (Confirmed: investor-coach stayed `0.6.0` across the last four releases.)

## Context

honest-claude's release-on-merge workflow bumps a **single** version value
(`plugin.json` + the matching marketplace entry, one series). Sulis's
marketplace carries an **umbrella `metadata.version`** in addition to the
per-plugin version, and the tag derives from the umbrella. The spec called this
out ("note the dual-version scheme … the tag is `v<marketplace-version>`"), but
the *exact* set of values and which one the tag uses had to be reconciled
against the live repo. Getting this wrong is the single most likely way the GHA
ships a half-bump or a mis-named tag.

## Evidence (from repo state at the time of writing)

```
v1.122.0 -> metadata.version=1.122.0  sulis(marketplace)=0.77.0  sulis(plugin)=0.77.0
v1.121.0 -> metadata.version=1.121.0  sulis(marketplace)=0.76.0  sulis(plugin)=0.76.0
v1.120.0 -> metadata.version=1.120.0  sulis(marketplace)=0.75.0  sulis(plugin)=0.75.0
v1.119.0 -> metadata.version=1.119.0  sulis(marketplace)=0.74.0  sulis(plugin)=0.74.0
investor-coach stayed 0.6.0 throughout.
```

Both series increment by the same tier each release; the umbrella leads by a
major but tracks the same minor/patch deltas.

## Alternatives considered

1. **Bump only the plugin + sulis entry, leave metadata (rejected).** *Rejected
   because* the tag derives from `metadata.version`; leaving it unbumped would
   produce a duplicate/colliding tag and break `release-prod.yml`'s
   tag-triggered GitHub Release.

2. **Tag from the plugin version (`v0.78.0`) (rejected).** *Rejected because*
   the established convention — confirmed by every existing tag — is
   `v<metadata.version>`. Changing the tag series would orphan the entire tag
   history and break consumers + `release-prod.yml`'s `tags: ['v*.*.*']`
   trigger. Convention Preference: keep the older, established series.

3. **Bump all three at one tier, tag from metadata (CHOSEN).** Matches the exact
   observed history. The GHA does three `jq` edits + one tag.

## Consequences

- **Positive:** the bump is fully specified and verifiable; the post-bump
  verification step (WP-003) re-reads **all three** values and fails if any did
  not move — a half-bump can never reach a tag.
- **Cost:** three edits instead of one; the VERSION_DRIFT guard must check that
  #1 == #2 *before* bumping (a prior partial bump is the usual drift cause).
- **`next_version` in `_changeset.py`** is series-agnostic — it takes a current
  version string + tier and returns the next, so the same function bumps both
  the `0.x.y` and `1.x.y` series. The GHA applies it three times (or the
  identical bash, per ADR-004).

## Related

- ADR-004 (the GHA that applies this), WP-001 (`next_version`), WP-003 (the
  three `jq` edits + post-bump verification + tag).
