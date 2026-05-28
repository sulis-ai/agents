# `.changesets/` — the release-train contract

This directory is the **producer/consumer contract** of the changeset-based
release train. Every change that touches the marketplace writes one small YAML
file here recording its *intent and tier* — never a version number. Versions are
computed at release time, by one authority, from the accumulated changesets.

This README **is** the contract. The deterministic helper that reads and writes
these files lives at `plugins/sulis/scripts/_changeset.py`; its unit tests parse
the worked example below through the real reader, so this document and the code
**cannot drift** (ADR-005). If you change the shape here, the helper's tests
fail until the code agrees.

## Why changesets

`/sulis:change ship` lands a change on `dev`. It does **not** bump a version —
bumping every ship would collide the moment two changes target the same next
version (issues #64 vs #52). Instead, each ship drops a changeset; the changesets
accumulate on `dev`; a single release step reads them all and bumps once.

This decouples **integration** (land on `dev`) from **release** (bump + tag) —
the root fix for #66.

## The YAML shape

Each changeset is a flat YAML file with six fields:

```yaml
change_id: 01KSQNPBPN7W74QVAZ25F79RNH   # ULID of the parent change
primitive: create                        # the change primitive (22-primitive vocabulary)
tier: minor                              # patch | minor | major — computed, overridable
touches_plugin: true                     # true when the change touches plugins/sulis/**
summary: |                               # founder-readable; assembled into the CHANGELOG
  Changeset-based release train: ship drops a changeset, the GHA bumps on merge.
created_at: 2026-05-28T17:30:00Z         # UTC ISO-8601 timestamp
```

| Field | Type | Meaning |
|---|---|---|
| `change_id` | string (ULID) | The parent change this changeset belongs to. |
| `primitive` | string | The change primitive declared at `start` (see `references/change-primitives.md`). |
| `tier` | `patch` \| `minor` \| `major` | The release tier. Computed from the primitive (ADR-002), but **authoritative** — edit it on `dev` to override the computed value. |
| `touches_plugin` | bool | `true` when the change touches `plugins/sulis/**`. Admin/docs-only changes (`false`, tier `None`) write **no** changeset at all. |
| `summary` | block string | One or more founder-readable lines. Assembled into the CHANGELOG entry at release. |
| `created_at` | string | UTC ISO-8601 (`YYYY-MM-DDTHH:MM:SSZ`). |

## The filename (triple-key, collision-proof)

```
{primitive}-{slug}-{datetimeZ}.yaml
```

e.g. `create-release-train-20260528T173000Z.yaml`. The triple key — primitive +
slug + compact UTC datetime (`20260528T173000Z`) — makes two parallel changes
writing the same path effectively impossible. The slug is sanitised (lowercased,
non-alphanumeric runs collapsed to `-`, edges trimmed).

## The tier is computed from the primitive (ADR-002)

`_changeset.tier_for_primitive(primitive)` maps the change's already-declared
primitive to a tier — no second judgment call at ship time. The map covers
**all 22 change primitives** (`references/change-primitives.md`) plus the five
Conventional-Commits types that also reach this function, so no code-altering
change type silently resolves to `None` and ships with no release (the #66
invisibility). This table is the authority `_PRIMITIVE_TIER` in the code mirrors;
`test_readme_tier_table_matches_primitive_tier_map` asserts they cannot drift.

| Primitive(s) | Group | Tier |
|---|---|---|
| `fix`, `chore`, `refactor`, `docs` | Conventional Commits | `patch` |
| `move`, `inline`, `merge`, `decompose`, `abstract` | REORGANISE | `patch` |
| `deprecate` | CONTRACT | `patch` |
| `test`, `document` | REINFORCE | `patch` |
| `feat` | Conventional Commits | `minor` |
| `create`, `extend`, `compose`, `reuse`, `generate` | EXPAND | `minor` |
| `strangle`, `wrap`, `replace` | SUBSTITUTE | `minor` |
| `delete` | CONTRACT | `minor` |
| `harden`, `instrument`, `secure`, `gate` | REINFORCE | `minor` |
| anything flagged **breaking** | — | `major` |
| `admin`, `docs-only`, or any unknown token | — | `None` → **no changeset written** |

**patch** covers behaviour-preserving moves and additions with no new shipping
surface (the REORGANISE group, `deprecate`, and the `test`/`document` REINFORCE
primitives). **minor** covers everything that adds or changes an observable
surface or behaviour (the EXPAND and SUBSTITUTE groups, `delete`, and the
behaviour-adding REINFORCE primitives `harden`/`instrument`/`secure`/`gate`).
**major** is reached only via the per-changeset **breaking** override.

The written `tier:` field is authoritative: for the rare case the default is
wrong (a `refactor` that is secretly breaking, or a `secure` change that is
actually patch-level), edit `tier:` on `dev` before the release PR. `None` is
meaningful, not an error — `admin`/`docs-only` changes don't touch
`plugins/sulis/**`, so they don't affect what consumers install and write
nothing.

## The lifecycle

1. **Write on ship.** `/sulis:change ship` (WP-002) computes the tier from the
   primitive and calls `_changeset.write_changeset(...)`, dropping one
   `.changesets/*.yaml` before the merge to `dev`. If the tier is `None`, it
   writes nothing.
2. **Accumulate on `dev`.** Changesets pile up as changes land. Each carries its
   own tier and summary.
3. **Read at release.** `/sulis:release-train` (WP-004) reads every changeset
   (`read_changesets`), computes the cumulative tier (`cumulative_tier` — the
   SemVer max), and opens a reviewed `dev → main` PR with the computed version
   and an assembled CHANGELOG preview. It is **read-only** — it never bumps.
4. **Bump on merge to `main`.** A single bot-driven GitHub Action
   (`release-on-merge.yml`, WP-003) is the **one** bump authority. It reads the
   changesets, applies `next_version` at the cumulative tier to all three
   version values (the plugin, the marketplace sulis entry, and the marketplace
   umbrella — ADR-003), assembles the CHANGELOG entry, **deletes the consumed
   changesets**, commits as `github-actions[bot]`, tags
   `v<marketplace metadata.version>`, and pushes.

## Rules for re-implementers (the cross-language parser grammar)

The WP-003 bash GitHub Action re-reads this exact format **without a YAML
library** (ADR-004), so it must parse it identically to the Python reader
(`_changeset.py`'s `_parse_changeset` / `_strip_inline_comment` /
`_coerce_scalar`). These are the rules that reader implements — they ARE the
format spec; a re-implementer conforming to them parses every changeset the
writer produces:

1. **Top-level fields are `key: value` on one line.** Split on the **first**
   `:`; trim whitespace around the key and the value. Lines with no `:` are
   ignored. Fully blank lines and lines whose first non-blank character is `#`
   are ignored (comment/blank tolerance for hand-edited files).

2. **Block scalars (`summary: |`).** When a value is exactly `|`, the field is a
   literal block scalar:
   - **Unit of indent is 2 spaces.** Each block line is the source line with its
     leading 2 spaces removed.
   - **The block ends** at the first line that is *not* 2-space-indented — i.e.
     the next top-level `key:` (or end of file).
   - **Internal blank lines are preserved** (they render as empty lines inside
     the block).
   - **Trailing blank lines are stripped** (a blank line immediately before the
     next top-level key does not become part of the value).

3. **Quoting.** A scalar value may be wrapped in matching single (`'…'`) or
   double (`"…"`) quotes; strip the one matching outer pair. (Block-scalar lines
   are never quote-stripped.)

4. **Inline comments.** Outside quotes, a `#` that is at column 0 **or** preceded
   by whitespace starts a comment — drop it and everything after. A `#` **inside**
   a quoted value is preserved (`summary: "tag #release"` keeps the `#`). Comment
   stripping applies to scalar values only, never to block-scalar lines.

5. **Booleans.** After comment-stripping and unquoting, the bare tokens `true`
   and `false` coerce to boolean; **every other value is a string** (an empty
   value coerces to the empty string, not null).

6. **Injection rule (the writer's guarantee, FIX 2).** The writer rejects a
   newline (`\n`/`\r`) in `change_id`, `primitive`, or `tier`, and rejects a `:`
   in `change_id` or `primitive`. So a re-implementer may treat each of those as
   a **single safe line** — no forged extra `tier:`/`primitive:` line can be
   smuggled in via a crafted value. (Do **not** rely on the Python reader's
   last-value-wins behaviour: a naive first-match reader such as
   `grep -m1 '^tier:'` is safe *only because* the writer enforces this rule.)

## Notes

- **No YAML library required.** The format is flat enough that the GHA reads it
  in bash (ADR-004); `_changeset.py` parses/emits it with a tiny inline
  reader/writer, the same no-pyyaml convention the rest of `plugins/sulis/scripts/`
  uses. Keep the shape simple and hand-editable.
- **`next_version` is series-agnostic** (ADR-003): the same function bumps the
  `0.x.y` plugin series and the `1.x.y` marketplace series. The GHA applies it
  three times, once per version value, at one tier.
