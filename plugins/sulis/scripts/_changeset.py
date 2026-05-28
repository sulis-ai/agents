"""Changeset data model + the deterministic core of the release train (WP-001).

This is the **keystone** of the changeset-based release train (TDD
`release-train`, ADR-001..006). It is a pure stdlib leaf module — it imports
nothing from the rest of the toolchain and lives alongside `_wpxlib.py` in
`plugins/sulis/scripts/`. Its public surface IS the producer/consumer contract
documented in `.changesets/README.md`:

  - `tier_for_primitive` — deterministic SemVer tier from the change primitive
    (ADR-002). The mapping is a literal dict covering ALL 22 change primitives
    in `references/change-primitives.md` (the `CHANGE_PRIMITIVES` constant is
    the single source of truth for that vocabulary, and `test_changeset.py`
    asserts every one resolves to a non-None tier). None is returned only for
    genuinely-unmapped/admin tokens (`admin`, `docs-only`, unknown strings).
  - `cumulative_tier`    — the SemVer max over a batch of changesets.
  - `next_version`       — series-agnostic SemVer bump; serves BOTH the 0.x.y
    plugin series and the 1.x.y marketplace series (ADR-003).
  - `changeset_filename` — the triple-key, collision-proof filename.
  - `write_changeset` / `read_changesets` — the YAML round-trip.
  - `read_changeset_examples` — parses the worked example out of the contract
    doc so the doc and the code cannot drift (ADR-005).

**YAML approach.** The changeset YAML is a flat file with six fields, one of
which (`summary`) is a `|` block scalar. We parse and emit it with a tiny inline
reader/writer — the SAME "no-pyyaml" convention `_wpxlib.read_overrides` /
`write_overrides` use — so the WP-003 GitHub Action can read the identical
format in bash (ADR-004) without a YAML library in CI.

Producers/consumers: the ship flow (WP-002) calls `write_changeset`; the
`release-on-merge.yml` GHA (WP-003) and the `/sulis:release-train` skill
(WP-004) read `.changesets/*.yaml` per this contract.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

Tier = Literal["patch", "minor", "major"]

# Single source of truth for tier precedence: patch < minor < major. Shared by
# `tier_for_primitive` (to name a tier) and `cumulative_tier` (to take the max).
# Index in this tuple IS the SemVer severity rank.
_TIER_ORDER: tuple[Tier, ...] = ("patch", "minor", "major")

# The canonical 22 change primitives (`references/change-primitives.md`), the
# single source of truth for the vocabulary `_PRIMITIVE_TIER` must cover. Listed
# by MECE group so a reader can see the coverage at a glance; the order matches
# the reference. `test_changeset.py` cross-checks this constant against its own
# copy of the 22, so a primitive added to the vocabulary fails loudly here until
# it is given a tier below.
CHANGE_PRIMITIVES: tuple[str, ...] = (
    # EXPAND — introduce new code or new usage
    "reuse", "compose", "extend", "generate", "create",
    # REORGANISE — restructure, behaviour-preserving
    "move", "refactor", "inline", "merge", "decompose", "abstract",
    # SUBSTITUTE — swap implementation behind a preserved surface
    "replace", "strangle", "wrap",
    # CONTRACT — remove behaviour
    "deprecate", "delete",
    # REINFORCE — add a cross-cutting concern
    "test", "instrument", "secure", "harden", "gate", "document",
)

# Primitive → tier (ADR-002). Covers ALL 22 change primitives in
# `CHANGE_PRIMITIVES` across the five MECE groups (EXPAND / REORGANISE /
# SUBSTITUTE / CONTRACT / REINFORCE) — the founder's "cover all 22" decision, so
# no code-altering change type silently resolves to None and ships with no
# release (the #66 invisibility). Conventional-Commits types (`fix`, `chore`,
# `refactor`, `docs`, `feat`) sit alongside the change-primitive names because
# both vocabularies reach this function (the ship flow declares a primitive;
# some callers pass a CC type). The written `tier:` field stays authoritative —
# the per-changeset override on `dev` is the escape hatch when a default is
# wrong (ADR-002). A token NOT in this map → None (see `tier_for_primitive`):
# admin / docs-only / unknown strings touch nothing consumers install.
_PRIMITIVE_TIER: dict[str, Tier] = {
    # patch — behaviour-preserving / no new shipping surface
    # Conventional-Commits types:
    "fix": "patch",
    "chore": "patch",
    "refactor": "patch",
    "docs": "patch",
    # REORGANISE — behaviour-preserving restructuring:
    "move": "patch",
    "inline": "patch",
    "merge": "patch",
    "decompose": "patch",
    "abstract": "patch",
    # CONTRACT-deprecate — marks for removal; behaviour preserved:
    "deprecate": "patch",
    # REINFORCE — no shipping-surface / runtime change:
    "test": "patch",
    "document": "patch",
    # minor — new or changed surface / behaviour
    # Conventional-Commits:
    "feat": "minor",
    # EXPAND — adds surface / behaviour:
    "create": "minor",
    "extend": "minor",
    "compose": "minor",
    "reuse": "minor",
    "generate": "minor",
    # SUBSTITUTE — swaps implementation; observable behaviour may change:
    "strangle": "minor",
    "wrap": "minor",
    "replace": "minor",
    # CONTRACT-delete — removes behaviour consumers may depend on:
    "delete": "minor",
    # REINFORCE — adds an observable behaviour / surface:
    "harden": "minor",
    "instrument": "minor",
    "secure": "minor",
    "gate": "minor",
}


def tier_for_primitive(primitive: str, *, breaking: bool = False) -> Tier | None:
    """Deterministic release tier from the change primitive (ADR-002).

    `breaking=True` → "major" regardless of the primitive. An unknown primitive
    — including `admin` / `docs-only` (changes outside `plugins/sulis/**`) —
    returns None, meaning the caller writes NO changeset. None is meaningful,
    not an error: admin/docs-only changes don't affect what consumers install.
    """
    if breaking:
        return "major"
    return _PRIMITIVE_TIER.get(primitive)


def cumulative_tier(changesets: list[dict]) -> Tier | None:
    """The SemVer max over a batch's tiers (major > minor > patch).

    An empty list → None ("nothing to release"). Changesets without a usable
    `tier` field are ignored; if none carry a tier, the result is None.
    """
    ranks = [
        _TIER_ORDER.index(c["tier"])
        for c in changesets
        if c.get("tier") in _TIER_ORDER
    ]
    if not ranks:
        return None
    return _TIER_ORDER[max(ranks)]


def next_version(current: str, tier: Tier | None) -> str:
    """Apply `tier` to a dotted SemVer string. Series-agnostic.

    Works identically for the 0.77.0 plugin series and the 1.122.0 marketplace
    series (ADR-003) — the GHA applies it three times, once per version value.
    `tier=None` → `current` unchanged. patch: x.y.(z+1); minor: x.(y+1).0;
    major: (x+1).0.0.

    `current` MUST be a strict dotted triple of integers (`x.y.z`). A malformed
    string raises `ValueError` (too few/many parts → unpack error; a non-integer
    part → `int()` error): the version values come from the marketplace/plugin
    manifests, so a malformed one is a contract breach worth failing loudly on,
    not silently passing through.

    NOTE: the WP-003 GitHub Action mirrors this exact arithmetic in bash (the
    accepted Python/bash duplication of ADR-004) — keep the two in lockstep.
    """
    if tier is None:
        return current
    major, minor, patch = (int(part) for part in current.split("."))
    if tier == "patch":
        return f"{major}.{minor}.{patch + 1}"
    if tier == "minor":
        return f"{major}.{minor + 1}.0"
    # tier == "major"
    return f"{major + 1}.0.0"


def changeset_filename(primitive: str, slug: str, created_at: datetime) -> str:
    """Triple-key, collision-proof changeset filename.

    `{primitive}-{slug}-{datetimeZ}.yaml`, where datetimeZ is the compact UTC
    ISO-8601 form (e.g. `20260528T173000Z`). The slug is sanitised (lowercased,
    non-alnum runs → single '-', trimmed). The triple key (primitive + slug +
    UTC datetime) makes collisions across parallel changes effectively
    impossible — the #64-vs-#52 conflict class is structurally gone.
    """
    stamp = _compact_utc(created_at)
    return f"{_sanitise_slug(primitive)}-{_sanitise_slug(slug)}-{stamp}.yaml"


def write_changeset(
    changesets_dir: Path,
    *,
    change_id: str,
    primitive: str,
    tier: Tier,
    touches_plugin: bool,
    summary: str,
    created_at: datetime | None = None,
    slug: str | None = None,
) -> Path:
    """Write one changeset YAML; return the path written.

    Creates `changesets_dir` if absent. The filename is the collision-proof
    triple key (`changeset_filename`). `created_at` defaults to now (UTC).
    `slug` is the human filename component — the change's own slug (e.g.
    `release-train`); when omitted it falls back to the `change_id` so the
    helper is self-contained for direct callers. WP-002 passes the human slug.
    """
    when = created_at or datetime.now(timezone.utc)
    changesets_dir.mkdir(parents=True, exist_ok=True)
    name = changeset_filename(primitive, slug=slug or change_id, created_at=when)
    path = changesets_dir / name
    path.write_text(
        _dump_changeset(
            change_id=change_id,
            primitive=primitive,
            tier=tier,
            touches_plugin=touches_plugin,
            summary=summary,
            created_at=_iso_utc(when),
        ),
        encoding="utf-8",
    )
    return path


def read_changesets(changesets_dir: Path) -> list[dict]:
    """Read every `*.yaml` in the dir into dicts.

    Ignores non-`.yaml` files (README.md, scratch .txt). A missing dir → [].
    Order is sorted by filename for determinism (the triple-key filename sorts
    primitive-then-slug-then-time).
    """
    if not changesets_dir.is_dir():
        return []
    records = []
    for path in sorted(changesets_dir.glob("*.yaml")):
        records.append(_parse_changeset(path.read_text(encoding="utf-8")))
    return records


def read_changeset_examples(readme: Path) -> list[dict]:
    """Parse the worked-example changeset YAML out of `.changesets/README.md`.

    Every fenced ```yaml block in the contract doc that parses to a dict
    carrying a `change_id` is treated as a worked example and parsed through
    the SAME reader the GHA/skill use. This is the executable-conformance check
    of ADR-005: the documented contract and the code cannot drift.
    """
    text = readme.read_text(encoding="utf-8")
    examples = []
    for block in _YAML_FENCE_RE.findall(text):
        record = _parse_changeset(block)
        if record.get("change_id"):
            examples.append(record)
    return examples


# ─── internals — the tiny no-pyyaml YAML round-trip ────────────────────────


_YAML_FENCE_RE = re.compile(r"```ya?ml\n(.*?)```", re.DOTALL)
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def _sanitise_slug(value: str) -> str:
    """Lowercase, collapse non-alnum runs to a single '-', trim edge dashes."""
    return _NON_ALNUM_RE.sub("-", value.lower()).strip("-")


def _compact_utc(value: datetime) -> str:
    """Compact UTC ISO-8601 stamp, e.g. 20260528T173000Z."""
    return _as_utc(value).strftime("%Y%m%dT%H%M%SZ")


def _iso_utc(value: datetime) -> str:
    """Full UTC ISO-8601 stamp, e.g. 2026-05-28T17:30:00Z."""
    return _as_utc(value).strftime("%Y-%m-%dT%H:%M:%SZ")


def _as_utc(value: datetime) -> datetime:
    """Normalise to UTC; treat a naive datetime as already-UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _reject_unsafe_scalar(field_name: str, value: str, *, forbid_colon: bool) -> None:
    """Guard a raw-interpolated scalar against YAML line injection (FIX 2).

    `change_id`, `primitive`, and `tier` are interpolated raw into the YAML
    (`f"tier: {tier}"`). A newline (`\\n` or `\\r`) in any of them forges an
    extra top-level line — e.g. a fake `tier: major` ahead of the real one. The
    Python reader is last-value-wins (immune), but the WP-003 bash GHA re-reads
    this format and a naive first-match reader (`grep -m1 '^tier:'`) would trust
    the forged value. Reject newlines for all three; additionally reject `:` in
    `change_id`/`primitive` (a ULID is `[0-9A-Z]`, a primitive is a single
    lowercase token — neither legitimately contains a colon, which could split a
    line into a forged key/value). `summary` is a `|` block scalar (every line
    forced to a 2-space indent) and cannot escape to a top-level key, so it is
    NOT passed through this guard. Raises `ValueError` naming the offending
    field.
    """
    if "\n" in value or "\r" in value:
        raise ValueError(f"{field_name} must not contain a newline: {value!r}")
    if forbid_colon and ":" in value:
        raise ValueError(f"{field_name} must not contain ':': {value!r}")


def _dump_changeset(
    *,
    change_id: str,
    primitive: str,
    tier: Tier,
    touches_plugin: bool,
    summary: str,
    created_at: str,
) -> str:
    """Emit the flat changeset YAML (the contract shape).

    `summary` is written as a `|` literal block scalar (founder-readable,
    possibly multi-line). All other fields are simple scalars. Booleans render
    lowercase (`true`/`false`) to match YAML + the bash reader's expectation.

    The raw-interpolated scalar fields (`change_id`, `primitive`, `tier`) are
    guarded against newline/colon injection first (`_reject_unsafe_scalar`,
    FIX 2) so a crafted value cannot forge an extra YAML line a first-match bash
    reader would trust.
    """
    _reject_unsafe_scalar("change_id", change_id, forbid_colon=True)
    _reject_unsafe_scalar("primitive", primitive, forbid_colon=True)
    _reject_unsafe_scalar("tier", tier, forbid_colon=False)
    lines = [
        f"change_id: {change_id}",
        f"primitive: {primitive}",
        f"tier: {tier}",
        f"touches_plugin: {'true' if touches_plugin else 'false'}",
        "summary: |",
    ]
    for summary_line in summary.splitlines() or [""]:
        lines.append(f"  {summary_line}")
    lines.append(f"created_at: {created_at}")
    return "\n".join(lines) + "\n"


def _parse_changeset(text: str) -> dict:
    """Parse a flat changeset YAML into a dict (the no-pyyaml reader).

    Handles simple `key: value` scalars, `true`/`false` booleans, and a
    `summary: |` literal block scalar (subsequent indented lines, dedented).
    Mirrors `_dump_changeset`; the two are the single round-trip the GHA reader
    re-implements in bash.
    """
    record: dict = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()
        i += 1
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, rest = line.partition(":")
        key = key.strip()
        rest = rest.strip()
        if rest == "|":
            # Literal block scalar: consume subsequent more-indented lines.
            block_lines: list[str] = []
            while i < len(lines) and (lines[i].startswith("  ") or not lines[i].strip()):
                if lines[i].strip() == "" and (
                    i + 1 >= len(lines) or not lines[i + 1].startswith("  ")
                ):
                    # trailing blank line before the next top-level key
                    break
                block_lines.append(lines[i][2:] if lines[i].startswith("  ") else "")
                i += 1
            record[key] = "\n".join(block_lines).rstrip("\n")
        else:
            record[key] = _coerce_scalar(rest)
    return record


def _coerce_scalar(value: str):
    """Coerce a YAML scalar: true/false → bool; everything else → str.

    A trailing inline `# comment` is stripped first — the contract doc annotates
    its worked example inline (`tier: minor  # patch | minor | major`), and the
    reader must see the bare value. None of the six scalar fields (ULID,
    primitive, tier, bool, ISO timestamp) legitimately contains `#`, so this is
    safe; the `summary` block scalar is parsed separately and never reaches here.
    """
    text = _strip_inline_comment(value)
    unquoted = text.strip().strip("'\"")
    if unquoted == "true":
        return True
    if unquoted == "false":
        return False
    return unquoted


def _strip_inline_comment(value: str) -> str:
    """Drop a trailing ` # comment` from a scalar value, preserving a quoted
    `#`. A `#` only starts a comment when preceded by whitespace (or at the
    start) and outside quotes."""
    in_single = in_double = False
    for idx, ch in enumerate(value):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            if idx == 0 or value[idx - 1].isspace():
                return value[:idx]
    return value
