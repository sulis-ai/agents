"""ADR → Decision-entity transformation + persistence helper.

When `/sulis:draft-architecture` writes an ADR markdown file, this module
emits the corresponding **Decision** entity through the EntityRepository
port (validated against the vendored compiled JSON Schema from the
plugins-repo dna-runner output).

The two halves are deliberate:
  - `compose_decision_from_adr(text)` is **pure** — text in, dict out. No I/O,
    no validation. Easy to unit-test the transformation in isolation.
  - `emit_decision_from_adr(path, repo)` is the orchestrator — reads the
    file, composes, persists via the port (which validates on save).

Decisions baked in (per founder confirmation, 2026-05-30):

  - **ID strategy (WP-012, FR-17).** Each emitted Decision gets a freshly-
    minted ULID `@id` (`dna:decision:{ulid}`). The earlier strategy reused the
    ADR's `change_id` frontmatter (`dna:decision:{change_id}`), but a change
    that produces more than one decision then collapsed every decision onto a
    single `@id` — the second emission silently overwrote the first on disk.
    A fresh ULID per emission guarantees distinctness; change→decision
    traceability moves off the primary id (a `prov:wasDerivedFrom` relation,
    deferred to the SPARQL runtime — see below — rather than overloading the
    storage identity).
  - **Kind discriminator (WP-012, ADR-006).** A Decision carries
    `kind ∈ {adr, bdr}` — a technical architecture decision (ADR) vs a
    business decision (BDR). It is a discriminator on the existing decision
    entity, not a new entity type. The caller supplies the kind (the CLI's
    `--kind` / `--from-bdr`); absent, it defaults to `adr`, so existing
    `decision/*.jsonld` need no rewrite (§9.1).
  - **Status → state translation.** ADR frontmatter has `status: accepted`
    (old marketplace vocabulary, predating the two-lifecycle model). The
    Decision entity wants `state: accepted` (business state) + a separate
    `sys_status: active` (storage lifecycle). The translation happens here,
    at the emitter boundary — the ADR convention doesn't change.
  - **Section extraction.** Parse the body for `## Context`, `## Decision`,
    `## Consequences`, and `## Options Considered` (with the
    `Alternatives considered` synonym — real ADRs in this repo use both).
    Tolerant of multi-line bullets and numbered lists.
  - **`sys_status`** is always `"active"` on emission. Storage lifecycle
    transitions (archive / delete / purge) happen via the storage seam,
    not via the ADR writer.

Future work (intentionally deferred this slice):
  - `supersedes` cross-reference resolution (ADR-NNN → dna:decision:{ulid}
    of the existing entity it supersedes) needs a registry lookup; the
    schema field is optional so we omit it for now.
  - Mapping the ADR's `change_id` itself as a `prov:wasDerivedFrom` triple
    once the SPARQL runtime lands (C4b, deferred upstream).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

from _entity_repository import EntityRepository
from _wpxlib import generate_change_ulid, parse_frontmatter


# ─── section-extraction internals ─────────────────────────────────────────


# Bullet list item: `- foo`, `* foo`, `1. foo`, `  - foo` (indented OK).
_LIST_ITEM_RE: Final = re.compile(
    r"^\s*(?:[-*]|\d+\.)\s+(.+?)\s*$", re.MULTILINE
)


# Heading aliases for the "options" / "alternatives" section. Real ADRs in
# this repo use both forms; future ADRs may use either — accept both at the
# emitter boundary rather than imposing a single canonical heading on the
# template (which would be a documentation burden for marginal cleanliness).
_OPTIONS_HEADINGS: Final[tuple[str, ...]] = (
    "Options Considered",
    "Alternatives Considered",
    "Options",
    "Alternatives",
)


def _section_body(body: str, *heading_aliases: str) -> str | None:
    """Return the text under the first matching `## <heading>` section.

    Content runs from the line after the heading until the next `##` heading
    or end-of-string. Returns ``None`` if no matching heading is found.
    Aliases match case-insensitively.
    """
    pattern = (
        r"^##\s+(?:"
        + "|".join(re.escape(a) for a in heading_aliases)
        + r")\s*$\n(.*?)(?=^##\s+|\Z)"
    )
    match = re.search(pattern, body, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    if match is None:
        return None
    return match.group(1).strip() or None


def _flatten_prose(section: str) -> str:
    """Collapse whitespace in a prose section to a single string."""
    return re.sub(r"\s+", " ", section).strip()


def _extract_list_items(section: str) -> list[str]:
    """Extract list items (bullet or numbered) from a section.

    Multi-line items (continuation lines without a new bullet marker) are
    folded into the preceding item. A blank line ends an item.
    """
    items: list[str] = []
    current: list[str] = []

    def _flush() -> None:
        if current:
            items.append(_flatten_prose(" ".join(current)))
            current.clear()

    for line in section.splitlines():
        m = _LIST_ITEM_RE.match(line)
        if m:
            _flush()
            current.append(m.group(1))
        elif current:
            if line.strip() == "":
                _flush()
            else:
                current.append(line.strip())
    _flush()
    return [item for item in items if item]


_VALID_KINDS: Final[tuple[str, ...]] = ("adr", "bdr")
_DEFAULT_KIND: Final[str] = "adr"


def _mint_decision_id() -> str:
    """Mint a fresh, distinct Decision `@id` (`dna:decision:{ulid}`).

    The single id-minting site. Every emitted Decision gets its own freshly-
    generated ULID, so two decisions produced by the same change (which share
    a `change_id` in their source frontmatter) never collide on the same `@id`
    — the WP-012 collision fix. The ULID is the storage identity; change→
    decision traceability lives in a relation, not the primary id.
    """
    return f"dna:decision:{generate_change_ulid()}"


def _normalise_kind(kind: str | None) -> str:
    """Validate + default the decision-kind discriminator.

    Absent (`None`) reads as `adr` — the additive-optional migration default
    (§9.1), so existing decisions and callers that don't pass a kind are
    unaffected. An explicit out-of-enum value is a caller error.
    """
    if kind is None:
        return _DEFAULT_KIND
    if kind not in _VALID_KINDS:
        raise ValueError(
            f"kind must be one of {_VALID_KINDS}, got {kind!r}"
        )
    return kind


# ─── public API ───────────────────────────────────────────────────────────


def compose_decision_from_adr(adr_text: str, *, kind: str | None = None) -> dict:
    """Compose a Decision entity dict from ADR (or BDR) markdown.

    Pure transformation: text in, dict out (modulo the freshly-minted ULID id).
    No file I/O, no schema validation — validation happens at the repository
    boundary on save (which is where rejection semantics live).

    `kind` is the ADR/BDR discriminator (ADR-006): `"adr"` for a technical
    architecture decision (the default — absent reads as `adr`, §9.1), `"bdr"`
    for a business decision. The body shape is identical; the kind is supplied
    by the caller, not inferred from the markdown.

    The returned dict has the shape the vendored `decision.schema.json`
    expects. Optional fields (`context`, `consequences`, `options_considered`)
    are omitted when the source doesn't contain them rather than emitted-empty,
    so the schema's `unevaluatedProperties:false` doesn't reject a
    sparse-but-valid input.
    """
    frontmatter, body = parse_frontmatter(adr_text)

    decision: dict = {
        "id": _mint_decision_id(),
        "kind": _normalise_kind(kind),
        "title": str(frontmatter.get("title", "")),
        "state": str(frontmatter.get("status", "proposed")),
        "sys_status": "active",
    }

    context = _section_body(body, "Context")
    if context:
        decision["context"] = _flatten_prose(context)

    decision_section = _section_body(body, "Decision")
    if decision_section:
        decision["decision"] = _flatten_prose(decision_section)

    consequences = _section_body(body, "Consequences")
    if consequences:
        decision["consequences"] = _flatten_prose(consequences)

    options = _section_body(body, *_OPTIONS_HEADINGS)
    if options:
        items = _extract_list_items(options)
        if items:
            decision["options_considered"] = items

    return decision


def emit_decision_from_adr(
    adr_path: Path,
    repo: EntityRepository,
    *,
    kind: str | None = None,
) -> dict:
    """Read an ADR (or BDR) markdown file and emit its Decision through `repo`.

    `kind` is the ADR/BDR discriminator (ADR-006), threaded to
    `compose_decision_from_adr`; absent defaults to `adr`.

    Returns the persisted Decision dict (caller can use it for cross-
    referencing).

    Raises:
        EntityValidationError: if the composed entity fails schema
            validation. The repository never persists an invalid instance.
    """
    adr_text = Path(adr_path).read_text(encoding="utf-8")
    decision = compose_decision_from_adr(adr_text, kind=kind)
    repo.save("decision", decision)
    return decision
