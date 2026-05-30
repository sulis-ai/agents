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

  - **ID strategy.** Reuse the ADR's `change_id` frontmatter field (so the
    Decision's id is `dna:decision:{change_id}`, giving natural traceability
    from a Change to the Decisions it produced). Fall back to a fresh ULID
    when `change_id` is absent.
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


def _resolve_decision_id(frontmatter: dict) -> str:
    """Compose the Decision's `@id`.

    Uses the ADR's `change_id` if present (so a Decision's id is
    deterministically tied to the Change that produced it); generates a
    fresh ULID otherwise. Both shapes pass the schema's id pattern.
    """
    change_id = frontmatter.get("change_id")
    if isinstance(change_id, str) and change_id:
        return f"dna:decision:{change_id}"
    return f"dna:decision:{generate_change_ulid()}"


# ─── public API ───────────────────────────────────────────────────────────


def compose_decision_from_adr(adr_text: str) -> dict:
    """Compose a Decision entity dict from ADR markdown.

    Pure transformation: text in, dict out. No I/O, no validation —
    validation happens at the repository boundary on save (which is where
    rejection semantics live).

    The returned dict has the shape the vendored `decision.schema.json`
    expects. Optional fields (`context`, `consequences`, `options_considered`)
    are omitted when the source ADR doesn't contain them rather than
    emitted-empty, so the schema's `unevaluatedProperties:false` doesn't
    reject a sparse-but-valid input.
    """
    frontmatter, body = parse_frontmatter(adr_text)

    decision: dict = {
        "id": _resolve_decision_id(frontmatter),
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
) -> dict:
    """Read an ADR markdown file and emit its Decision entity through `repo`.

    Returns the persisted Decision dict (caller can use it for cross-
    referencing).

    Raises:
        EntityValidationError: if the composed entity fails schema
            validation. The repository never persists an invalid instance.
    """
    adr_text = Path(adr_path).read_text(encoding="utf-8")
    decision = compose_decision_from_adr(adr_text)
    repo.save("decision", decision)
    return decision
