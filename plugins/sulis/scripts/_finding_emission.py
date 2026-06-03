"""Finding-entity emission.

Sixth worked entity emission. Finding replaces the `findings-register.md`
danger-class artifact from the strong-typed-artifacts inventory — that
table-in-markdown was being regex-parsed by `wpx-findings` (one of the
canonical danger-class members alongside `INDEX.md`).

Two source modes — Finding is the first emitter where source-cardinality
genuinely varies by caller, not by the entity itself:

  1. **Single-finding mode** — `compose_finding(kind=, severity=, summary=, observed_in=)`
     creates one Finding dict. Used by skills emitting one finding at a time
     (`/sulis:check-security` flags an SSRF; `/sulis:code-review` flags one
     code smell).
  2. **Bulk mode** — `compose_findings_from_register(register_path)` reads an
     existing `findings-register.md` (legacy) and emits a Finding per row.
     Migration helper; deprecates once all check skills wire mode (1).

ID strategy: deterministic Crockford-base32 ULID from a signature derived
from (kind + severity + summary + observed_in). Same finding → same id →
re-running a scan is idempotent. The signature is the same key
`wpx-findings` uses today for dedupe — we keep that contract.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

from _entity_repository import EntityRepository


_CROCKFORD_ALPHABET: Final[str] = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

# Accepted kinds + severities per the vendored schema (must stay in lockstep).
_VALID_KINDS: Final[set[str]] = {
    "code-quality", "security", "operability", "performance",
    "accessibility", "other",
}
_VALID_SEVERITIES: Final[set[str]] = {
    "critical", "high", "medium", "low", "info",
}

# `observed_in` on a Finding is a TYPED ref — must point at a Component,
# Release, or Deployment entity. Free-form locators (file:line) are NOT
# accepted by the schema; they get dropped (with the truthful loc still
# encoded in the `summary` for now). Once Component emission lands, the
# call site will pass a real `dna:component:<ulid>` here.
_OBSERVED_IN_RE: Final = re.compile(
    r"^dna:(component|release|deployment):[0-9A-HJKMNP-TV-Z]{26}$"
)


def _deterministic_ulid_from(seed: str) -> str:
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    n = int.from_bytes(digest[:17], "big") & ((1 << 130) - 1)
    chars: list[str] = []
    for _ in range(26):
        chars.append(_CROCKFORD_ALPHABET[n & 0x1F])
        n >>= 5
    return "".join(reversed(chars))


def _finding_signature(kind: str, severity: str, summary: str, observed_in: str) -> str:
    """The dedupe key for a finding. Same as the convention `wpx-findings`
    uses today — kept stable so the migration helper produces identical
    ULIDs to what wpx-findings would assign."""
    normalised_summary = re.sub(r"\s+", " ", summary).strip().lower()
    return f"{kind}:{severity}:{observed_in or 'unscoped'}:{normalised_summary}"


def compose_finding(
    *,
    kind: str,
    severity: str,
    summary: str,
    observed_in: str = "",
    observed_at: str | None = None,
) -> dict:
    """Compose a single Finding dict from explicit inputs.

    `kind` and `severity` MUST be valid per schema. `observed_in` is a free-
    form locator (file:line, URL, component id). `observed_at` defaults to
    now() in ISO 8601 UTC.
    """
    if kind not in _VALID_KINDS:
        raise ValueError(
            f"finding kind must be one of {sorted(_VALID_KINDS)}; got {kind!r}"
        )
    if severity not in _VALID_SEVERITIES:
        raise ValueError(
            f"finding severity must be one of {sorted(_VALID_SEVERITIES)}; got {severity!r}"
        )
    if not summary or not summary.strip():
        raise ValueError("finding summary may not be empty")

    # `observed_in` strict: only emit if it matches the schema pattern (a
    # typed ref). Free-form locators (file:line) are dropped — keep the
    # signature carrying them so dedup remains stable, fold the locator
    # into `summary` so it's not lost.
    typed_observed_in: str | None = None
    locator_for_summary: str = ""
    if observed_in:
        if _OBSERVED_IN_RE.match(observed_in):
            typed_observed_in = observed_in
        else:
            locator_for_summary = observed_in.strip()

    composed_summary = summary.strip()
    if locator_for_summary and locator_for_summary not in composed_summary:
        composed_summary = f"{composed_summary} (at {locator_for_summary})"

    sig = _finding_signature(kind, severity, composed_summary, observed_in)
    finding: dict = {
        "id": "dna:finding:" + _deterministic_ulid_from(f"finding:{sig}"),
        "kind": kind,
        "severity": severity,
        "summary": composed_summary,
        "observed_at": observed_at or datetime.now(timezone.utc).isoformat(),
        "state": "open",
        "sys_status": "active",
    }
    if typed_observed_in:
        finding["observed_in"] = typed_observed_in
    return finding


def compose_findings_from_register(
    register_path: Path,
) -> list[dict]:
    """Migration helper — parse a legacy `findings-register.md` table into
    a list of Finding dicts.

    Expected table shape (the canonical `wpx-findings` register format):

        | SF-NNN | kind | severity | observed_in | summary | signature |

    Rows are recognised by the `SF-NNN` id column. Other rows (separator,
    header) are skipped.
    """
    text = Path(register_path).read_text(encoding="utf-8")
    findings: list[dict] = []
    for line in text.splitlines():
        # Recognise table rows by the `| SF-xxxx |` cell pattern. The SF id is
        # hex (derived from the finding signature); `[0-9a-f]+` also matches
        # legacy decimal ids (SF-001), so pre-existing registers still parse.
        match = re.match(
            r"^\|\s*SF-[0-9a-f]+\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|\s*([^|]+?)\s*\|",
            line,
        )
        if not match:
            continue
        kind, severity, observed_in, summary = match.groups()
        try:
            f = compose_finding(
                kind=kind.strip(),
                severity=severity.strip(),
                summary=summary.strip(),
                observed_in=observed_in.strip(),
            )
        except ValueError:
            # Skip malformed rows rather than failing the whole migration.
            continue
        findings.append(f)
    return findings


def emit_finding(
    *,
    repo: EntityRepository,
    kind: str,
    severity: str,
    summary: str,
    observed_in: str = "",
    observed_at: str | None = None,
) -> dict:
    """Compose-and-persist one Finding."""
    finding = compose_finding(
        kind=kind,
        severity=severity,
        summary=summary,
        observed_in=observed_in,
        observed_at=observed_at,
    )
    repo.save("finding", finding)
    return finding


def emit_findings_from_register(
    register_path: Path,
    repo: EntityRepository,
) -> list[dict]:
    findings = compose_findings_from_register(register_path)
    for f in findings:
        repo.save("finding", f)
    return findings
