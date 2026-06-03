"""SRD → Requirement-entity transformation + persistence helper.

Two compose paths share this module:

  - `compose_requirements_from_srd` — the document path: parses an SRD's
    `**FR-NN: ...**` markers into N Requirement dicts (described below).
  - `compose_requirement_from_idea` — the single-idea path (ADR-005): one
    Requirement dict built from explicit conversation fields, sourced from a
    **real** Opportunity ref the caller already emitted. This closes the
    synthetic-placeholder loop note (3) below documents: the from-idea path
    never synthesises a source, so it raises `ValueError` rather than emit a
    dangling/synthetic ref (the code-level "no orphan requirements" gate).

Both produce the same Requirement dict shape (same vendored schema) and reuse
the `_deterministic_ulid_from` + `_flatten` helpers unchanged; the from-idea
path uses a distinct id namespace (`requirement-from-idea:{seed}`) so the two
never collide on the same seed string.

Second worked entity emission (n=2 toward generalising the entity-emitter
skill). Pairs with `_decision_emission.py` (n=1 from CH-01KSWB). The shape
diverges in three interesting ways that inform the generalised skill:

  1. **Many entities per call.** A single SRD produces N Requirement
     entities (one per FR / NFR block). `_decision_emission` produced one
     per ADR file; this produces a list per call.
  2. **In-body markers, not frontmatter.** Field source is the
     `**FR-NN: Title**` headers + `**Acceptance criteria:**` markers in the
     prose body, not structured YAML frontmatter.
  3. **Cross-entity references with a synthetic placeholder.** The schema's
     `source` field requires a `dna:opportunity:{ulid}` or
     `dna:actor:{ulid}` reference. Opportunity emission doesn't exist yet
     (queued follow-on), so we emit a **deterministic synthetic Opportunity
     ULID** derived from the SRD path. Same SRD always produces the same
     synthetic id → idempotent + replaceable when real Opportunity emission
     lands. The placeholder nature is recorded in the entity's `rationale`
     so a downstream reader sees the marker.

Decisions baked in:
  - **Deterministic ids** via sha256(srd_path + ":" + fr_id) → 130-bit
    Crockford-base32 ULID. Re-emission is idempotent; ids survive moves.
  - **Defaults** for SRD-absent fields: `priority="must"`,
    `verification_method="test"`, `state="draft"`, `sys_status="active"`.
    Honest values; loud enough that an author overriding them sees the diff.
  - **NFR-NN blocks are extracted identically** to FR-NN. Both compile to
    the same `Requirement` entity (the ontology has one Requirement type;
    NFR is a shape-layer concern, not a separate spine entity).
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Final

from _entity_repository import EntityRepository


# Crockford base32 — same alphabet as ULID; no I/L/O/U.
_CROCKFORD_ALPHABET: Final[str] = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

# `**FR-NN: Title**` or `**NFR-NN: Title**` on a line of its own. The title
# captures up to the closing `**` (greedy across the rest of the line).
_FR_HEADER_RE: Final = re.compile(
    r"^\*\*((?:FR|NFR)-\d+(?:\.\d+)?):\s*(.+?)\*\*\s*$",
    re.MULTILINE,
)

# Used to truncate a block when a section heading appears inside it (e.g.
# `## 6. Other content` between FRs, or a `#### 4.3 New Feature` heading
# that starts a different feature section). Matches H2..H5 headings; H1
# is typically the document title (won't appear mid-document) and H6 is
# rare enough to be ignored. Anything tighter loses legitimate sub-content
# inside an FR; anything looser cuts FR bodies at their own sub-headings.
_SECTION_HEADING_RE: Final = re.compile(r"^#{2,5}\s+\S", re.MULTILINE)

# Marker that separates the statement-body from the acceptance criteria.
_ACCEPTANCE_MARKER_RE: Final = re.compile(
    r"^\*\*Acceptance criteria:\*\*\s*", re.MULTILINE
)

# A well-formed Opportunity reference: `dna:opportunity:` + a 26-char
# Crockford-base32 ULID (no I/L/O/U). This is the *load-bearing* gate of the
# single-idea path (ADR-005): a Requirement composed from an idea MUST trace to
# a real Opportunity the orchestrator just emitted — never a synthetic
# placeholder, never a dangling ref. It is deliberately tighter than the
# schema's `source` pattern (which also admits `dna:actor:`): the from-idea
# path only ever sources from an Opportunity.
_OPPORTUNITY_REF_RE: Final = re.compile(r"^dna:opportunity:[0-9A-HJKMNP-TV-Z]{26}$")


# ─── id derivation ────────────────────────────────────────────────────────


def _deterministic_ulid_from(seed: str) -> str:
    """Stable 26-char Crockford-base32 ULID derived from `seed`.

    Used here to make Requirement ids reproducible — the same SRD + FR id
    always yield the same Requirement entity id, so re-emitting an SRD
    overwrites prior instances in place rather than creating duplicates.
    Same trick generates the synthetic Opportunity source id.
    """
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    # 17 bytes = 136 bits; mask down to exactly 130 (26 chars × 5 bits).
    n = int.from_bytes(digest[:17], "big") & ((1 << 130) - 1)
    chars: list[str] = []
    for _ in range(26):
        chars.append(_CROCKFORD_ALPHABET[n & 0x1F])
        n >>= 5
    return "".join(reversed(chars))


# ─── block extraction ─────────────────────────────────────────────────────


def _split_into_blocks(body: str) -> list[tuple[str, str, str]]:
    """Find each FR/NFR header and the body block following it.

    Returns `(fr_id, title, block_body)` tuples in document order. A block
    runs from the line after its header to the next FR/NFR header *or* the
    next `^## ` section heading (whichever comes first) — so trailing
    sections like "Out-of-scope" don't get vacuumed into the last FR.
    """
    headers = list(_FR_HEADER_RE.finditer(body))
    if not headers:
        return []

    blocks: list[tuple[str, str, str]] = []
    for i, header in enumerate(headers):
        fr_id = header.group(1)
        title = header.group(2).strip()
        block_start = header.end()
        block_end = (
            headers[i + 1].start() if i + 1 < len(headers) else len(body)
        )

        # If a section heading falls between this header and the next FR,
        # truncate the block there.
        section_in_block = _SECTION_HEADING_RE.search(body, block_start, block_end)
        if section_in_block is not None:
            block_end = section_in_block.start()

        block_body = body[block_start:block_end].strip()
        blocks.append((fr_id, title, block_body))

    return blocks


def _split_statement_and_acceptance(
    block_body: str,
) -> tuple[str, list[str]]:
    """Split a block's body into (statement_prose, acceptance_criteria)."""
    marker = _ACCEPTANCE_MARKER_RE.search(block_body)
    if marker is None:
        return _flatten(block_body), []
    statement = _flatten(block_body[: marker.start()])
    acceptance_raw = block_body[marker.end():].strip()
    acceptance = [_flatten(acceptance_raw)] if acceptance_raw else []
    return statement, acceptance


def _flatten(text: str) -> str:
    """Collapse whitespace in a prose block to a single string."""
    return re.sub(r"\s+", " ", text).strip()


# ─── public API ───────────────────────────────────────────────────────────


def compose_requirements_from_srd(
    srd_text: str,
    *,
    srd_path: str,
) -> list[dict]:
    """Pure transformation: SRD text + path → list of Requirement entity dicts.

    Args:
        srd_text: the full SRD markdown content.
        srd_path: a string identifier for the source SRD (path or any stable
            label). Used as input to deterministic-id derivation; no I/O is
            performed on this path.

    Each detected `**FR-NN: ...**` / `**NFR-NN: ...**` block produces one
    Requirement entity dict. Returns an empty list when no FR markers exist
    (the extractor does not raise on missing structure).
    """
    blocks = _split_into_blocks(srd_text)
    if not blocks:
        return []

    # One synthetic Opportunity for all FRs in this SRD. The schema requires
    # `source` to match `dna:opportunity:{ulid}` or `dna:actor:{ulid}`. The
    # synthetic id is deterministic from the SRD path; the placeholder
    # nature is recorded in each Requirement's `rationale`. Once Opportunity
    # emission lands, this gets replaced with a real reference (the synthetic
    # ULID's hash space cannot collide with real ULIDs by accident — the
    # bit pattern is hash-derived, not random + timestamp).
    source_ulid = _deterministic_ulid_from(f"opportunity-from-srd:{srd_path}")
    source = f"dna:opportunity:{source_ulid}"

    requirements: list[dict] = []
    for fr_id, title, block_body in blocks:
        statement_prose, acceptance = _split_statement_and_acceptance(block_body)
        # Join title + body for the schema's `statement` field — title alone
        # is too thin; body alone hides which FR this came from.
        statement = _flatten(f"{title}. {statement_prose}").rstrip(". ")

        req_ulid = _deterministic_ulid_from(f"requirement:{srd_path}:{fr_id}")

        requirements.append({
            "id": f"dna:requirement:{req_ulid}",
            "statement": statement,
            "priority": "must",
            "source": source,
            "verification_method": "test",
            "acceptance_criteria": acceptance if acceptance else ["see SRD body"],
            "state": "draft",
            "sys_status": "active",
            "rationale": (
                f"Extracted from {fr_id} of {srd_path}. The `source` ref is a "
                "synthetic Opportunity placeholder generated from the SRD "
                "path; replace when Opportunity emission lands (queued "
                "follow-on slice). Defaults applied for SRD-absent fields: "
                "priority=must, verification_method=test, state=draft."
            ),
        })

    return requirements


def compose_requirement_from_idea(
    *,
    statement: str,
    source: str,
    seed: str,
    priority: str = "must",
    acceptance_criteria: list[str] | None = None,
) -> dict:
    """Pure transform: single idea fields → one Requirement entity dict. No I/O.

    The single-idea sibling of `compose_requirements_from_srd` (ADR-005).
    Capture has no document to parse — it has a what-string typed in
    conversation and a *real* Opportunity ref the orchestrator just emitted.
    This produces the same Requirement dict shape the from-SRD path produces
    (validates against the same vendored `requirement.schema.json`), but from
    explicit fields rather than parsed markers.

    Args:
        statement: the requirement text (the "what").
        source: a `dna:opportunity:<ulid>` reference — REAL, never synthetic.
            The caller (the capture orchestrator) supplies an Opportunity id it
            just emitted. Passed through verbatim.
        seed: a stable seed string → deterministic ULID (NFR-04). Same seed ⇒
            same id ⇒ re-capturing overwrites in place rather than duplicating.
        priority: MoSCoW priority; defaults to ``"must"``.
        acceptance_criteria: optional list; ``None`` ⇒ a single honest
            placeholder criterion (the schema requires ``minItems: 1``).

    Returns:
        A Requirement entity dict. The ``id`` is
        ``dna:requirement:`` + ``_deterministic_ulid_from("requirement-from-idea:" + seed)``
        — a distinct namespace from the from-SRD path so the two never collide
        on the same seed string. ``state`` defaults to ``"draft"``
        (captured-and-set-aside lives as a draft).

    Raises:
        ValueError: if ``source`` is not a well-formed
            ``dna:opportunity:<ulid>`` reference. This is the code-level
            enforcement of "no orphan requirements": the function refuses to
            emit a Requirement with a dangling or synthetic source (ADR-005,
            ADR-003). Fail loud — never compose a Requirement that can't trace
            to a real Opportunity.
    """
    if not _OPPORTUNITY_REF_RE.match(source):
        raise ValueError(
            "compose_requirement_from_idea: `source` must be a real "
            "Opportunity reference matching "
            "'dna:opportunity:<26-char-ULID>' (ADR-005: no orphan "
            f"requirements); got {source!r}. The caller must pass the id of "
            "an Opportunity it has already emitted — never a synthetic "
            "placeholder."
        )

    req_ulid = _deterministic_ulid_from(f"requirement-from-idea:{seed}")

    return {
        "id": f"dna:requirement:{req_ulid}",
        "statement": _flatten(statement),
        "priority": priority,
        "source": source,
        "verification_method": "test",
        "acceptance_criteria": (
            acceptance_criteria
            if acceptance_criteria
            else ["captured from idea; acceptance criteria to be elaborated"]
        ),
        "state": "draft",
        "sys_status": "active",
    }


def emit_requirements_from_srd(
    srd_path: Path,
    repo: EntityRepository,
) -> list[dict]:
    """Read an SRD file and emit each detected Requirement through `repo`.

    Returns the list of saved Requirement dicts. Raises
    `EntityValidationError` (propagated from the adapter) on a malformed
    entity; the adapter persists nothing in that case.
    """
    srd_text = Path(srd_path).read_text(encoding="utf-8")
    requirements = compose_requirements_from_srd(
        srd_text, srd_path=str(srd_path)
    )
    for req in requirements:
        repo.save("requirement", req)
    return requirements
