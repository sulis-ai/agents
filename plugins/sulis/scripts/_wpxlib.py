"""Shared helpers for the wpx-* CLI tools.

Stdlib only. Provides:
- Path resolution for project-relative artifacts.
- Markdown frontmatter parsing (tiny, no pyyaml dependency).
- JSON output helpers (consistent shape).
- Markdown table parsing/writing (for journal + INDEX manipulation).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol, runtime_checkable


# ─────────────────────────────────────────────────────────────────────────
# Path resolution
# ─────────────────────────────────────────────────────────────────────────


@dataclass
class WpxPaths:
    """Project-relative paths for executor artifacts."""

    repo_root: Path
    project: str

    @property
    def arch_root(self) -> Path:
        return self.repo_root / ".architecture" / self.project

    @property
    def wp_dir(self) -> Path:
        return self.arch_root / "work-packages"

    @property
    def index_md(self) -> Path:
        return self.wp_dir / "INDEX.md"

    @property
    def security_dir(self) -> Path:
        return self.repo_root / ".security" / self.project

    @property
    def findings_dir(self) -> Path:
        return self.security_dir / "findings"

    @property
    def findings_register(self) -> Path:
        return self.security_dir / "findings-register.md"

    def journal(self, wp: str) -> Path:
        return self.wp_dir / f".executor-{wp}.md"

    @property
    def train_overrides(self) -> Path:
        return self.arch_root / "train-overrides.yaml"

    @property
    def train_runs_dir(self) -> Path:
        return self.arch_root / "train-runs"

    def blocker(self, wp: str) -> Path:
        return self.wp_dir / f"BLOCKER-{wp}.md"

    def wp_file(self, wp: str) -> Path:
        # Look for WP-NNN-*.md (the file's name includes a slug)
        matches = list(self.wp_dir.glob(f"{wp}-*.md"))
        # Filter out journal/blocker/auto-draft files
        matches = [
            m for m in matches
            if not m.name.startswith(".")
            and not m.name.startswith("BLOCKER-")
        ]
        if not matches:
            raise FileNotFoundError(
                f"No WP file matching {wp}-*.md in {self.wp_dir}"
            )
        if len(matches) > 1:
            raise ValueError(
                f"Multiple WP files match {wp}-*.md: {matches}"
            )
        return matches[0]


def add_common_args(parser: argparse.ArgumentParser) -> None:
    """Add --project and --repo-root to a parser."""
    parser.add_argument(
        "--project",
        required=True,
        help="Project slug (used to resolve .architecture/<project>/ paths)",
    )
    parser.add_argument(
        "--repo-root",
        default=os.getcwd(),
        help="Repo root directory (defaults to cwd)",
    )


def paths_from_args(args: argparse.Namespace) -> WpxPaths:
    return WpxPaths(repo_root=Path(args.repo_root).resolve(), project=args.project)


# ─────────────────────────────────────────────────────────────────────────
# JSON output
# ─────────────────────────────────────────────────────────────────────────


def emit_ok(
    data: dict | None = None,
    warnings: list[str] | None = None,
    exit_code: int = 0,
) -> None:
    """Print success JSON to stdout and exit with the given code (default 0).

    The `exit_code` parameter exists for tools that emit a
    structured-JSON result alongside a non-zero exit semantic.
    Concrete use case: `wpx-pipeline` emits a fully-formed result
    object with `outcome="blocker"` and `exit_code=1` so the calling
    session's `Bash(run_in_background)` notification can distinguish
    a clean pipeline-blocker (exit 1, structured JSON readable from
    the stdout file) from a successful pipeline (exit 0) or an
    internal-error crash (exit 2 via emit_internal_error).

    For normal success in every other wpx-* tool, the default
    exit_code=0 preserves the prior contract.
    """
    payload = {"ok": True}
    if data is not None:
        payload["data"] = data
    if warnings:
        payload["warnings"] = warnings
    print(json.dumps(payload, indent=2, sort_keys=True))
    sys.exit(exit_code)


def emit_error(message: str, context: dict | None = None) -> None:
    """Print error JSON to stdout, error to stderr, exit 1 (expected failure)."""
    payload = {"ok": False, "error": message}
    if context is not None:
        payload["context"] = context
    print(json.dumps(payload, indent=2, sort_keys=True))
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def emit_internal_error(exc: BaseException) -> None:
    """Print traceback to stderr, exit 2 (bug)."""
    traceback.print_exception(type(exc), exc, exc.__traceback__, file=sys.stderr)
    sys.exit(2)


def cli_main(parser: argparse.ArgumentParser, handlers: dict) -> None:
    """Run a CLI tool with subcommand dispatch."""
    args = parser.parse_args()
    handler = handlers.get(args.subcommand)
    if handler is None:
        emit_error(f"Unknown subcommand: {args.subcommand}")
    try:
        handler(args)
    except FileNotFoundError as e:
        emit_error(str(e))
    except ValueError as e:
        emit_error(str(e))
    except SystemExit:
        raise
    except BaseException as e:  # noqa: BLE001
        emit_internal_error(e)


# ─────────────────────────────────────────────────────────────────────────
# Markdown frontmatter (YAML-like, tiny inline parser)
# ─────────────────────────────────────────────────────────────────────────


_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


# #104 — historical drift: SEA authored snake-case `depends_on` while every
# wpx/execution reader uses camel-case `dependsOn`. Alias snake → camel at
# parse time so the dep set surfaces regardless of which spelling the
# author used. List form (`depends-on`) covered for symmetry.
_FRONTMATTER_KEY_ALIASES: dict[str, str] = {
    "depends_on": "dependsOn",
    "depends-on": "dependsOn",
}


def _alias_frontmatter_key(key: str) -> str:
    return _FRONTMATTER_KEY_ALIASES.get(key, key)


_FM_INLINE_COMMENT_RE = re.compile(r"\s+#(?:\s.*)?$")


def _strip_frontmatter_inline_comment(s: str) -> str:
    """Strip a trailing YAML-style inline ``# comment``.

    A comment starts with whitespace + ``#`` and either ends the line
    immediately OR is followed by whitespace + the comment text. A ``#``
    glued to a value with no leading whitespace stays intact, and a
    ``#`` immediately followed by a non-space token (e.g. ``Honest #1``
    or ``id: WP-#1``) stays intact — only YAML-form comments are stripped.
    """
    return _FM_INLINE_COMMENT_RE.sub("", s).rstrip()


def parse_frontmatter(text: str) -> tuple[dict[str, str | list[str]], str]:
    """Parse a Markdown file's YAML-like frontmatter.

    Supports:
      key: value          (scalar)
      key:                (start of list)
        - item1
        - item2
      key: [a, b, c]      (inline list)

    Snake-case `depends_on` and `depends-on` alias to `dependsOn` (#104).
    Trailing inline `# comment`s are stripped from values + list items.

    Returns (frontmatter_dict, body_after_frontmatter).
    """
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    fm_text = match.group(1)
    body = text[match.end():]
    fm: dict[str, str | list[str]] = {}
    current_list_key: str | None = None
    for raw_line in fm_text.splitlines():
        line = raw_line.rstrip()
        if not line or line.startswith("#"):
            continue
        if current_list_key is not None and line.startswith("  - "):
            # Continue list — strip inline comment before unquoting.
            item = _strip_frontmatter_inline_comment(line[4:]).strip().strip("'\"")
            assert isinstance(fm[current_list_key], list)
            fm[current_list_key].append(item)  # type: ignore[union-attr]
            continue
        # New key
        current_list_key = None
        if ":" not in line:
            continue
        key, _, rest = line.partition(":")
        key = _alias_frontmatter_key(key.strip())
        rest = _strip_frontmatter_inline_comment(rest.strip())
        if rest == "":
            # Start of a list
            fm[key] = []
            current_list_key = key
        elif rest.startswith("[") and rest.endswith("]"):
            # Inline list — strip per-item inline comments too.
            inner = rest[1:-1]
            items = [
                _strip_frontmatter_inline_comment(i).strip().strip("'\"")
                for i in inner.split(",")
                if i.strip()
            ]
            fm[key] = items
        else:
            # Scalar
            value = rest.strip("'\"")
            fm[key] = value
    return fm, body


def read_frontmatter(path: Path) -> dict[str, str | list[str]]:
    text = path.read_text(encoding="utf-8")
    fm, _ = parse_frontmatter(text)
    return fm


# ─────────────────────────────────────────────────────────────────────────
# Markdown table helpers
# ─────────────────────────────────────────────────────────────────────────


@dataclass
class MdTable:
    """Lightweight Markdown table representation."""

    headers: list[str] = field(default_factory=list)
    alignments: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)

    def render(self) -> str:
        lines = []
        lines.append("| " + " | ".join(self.headers) + " |")
        lines.append("|" + "|".join(self.alignments or ["---"] * len(self.headers)) + "|")
        for row in self.rows:
            # Pad / truncate to headers length
            padded = list(row) + [""] * (len(self.headers) - len(row))
            padded = padded[: len(self.headers)]
            lines.append("| " + " | ".join(padded) + " |")
        return "\n".join(lines)


def parse_md_table(table_text: str) -> MdTable:
    """Parse a Markdown table block (starting with | header |)."""
    lines = [ln for ln in table_text.strip().splitlines() if ln.strip()]
    if len(lines) < 2:
        return MdTable()
    headers = [c.strip() for c in lines[0].strip("|").split("|")]
    alignments = [c.strip() for c in lines[1].strip("|").split("|")]
    rows = []
    for line in lines[2:]:
        if not line.startswith("|"):
            break
        cells = [c.strip() for c in line.strip("|").split("|")]
        rows.append(cells)
    return MdTable(headers=headers, alignments=alignments, rows=rows)


# ─── WP INDEX column resolution (shared by wpx-index + parse_index_md) ──────
#
# Two parsers historically disagreed on the "depends" column header —
# wpx-index keyed on "depends", parse_index_md keyed on "depends on" — so a
# correctly-generated INDEX (canonical header "Depends On") was silently
# rejected by one of them (L-02). This is the SINGLE source of truth both now
# call: a canonical column key → the set of accepted (lowercased) header
# spellings. Adding a spelling here fixes both parsers at once.
WP_COLUMN_ALIASES: dict[str, frozenset[str]] = {
    "id": frozenset({"id", "wp", "wp id"}),
    "title": frozenset({"title", "name"}),
    "primitive": frozenset({"primitive", "kind"}),
    "status": frozenset({"status"}),
    "depends": frozenset(
        {"depends", "depends on", "dependson", "depends_on", "depends-on"}
    ),
    "blocks": frozenset({"blocks", "blocked by", "unblocks"}),
}


def _normalise_header(header: str) -> str:
    """Lowercase + strip a header to its comparable form (drops a trailing
    footnote marker like ' *')."""
    return header.strip().lower().rstrip(" *")


def resolve_wp_columns(headers: list[str]) -> dict[str, int]:
    """Map a WP table's headers to canonical column keys → column index.

    Both wpx-index and parse_index_md call this so they resolve the same
    table identically. Header spelling variants (``Depends On`` / ``Depends``
    / ``depends_on``) all collapse to the canonical key ``"depends"``.
    Unknown headers are ignored (callers read them as extras). First match
    wins if a spelling somehow maps twice.
    """
    resolved: dict[str, int] = {}
    for i, raw in enumerate(headers):
        norm = _normalise_header(raw)
        for canonical, spellings in WP_COLUMN_ALIASES.items():
            if norm in spellings and canonical not in resolved:
                resolved[canonical] = i
                break
    return resolved


# ─── Canonical WP status vocabulary (L-03) ──────────────────────────────
#
# `pending` is the canonical "ready to start" word — it aligns wpx-index,
# parse_index_md, the orchestrator, and the plan-work template. Before L-03
# there were four spellings (WP-07 said `todo`; _lib.wp_index defaulted
# `todo` and bucketed any UNKNOWN status as "ready"), so a WP with a drifted
# status (`ready`) looked fine in the INDEX but was invisible to `list-ready`,
# which counts only `pending`.
#
# Two sets, two jobs:
#   * WRITE path (this set, strict) — a WP being added/decomposed MUST use one
#     of these. `todo`/`ready` are deliberately absent: new WPs use `pending`,
#     so drift fails loudly at add time (validate_wp_status) instead of
#     vanishing silently.
#   * READ path (lenient) — `_lib.wp_index.STATUS_BUCKETS` separately tolerates
#     `pending`/`todo`/`ready` so any pre-existing legacy file still surfaces.

WP_STATUS_READY = "pending"

CANONICAL_WP_STATUSES: frozenset[str] = frozenset(
    {
        "pending",              # ready to start (canonical)
        "in_progress",
        "blocked",
        "dependency_blocked",   # transitional, set by propagate-blocked
        "sleeping",             # paused, needs a decision (WP-07)
        "step-7-complete",      # train lifecycle: coded, awaiting steps 8-11
        "step-7-held",
        "step-7-blocked",
        "done",
        "closed",               # loop-verified (WP-07)
        "regressed",            # WP-07
        "abandoned",            # WP-07
        "cancelled",            # auto-draft dispositioned out
        "auto-draft",           # security finding awaiting disposition
    }
)


def validate_wp_status(status: str) -> str | None:
    """Return None if ``status`` is a canonical WP status, else an error string.

    Comparison is whitespace-trimmed + case-insensitive; the canonical set is
    lowercase. An unrecognised non-empty status is the L-03 bug class (a WP that
    silently never appears in ``list-ready``); callers MUST surface the returned
    message loudly (emit_error for a single WP, a per-WP error for a batch)
    rather than write the row.
    """
    norm = (status or "").strip().lower()
    if norm in CANONICAL_WP_STATUSES:
        return None
    valid = ", ".join(sorted(CANONICAL_WP_STATUSES))
    return (
        f"unrecognised WP status {status!r} — must be one of: {valid}. "
        f"Use {WP_STATUS_READY!r} for a ready-to-start WP "
        f"('todo'/'ready' are tolerated only for display, not for new WPs)."
    )


# ─── Visual-contract gate (#45 / UXD-14) ────────────────────────────────
#
# A user-facing surface MUST be built against a signed-off visual contract
# (a real-token mockup), or the "still looks the same" failure recurs (L-13:
# tokens matched the mockup but the founder saw no brand — fonts unloaded).
# The gate has two halves:
#   * write-time (validate_frontend_wp_visual_contract, below) — a
#     `kind: frontend` WP cannot enter the INDEX unless it declares the
#     visual-contract WP it depends on. Fires at the single chokepoint every WP
#     passes through (`_cells_from_frontmatter` in wpx-index), exactly like
#     validate_wp_status. Because the declared contract WP is in `dependsOn`,
#     list-ready's done-oracle won't dispatch the frontend WP until that
#     contract WP is `done`.
#   * runtime sign-off (the contract WP only reaches `done` once its mockup
#     record is signed off) — Phase 2, wired at the done-transition.
#
# The only bypass is an explicit, logged exemption (`visual_contract:
# exempt — <reason>`) or a `prototype` WP — rare, never silent.


def _as_str_list(value) -> list[str]:
    """Normalise a dependsOn/blocks value (list, comma-string, or scalar) to a
    list of trimmed strings."""
    if value is None:
        return []
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [str(value).strip()] if str(value).strip() else []


def validate_frontend_wp_visual_contract(fm: dict) -> str | None:
    """Return None if a frontend WP correctly declares its visual contract,
    else an error message (the write-time half of the #45 / UXD-14 gate).

    A ``kind: frontend`` WP MUST carry a ``visual_contract:`` field that is
    either (a) the id of the visual-contract WP it depends on — which MUST also
    appear in ``dependsOn`` so list-ready won't dispatch it before that WP is
    signed off (done) — or (b) an explicit logged exemption
    (``visual_contract: exempt — <reason>``) or a ``prototype: true`` WP.
    Non-frontend WPs are never gated.
    """
    kind = str(fm.get("kind", "")).strip().lower()
    if kind != "frontend":
        return None
    if fm.get("prototype") is True:
        return None
    vc = str(fm.get("visual_contract", "") or "").strip()
    if vc.lower().startswith("exempt"):
        return None
    if not vc:
        return (
            "kind: frontend requires a `visual_contract:` field naming the "
            "signed-off visual-contract WP it depends on (or "
            "`visual_contract: exempt — <reason>` for a logged, genuinely "
            "non-visual exception). The visual contract is mandatory for "
            "user-facing surfaces (UXD-14)."
        )
    deps = _as_str_list(fm.get("dependsOn"))
    if vc not in deps:
        return (
            f"`visual_contract: {vc}` must also appear in dependsOn so "
            f"list-ready won't dispatch this frontend WP before the "
            f"visual-contract WP {vc} is signed off (done)."
        )
    return None


def is_visual_contract_wp(fm: dict) -> bool:
    """True if a WP's frontmatter marks it as the visual-contract WP
    (``kind: contract`` + ``contract_type: visual``)."""
    return (
        str(fm.get("kind", "")).strip().lower() == "contract"
        and str(fm.get("contract_type", "")).strip().lower() == "visual"
    )


def visual_contract_signed_off(fm: dict) -> str | None:
    """Return None if a visual-contract WP's frontmatter shows founder
    sign-off, else an error message (the runtime half of the #45 / UXD-14
    gate, wired at the visual-contract WP's done-transition).

    Signed off = a non-empty ``signed_off_at`` timestamp AND
    ``provenance: production-approved`` (UXD-13's strongest track — the founder
    has seen the real-token mockup *rendered*, per L-13, not merely matched
    token values). Until then the contract WP cannot reach ``done``, so the
    frontend WPs that ``dependsOn`` it stay undispatchable.
    """
    signed_at = str(fm.get("signed_off_at", "") or "").strip()
    provenance = str(fm.get("provenance", "") or "").strip().lower()
    if not signed_at:
        return (
            "visual contract not signed off — `signed_off_at` is empty. The "
            "founder must sign off the rendered real-token mockup before this "
            "contract WP can reach `done` (UXD-14)."
        )
    if provenance != "production-approved":
        return (
            f"visual contract provenance is {provenance!r}, not "
            f"'production-approved' — sign-off means the founder approved the "
            f"rendered mockup, not just that token values matched (UXD-13/L-13)."
        )
    return None


# ─── Interaction-flow gate (CH-01KT9H / ADR-001) ────────────────────────────
#
# Sibling of the visual-contract gate above. Same two seams (recognition
# predicate + runtime done-gate predicate), reused verbatim in shape. The one
# genuinely-new contract is the evidence frontmatter (ADR-001): an interaction
# contract carries TWO valid evidence sources (agent-observed | human-attested)
# rather than the visual gate's single `production-approved` track, so the
# controlled token compares against a frozenset of two rather than a literal —
# the only structural difference from `visual_contract_signed_off`. The token
# set and the messages differ, so no helper is force-extracted (Boy-Scout-
# scoped non-extraction; the two predicates stay legible side-by-side).


def is_interaction_contract_wp(fm: dict) -> bool:
    """True if a WP's frontmatter marks it as the interaction-contract WP
    (``kind: contract`` + ``contract_type: interaction``). Sibling of
    :func:`is_visual_contract_wp`."""
    return (
        str(fm.get("kind", "")).strip().lower() == "contract"
        and str(fm.get("contract_type", "")).strip().lower() == "interaction"
    )


# The two valid evidence sources for an exercised interaction flow (ADR-001).
_INTERACTION_EVIDENCE_SOURCES: frozenset[str] = frozenset(
    {"agent-observed", "human-attested"}
)


def interaction_flow_exercised(fm: dict) -> str | None:
    """Return None if an interaction-contract WP's frontmatter shows its flow
    was exercised end-to-end over stub adapters, else a founder-readable error
    (the runtime half of the CH-01KT9H gate, wired at the interaction-contract
    WP's done-transition). Mirrors :func:`visual_contract_signed_off`.

    Exercised = (ADR-001) a non-empty ``exercised_at`` timestamp AND
    ``exercised_by`` ∈ {``agent-observed``, ``human-attested``}
    (case-insensitive) AND a non-empty ``exercised_attestation``. Requiring the
    attestation keeps the evidence falsifiable — a bare timestamp with no record
    of *who/what* exercised the flow must NOT satisfy the gate. The gate trusts
    the record and does not re-run the flow (ADR-003).
    """
    exercised_at = str(fm.get("exercised_at", "") or "").strip()
    exercised_by = str(fm.get("exercised_by", "") or "").strip().lower()
    attestation = str(fm.get("exercised_attestation", "") or "").strip()
    if not exercised_at:
        return (
            "interaction flow not exercised — `exercised_at` is empty. The flow "
            "must be exercised end-to-end over stub adapters before this "
            "contract WP can reach `done` (CH-01KT9H / ADR-001)."
        )
    if not exercised_by:
        return (
            "interaction flow not exercised — `exercised_by` is empty. Record "
            "the evidence source: `agent-observed` or `human-attested` "
            "(ADR-001)."
        )
    if exercised_by not in _INTERACTION_EVIDENCE_SOURCES:
        return (
            f"interaction `exercised_by` is {exercised_by!r}, not a valid "
            f"evidence source — must be `agent-observed` or `human-attested` "
            f"(ADR-001)."
        )
    if not attestation:
        return (
            "interaction flow not exercised — `exercised_attestation` is empty. "
            "Name who/what exercised the flow (an agent run points at its "
            "transcript; a human names themselves), so the evidence is "
            "falsifiable (ADR-001)."
        )
    return None


# ─── Data-contract structural check (#48 / CF-05 / WP-08.5) ──────────────
#
# The symmetric partner to the visual-contract gate, but GRAPH-level: whether a
# change is a producer/consumer seam is a property of the whole WP set, not a
# single WP (so it can't live at the per-WP _cells_from_frontmatter chokepoint
# the way the visual gate does). The data contract's *conformance* is already
# test-enforced (CF-07 integration WP); this closes the structural-wiring half
# — the same "aspirational MUST" weakness #45 fixed for visual.

_IMPL_KINDS: frozenset[str] = frozenset({"backend", "frontend", "async"})


def validate_cross_kind_contract_wiring(wps: list[dict]) -> list[str]:
    """Return a list of data-contract wiring violations for a WP set (empty =
    pass). Pure; operates on WP frontmatter dicts ({id, kind, contract_type,
    dependsOn, prototype}).

    Applied only when the set spans a producer/consumer seam (≥2 distinct
    implementation kinds among backend/frontend/async, excluding prototypes):
      1. A data-contract WP must exist (``kind: contract`` with
         ``contract_type`` != ``visual``). A visual contract does not satisfy
         a data seam.
      2. No direct dependency edge between two different implementation kinds —
         cross-kind deps MUST route through the contract WP (CF-05 parallel-
         not-sequential). ``frontend dependsOn backend`` is the canonical
         violation.
    Single-kind sets and prototype-only seams are not checked.
    """
    by_id: dict[str, dict] = {}
    kinds_present: set[str] = set()
    for wp in wps:
        wid = str(wp.get("id", "")).strip()
        if not wid:
            continue
        by_id[wid] = wp
        kind = str(wp.get("kind", "")).strip().lower()
        if kind in _IMPL_KINDS and wp.get("prototype") is not True:
            kinds_present.add(kind)

    if len(kinds_present) < 2:
        return []  # not a cross-kind seam

    violations: list[str] = []

    # Rule 1 — a data-contract WP exists.
    has_data_contract = any(
        str(w.get("kind", "")).strip().lower() == "contract"
        and str(w.get("contract_type", "") or "").strip().lower() != "visual"
        for w in wps
    )
    if not has_data_contract:
        violations.append(
            f"cross-kind WP set (kinds: {', '.join(sorted(kinds_present))}) has "
            f"no data-contract WP. Per CONTRACT_FIRST CF-01 / WP-08.5, emit a "
            f"`kind: contract` WP first; producer + consumer WPs dependsOn it."
        )

    # Rule 2 — no direct edge between two different implementation kinds.
    for wid, wp in by_id.items():
        kind = str(wp.get("kind", "")).strip().lower()
        if kind not in _IMPL_KINDS or wp.get("prototype") is True:
            continue
        for dep in _as_str_list(wp.get("dependsOn")):
            dep_wp = by_id.get(dep)
            if dep_wp is None:
                continue
            dep_kind = str(dep_wp.get("kind", "")).strip().lower()
            if dep_kind in _IMPL_KINDS and dep_kind != kind:
                violations.append(
                    f"{wid} (kind: {kind}) dependsOn {dep} (kind: {dep_kind}) "
                    f"directly — cross-kind deps MUST route through the data "
                    f"contract WP, not the other implementation (CF-05)."
                )
    return violations


# ─── Repository contract (RC v0.3.0 profile model) — L-05 ───────────────
#
# Promoted from wpx-arrival-check._read_contract so the pipeline, the train,
# AND the arrival check all read the contract through ONE parser. A duplicated
# parser drifting from its twin is exactly the bug class that produced L-02 —
# arrival-check now delegates here. Stdlib-only, indentation-aware enough for
# the well-formed contract shape.

_RC_DEPLOYABLE_ARTIFACT_TYPE = "deployable-web-app"


def _rc_strip_value(raw: str) -> str:
    """Strip an inline `# comment` and surrounding whitespace from a value."""
    return raw.split(" #", 1)[0].strip()


def read_repo_contract(repo_root: Path) -> dict:
    """Parse `.sulis/repo-contract.yml` into a normalised dict.

    Returns {profile, contribution_model, artifacts: [{name, type}],
    deploy_target}. A missing file returns the all-None/empty shape (callers
    treat that as the strict deployable default).
    """
    result: dict = {
        "profile": None, "contribution_model": None,
        "artifacts": [], "deploy_target": None,
    }
    contract = Path(repo_root) / ".sulis" / "repo-contract.yml"
    if not contract.is_file():
        return result

    in_artifacts = False
    cur: dict | None = None
    for line in contract.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        top_level = not line[:1].isspace()
        if top_level:
            in_artifacts = False
            if stripped.startswith("profile:"):
                result["profile"] = _rc_strip_value(stripped.split(":", 1)[1]) or None
            elif stripped.startswith("contribution_model:"):
                result["contribution_model"] = _rc_strip_value(stripped.split(":", 1)[1]) or None
            elif stripped.startswith("deploy_target:"):
                result["deploy_target"] = _rc_strip_value(stripped.split(":", 1)[1]) or None
            elif stripped.startswith("artifacts:"):
                in_artifacts = True
            continue
        if in_artifacts:
            if stripped.startswith("- name:"):
                if cur:
                    result["artifacts"].append(cur)
                cur = {"name": _rc_strip_value(stripped.split(":", 1)[1]), "type": None}
            elif stripped.startswith("name:"):
                if cur:
                    result["artifacts"].append(cur)
                cur = {"name": _rc_strip_value(stripped.split(":", 1)[1]), "type": None}
            elif stripped.startswith("type:") and cur is not None:
                cur["type"] = _rc_strip_value(stripped.split(":", 1)[1])
    if cur:
        result["artifacts"].append(cur)
    return result


def deploy_is_applicable(contract: dict) -> bool:
    """True iff a deploy → health → smoke phase applies to this repo (L-05).

    Only a ``deployable-web-app`` runs a staging deploy poll + health check.
    A ``published-artifact`` (this marketplace) or ``internal-tool`` ships
    without one; ``deploy_target: none`` is the explicit opt-out. An unset
    profile defaults to deployable (strict — matches arrival-check's
    backward-compat default). Multi-artifact → True iff ANY artifact is
    deployable.
    """
    if (contract.get("deploy_target") or "").strip().lower() == "none":
        return False
    artifacts = contract.get("artifacts") or []
    if artifacts:
        return any(
            (a.get("type") or "") == _RC_DEPLOYABLE_ARTIFACT_TYPE
            for a in artifacts
        )
    profile = (contract.get("profile") or "").strip()
    if not profile:
        return True  # strict default = deployable-web-app
    return profile == _RC_DEPLOYABLE_ARTIFACT_TYPE


# ─── Free-plan branch-protection predicate (HD-003/HD-004) ──────────────────
#
# GitHub's protection API returns this body (on stderr via `gh`) when a repo
# is private on the free plan — branch protection is unavailable ON THE PLAN,
# not merely unconfigured. Stable enough to match on; if GitHub changes the
# wording the tests pin the expectation and the failure is loud (HD-003).
#
# Promoted here (CLAUDE.md #2 extract-now) once a SECOND caller appeared:
# wpx-arrival-check's RC-02 check (HD-003) and wpx-preflight's
# protection-status subcommand (HD-004) both classify the same 403. One home
# so the free-plan vs unconfigured distinction can never drift between the
# arrival-check surface and the per-run/per-ship surface.

_FREEPLAN_403_MARKER = "upgrade to github pro"


def is_freeplan_protection_403(rc: int, stderr: str) -> bool:
    """True when the branch-protection API was unavailable because the repo is
    private on the free plan (403 'Upgrade to GitHub Pro…'), as opposed to a
    genuine missing/misconfigured protection on a protection-capable repo."""
    return rc != 0 and _FREEPLAN_403_MARKER in (stderr or "").lower()


def find_section(text: str, heading: str) -> tuple[int, int]:
    """Find the byte range of a Markdown section by heading.

    Returns (start, end) where start is the first char of the section's
    heading line and end is one past the last char before the next heading
    of equal-or-higher level (or EOF).

    Raises ValueError if the heading is not found.
    """
    # Match "## Heading" or "# Heading" — derive level from input
    level = 0
    for ch in heading:
        if ch == "#":
            level += 1
        else:
            break
    title = heading[level:].strip()
    pattern = re.compile(
        rf"^(#{{{level}}}) {re.escape(title)}\s*$",
        re.MULTILINE,
    )
    match = pattern.search(text)
    if not match:
        raise ValueError(f"Section not found: {heading}")
    start = match.start()
    # Find next heading of equal or higher level
    next_pattern = re.compile(
        rf"^#{{1,{level}}} \S",
        re.MULTILINE,
    )
    next_match = next_pattern.search(text, pos=match.end())
    end = next_match.start() if next_match else len(text)
    return start, end


def replace_section(text: str, heading: str, new_content: str) -> str:
    """Replace a section's content (everything after the heading line, up to next heading).

    new_content should NOT include the heading itself.
    """
    start, end = find_section(text, heading)
    # Find end of heading line
    nl = text.index("\n", start) + 1
    return text[:nl] + new_content + (text[end:] if end < len(text) else "")


# ─────────────────────────────────────────────────────────────────────────
# Pipeline helpers (shell, gh API, CI poll, rebase, merge, deploy, health, smoke)
# ─────────────────────────────────────────────────────────────────────────
#
# Shared between wpx-pipeline (per-WP path) and wpx-train (per-batch path).
# Both CLIs import these so the gh / git / polling primitives stay in
# one place. The CLI scripts themselves contain only state-machine logic
# specific to their dispatch shape.
#


# --- Constants -----------------------------------------------------------

CI_DEFAULT_INTERVAL = 300     # 5 min
CI_DEFAULT_CAP = 45 * 60      # 45 min

DEPLOY_DEFAULT_INTERVAL = 300  # 5 min
DEPLOY_DEFAULT_CAP = 60 * 60   # 60 min — raised from 30 in v0.15.2 after a real
                               # platform-repo deploy took ~35 min, triggered
                               # ADR-212 revert even though the deploy actually
                               # succeeded. Override via --deploy-cap.

HEALTH_MIN_INTERVAL = 60       # 1 min initial
HEALTH_MAX_INTERVAL = 300      # 5 min cap (exponential backoff)
HEALTH_DEFAULT_CAP = 10 * 60   # 10 min total

REBASE_BUDGET = 2              # GIT-05 step-4

# Conventional Commits branch prefixes that branch-CI workflows
# typically gate on. Used by _has_branch_ci_trigger to decide whether
# a `branches:` list item in a workflow YAML targets feature branches.
_BRANCH_CI_PREFIXES = (
    "feat/", "fix/", "chore/", "refactor/", "docs/",
    "test/", "perf/", "build/", "ci/", "style/", "revert/",
)

_URL_RE = re.compile(r"https?://[^\s'\"`]+")


# --- Branch-CI detection -------------------------------------------------

def _matches_cc_prefix(value: str) -> bool:
    """True if a `branches:` list entry targets a Conventional Commits
    feature prefix (feat/**, fix/*, chore/foo, etc.).
    """
    v = value.strip().strip("'\"")
    return any(v.startswith(p) for p in _BRANCH_CI_PREFIXES)


def _has_branch_ci_trigger(text: str) -> bool:
    """Inspect a GitHub Actions workflow YAML for a real branch-CI trigger.

    Looks specifically for `branches:` declarations under `on.push` or
    `on.pull_request`, and checks whether ANY listed branch glob matches
    a Conventional Commits prefix. Rejects `branches-ignore:`, `paths:`,
    `paths-ignore:`, `tags:`, comments, and any other location where a
    substring like `docs/` might legitimately appear without indicating
    branch CI.

    The v0.10.5 version used a naked substring grep, which produced
    false positives on workflows like:

        on:
          push:
            branches: [dev]
            paths-ignore:
              - 'docs/**'        # ← `docs/` matched the substring grep

    Now we walk the YAML line-by-line. When we hit a `branches:` line,
    we either:
      - parse the inline list (`branches: ['feat/**', 'main']`), or
      - scan the following lines at deeper indent for `- 'feat/**'`
        style list items.

    `branches-ignore:` is explicitly excluded (an "ignore" list means
    the workflow does NOT run on those branches — opposite of branch CI).

    Returns True iff at least one workflow has a `branches:` (under
    `on.push` or `on.pull_request`) listing a Conventional Commits
    prefix glob.
    """
    lines = text.splitlines()
    n = len(lines)
    i = 0
    while i < n:
        line = lines[i]
        # Match `<indent>branches:` (NOT branches-ignore, paths, tags)
        m = re.match(r"^(\s*)branches\s*:\s*(.*?)\s*$", line)
        # Skip `branches-ignore:` / commented lines
        if not m or line.lstrip().startswith("#"):
            i += 1
            continue
        indent = m.group(1)
        rest = m.group(2).rstrip()

        # Inline list: `branches: ['feat/**', 'main']` or `branches: [feat/**]`
        if rest.startswith("[") and rest.endswith("]"):
            inner = rest[1:-1]
            items = [it.strip() for it in inner.split(",") if it.strip()]
            if any(_matches_cc_prefix(it) for it in items):
                return True
            i += 1
            continue

        # Single inline value: `branches: feat/**`
        if rest and not rest.startswith("#"):
            if _matches_cc_prefix(rest):
                return True
            i += 1
            continue

        # Block list: scan following indented lines for list items
        j = i + 1
        base_indent = len(indent)
        while j < n:
            nl = lines[j]
            if not nl.strip():
                j += 1
                continue
            nl_indent = len(nl) - len(nl.lstrip())
            if nl_indent <= base_indent:
                break  # dedented out of the list
            # Match `<indent>- '<value>'` or `<indent>- <value>`
            lm = re.match(r"^\s*-\s*(.+?)\s*$", nl)
            if lm and _matches_cc_prefix(lm.group(1)):
                return True
            j += 1
        i = j

    return False


def _detect_branch_ci(worktree: Path) -> bool:
    """Detect whether the project has branch CI configured.

    For GitHub Actions: inspects `.github/workflows/*.y[a]ml` for
    structural `branches:` declarations under `on.push` /
    `on.pull_request` (NOT `branches-ignore`, `paths`, `paths-ignore`).
    Returns True iff at least one such declaration lists a Conventional
    Commits prefix glob (`feat/**`, `fix/**`, etc.).

    For GitLab CI: falls back to a coarser substring grep on
    `.gitlab-ci.yml` since GitLab's rule syntax varies. May produce
    false positives on GitLab; refine when needed.

    Used by wpx-pipeline / wpx-train to decide whether to skip CI
    polling (no branch CI → poll would hang waiting for check-runs
    that never appear).
    """
    gh = worktree / ".github" / "workflows"
    if gh.exists() and gh.is_dir():
        for yml in list(gh.glob("*.yml")) + list(gh.glob("*.yaml")):
            try:
                text = yml.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if _has_branch_ci_trigger(text):
                return True
    gitlab = worktree / ".gitlab-ci.yml"
    if gitlab.exists() and gitlab.is_file():
        try:
            text = gitlab.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            text = ""
        # GitLab fallback: coarser check; refine with proper rule parsing
        # if GitLab false-positives become a problem.
        if any(p in text for p in _BRANCH_CI_PREFIXES):
            return True
    return False


# --- Logging + shell -----------------------------------------------------

def _log(msg: str) -> None:
    """Progress log to stderr so the calling session can tail it if desired."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{ts}] {msg}", file=sys.stderr, flush=True)


def _run(cmd: list[str], cwd: Path | None = None,
         timeout: int = 60) -> tuple[int, str, str]:
    """Run a shell command; return (rc, stdout, stderr). 124 on timeout."""
    try:
        proc = subprocess.run(  # noqa: S603
            cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"Timeout after {timeout}s"


# --- GHClient protocol (HD-005) ------------------------------------------
#
# The train + pipeline + helpers reach GitHub through ten distinct
# `_run(["gh", ...])` callsites scattered across this module. Without a
# named seam between "what we ask of GitHub" and "how we ask it (shell-out
# to gh)", integration tests have to monkeypatch every helper one at a
# time, and the merge-queue strategy dispatcher landing in HD-001 has
# nowhere clean to swap in a fake.
#
# The Protocol below defines the surface; `RealGHClient` is the production
# adapter (each method is the existing shell-out, moved verbatim). The
# helpers below the Protocol gain an optional `gh: GHClient | None = None`
# parameter — when unset they delegate to a module-level singleton,
# preserving every existing callsite without change.
#
# This is EXPAND-Create over an external subject (the gh CLI / GitHub API),
# not Wrap over internal code; the Protocol is owned by this module and
# the gh CLI is *called by* RealGHClient, not wrapped at the architecture
# level. See HD-005.


@runtime_checkable
class GHClient(Protocol):
    """The GitHub-API surface the train and pipeline depend on.

    Methods correspond one-to-one with the ten distinct ``gh`` shell-outs
    historically scattered across this module. Each returns parsed JSON
    (or a string SHA) and raises ``RuntimeError`` on failure — matching
    the existing helpers' contract so callers don't need to special-case
    real vs fake clients.

    Test doubles implement this Protocol to drive train scenarios
    deterministically; see scripts/tests/integration/testbed.py
    (FakeGHClient) per HD-002.
    """

    def check_runs(self, repo: str, branch: str) -> dict:
        """Return the JSON envelope from ``gh api repos/{repo}/commits/{branch}/check-runs``."""
        ...

    def branch_sha(self, repo: str, branch: str) -> str:
        """Return the head commit SHA of ``branch`` via ``gh api .../git/refs/heads/{branch}``."""
        ...

    def ref_sha(self, repo: str, ref: str) -> str:
        """Return the SHA at ``ref`` via ``gh api .../git/refs/heads/{ref}``."""
        ...

    def compare(self, repo: str, base: str, head: str) -> dict:
        """Return ``gh api repos/{repo}/compare/{base}...{head}`` as parsed JSON."""
        ...

    def merge(self, repo: str, base: str, head: str, commit_message: str) -> str:
        """Squash-merge ``head`` into ``base`` via ``gh api -X POST .../merges``; return merge SHA."""
        ...

    def deploy_runs(self, repo: str, workflow: str, commit: str) -> list[dict]:
        """List workflow runs for ``commit`` via ``gh run list``."""
        ...

    def delete_branch(self, repo: str, branch: str) -> None:
        """Delete the remote ``branch`` via ``gh api -X DELETE .../git/refs/heads/{branch}``.

        Best-effort; never raises (matches the pre-HD-005 behaviour of
        ``_merge_squash``'s post-merge branch delete).
        """
        ...

    def branch_exists(self, repo: str, branch: str) -> bool:
        """True if origin/{branch} exists. Best-effort; returns False on gh error."""
        ...

    def list_matching_branches(self, repo: str, pattern: str) -> list[dict]:
        """List origin branches whose names match ``pattern`` (e.g. ``feat/wp-008-*``).

        Returns a list of ``{"name": str, "committerdate": ISO8601 str}`` dicts
        — empty list when none match or gh errors (best-effort, matching the
        ``branch_exists`` contract). Order is not guaranteed; callers that
        want a specific order should sort by ``committerdate``.

        Used by ``resolve_wp_branch`` to tolerate executor-side slug drift
        (a WP file ``WP-NNN-long-slug.md`` whose pushed branch is
        ``feat/wp-NNN-short-slug``). The shape is intentionally minimal —
        we only need the branch name and a recency hint to disambiguate
        when multiple candidates exist.
        """
        ...

    def clone(self, repo: str, dest: Path) -> tuple[int, str]:
        """Clone ``repo`` to ``dest`` via ``gh repo clone --depth 100``.

        Returns ``(rc, stderr)`` so callers can fall back to a direct
        ``git clone`` on failure (preserves ``clone_repo_to_temp``'s
        existing fallback shape).
        """
        ...


class RealGHClient:
    """Production GHClient — every method shells out to the ``gh`` CLI.

    The bodies are byte-for-byte the same subprocess invocations the
    pre-HD-005 ``_gh_*`` helpers used. This class is the *only* place that
    knows about the shape of the ``gh`` command line; everything else
    talks to the GHClient Protocol.

    Stateless. Constructed once at module load as ``_default_gh_client``;
    constructed again ad-hoc only in tests.
    """

    def check_runs(self, repo: str, branch: str) -> dict:
        rc, out, err = _run(
            ["gh", "api", f"repos/{repo}/commits/{branch}/check-runs",
             "--paginate"],
            timeout=30,
        )
        if rc != 0:
            raise RuntimeError(f"gh check-runs failed: {err}")
        return json.loads(out) if out.strip() else {"check_runs": []}

    def branch_sha(self, repo: str, branch: str) -> str:
        rc, out, err = _run(
            ["gh", "api", f"repos/{repo}/git/refs/heads/{branch}"], timeout=30,
        )
        if rc != 0:
            raise RuntimeError(f"gh branch-sha failed for {branch}: {err}")
        return json.loads(out)["object"]["sha"]

    def ref_sha(self, repo: str, ref: str) -> str:
        rc, out, err = _run(
            ["gh", "api", f"repos/{repo}/git/refs/heads/{ref}"], timeout=30,
        )
        if rc != 0:
            raise RuntimeError(f"gh ref-sha failed for {ref}: {err}")
        return json.loads(out)["object"]["sha"]

    def compare(self, repo: str, base: str, head: str) -> dict:
        rc, out, err = _run(
            ["gh", "api", f"repos/{repo}/compare/{base}...{head}"],
            timeout=30,
        )
        if rc != 0:
            # HD-013: include rc in the message so callers can distinguish
            # auth-expired, rate-limit, network-blip from each other in logs.
            raise RuntimeError(f"gh compare failed (rc={rc}): {err}")
        if not out.strip():
            # HD-013: restore the diagnostic log lost in HD-005's extraction.
            _log(
                f"compare API returned empty output for "
                f"{base}...{head} on {repo}; returning empty dict"
            )
            return {}
        try:
            return json.loads(out)
        except json.JSONDecodeError:
            # HD-013: restore the diagnostic log for non-JSON output.
            preview = out[:200] + ("..." if len(out) > 200 else "")
            _log(
                f"compare API returned non-JSON for {base}...{head} "
                f"on {repo}; returning empty dict. out: {preview!r}"
            )
            return {}

    def merge(self, repo: str, base: str, head: str, commit_message: str) -> str:
        rc, out, err = _run(
            ["gh", "api", "-X", "POST", f"repos/{repo}/merges",
             "-f", f"base={base}", "-f", f"head={head}",
             "-f", f"commit_message={commit_message}",
             "-F", "merge_method=squash"],
            timeout=60,
        )
        if rc != 0:
            raise RuntimeError(f"gh merges failed: {err}\nstdout={out}")
        return json.loads(out)["sha"]

    def deploy_runs(self, repo: str, workflow: str, commit: str) -> list[dict]:
        rc, out, err = _run(
            ["gh", "run", "list", "--workflow", workflow, "--commit", commit,
             "--json", "databaseId,status,conclusion,createdAt,url",
             "--limit", "5"],
            timeout=30,
        )
        if rc != 0:
            raise RuntimeError(f"gh run list failed: {err}")
        return json.loads(out) if out.strip() else []

    def delete_branch(self, repo: str, branch: str) -> None:
        # Best-effort; matches the pre-HD-005 fire-and-forget shape in
        # _merge_squash. We swallow errors here so a failed branch-delete
        # doesn't mask a successful merge.
        _run(
            ["gh", "api", "-X", "DELETE",
             f"repos/{repo}/git/refs/heads/{branch}"],
            timeout=30,
        )

    def branch_exists(self, repo: str, branch: str) -> bool:
        rc, out, _err = _run(
            ["gh", "api", f"repos/{repo}/git/refs/heads/{branch}"],
            timeout=30,
        )
        return rc == 0 and bool(out.strip())

    def list_matching_branches(self, repo: str, pattern: str) -> list[dict]:
        # Translate the shell-glob pattern (``feat/wp-008-*``) into a
        # ref-prefix lookup. The GitHub API's ``git/matching-refs`` endpoint
        # accepts the literal prefix; the trailing ``*`` is implicit.
        prefix = pattern.rstrip("*").rstrip("/")
        rc, out, _err = _run(
            ["gh", "api", f"repos/{repo}/git/matching-refs/heads/{prefix}",
             "--paginate"],
            timeout=30,
        )
        if rc != 0 or not out.strip():
            return []
        try:
            refs = json.loads(out)
        except json.JSONDecodeError:
            return []
        if not isinstance(refs, list):
            return []
        results: list[dict] = []
        # Best-effort committer-date fetch per ref so callers can pick
        # the most-recently-pushed match. We fetch the commit object for
        # each SHA; the list is typically tiny (1-3 candidates per WP).
        for ref in refs:
            name = ref.get("ref", "").removeprefix("refs/heads/")
            sha = ref.get("object", {}).get("sha")
            committerdate = ""
            if sha:
                rc2, out2, _ = _run(
                    ["gh", "api", f"repos/{repo}/git/commits/{sha}"],
                    timeout=30,
                )
                if rc2 == 0 and out2.strip():
                    try:
                        commit = json.loads(out2)
                        committerdate = (
                            commit.get("committer", {}).get("date", "")
                        )
                    except json.JSONDecodeError:
                        pass
            if name:
                results.append({"name": name, "committerdate": committerdate})
        return results

    def clone(self, repo: str, dest: Path) -> tuple[int, str]:
        rc, _out, err = _run(
            ["gh", "repo", "clone", repo, str(dest), "--", "--depth", "100"],
            timeout=120,
        )
        return rc, err


# Module-level singleton. Helpers below use this when no explicit
# `gh` parameter is passed. Tests can swap it via monkeypatch (the
# TrainTestbed fixture does so in scripts/tests/integration/testbed.py).
_default_gh_client: GHClient = RealGHClient()


def _resolve_gh(gh: GHClient | None) -> GHClient:
    """Return the caller's gh client, or the module default if None.

    Tiny helper used by every shim below; centralising the resolution
    means tests can monkeypatch `_default_gh_client` in one place if they
    want to swap the default without rewriting every callsite.
    """
    return gh if gh is not None else _default_gh_client


# --- gh API helpers ------------------------------------------------------
#
# These shims preserve the pre-HD-005 public surface (function names,
# positional signatures). Each accepts an optional `gh: GHClient | None`
# kw-arg so tests can inject a fake without monkeypatching every helper;
# default behaviour (no gh passed) is unchanged.

def _gh_check_runs(repo: str, branch: str,
                   *, gh: GHClient | None = None) -> dict:
    """Return list of latest check-runs for the branch's HEAD commit."""
    return _resolve_gh(gh).check_runs(repo, branch)


def _gh_branch_sha(repo: str, branch: str,
                   *, gh: GHClient | None = None) -> str:
    return _resolve_gh(gh).branch_sha(repo, branch)


def _gh_ref_sha(repo: str, ref: str,
                *, gh: GHClient | None = None) -> str:
    """Get SHA for any ref (e.g., dev)."""
    return _resolve_gh(gh).ref_sha(repo, ref)


def _gh_branch_already_merged(repo: str, branch: str, base: str = "main",
                              *, gh: GHClient | None = None) -> tuple[bool, str]:
    """Check whether `branch` is already fully merged into `base`.

    Uses GitHub's compare API: `gh api repos/{repo}/compare/{base}...{branch}`
    which returns a `status` field with one of:

      - `"identical"` — branch HEAD == base HEAD; already merged (squash or ff)
      - `"behind"`   — base has commits beyond branch; branch has no commits to merge
      - `"ahead"`    — branch has commits beyond base; needs merge (normal case)
      - `"diverged"` — both have unique commits; needs rebase before merge

    Returns (already_merged, base_sha). When already_merged, the caller
    should skip _gh_merge and proceed using base_sha as the merge SHA
    (no new commit is needed; the work is already on dev).

    Returns (False, "") for `ahead` / `diverged` / errors — the caller
    should proceed with the normal merge path.

    v0.10.5 — fixes the pre-existing bug where re-running wpx-pipeline
    on an already-merged branch would crash with RuntimeError from
    _gh_merge (POST /merges returns 409 when base already contains head).
    """
    client = _resolve_gh(gh)
    try:
        data = client.compare(repo, base, branch)
    except RuntimeError as exc:
        _log(
            f"compare API failed; falling through to normal merge path. "
            f"err: {exc}"
        )
        return False, ""
    if not isinstance(data, dict):
        _log(f"compare API returned non-dict; falling through. data: {data!r}")
        return False, ""
    status = data.get("status", "")
    if status in ("identical", "behind"):
        # Already merged. Fetch the current base HEAD as the merge SHA.
        try:
            base_sha = client.ref_sha(repo, base)
        except RuntimeError:
            base_sha = ""
        return True, base_sha
    return False, ""


def _gh_merge(repo: str, base: str, head: str, commit_message: str,
              *, gh: GHClient | None = None) -> str:
    """Squash-merge head into base via the merges endpoint. Returns merge SHA."""
    return _resolve_gh(gh).merge(repo, base, head, commit_message)


def _gh_deploy_runs(repo: str, workflow: str, commit: str,
                    *, gh: GHClient | None = None) -> list[dict]:
    return _resolve_gh(gh).deploy_runs(repo, workflow, commit)


# --- Phase implementations ----------------------------------------------

def _preflight_ci_conclusion(
    repo: str, branch: str, *, gh: GHClient | None = None,
) -> tuple[str, list[str]]:
    """Read branch HEAD's CURRENT recorded CI conclusion. No polling.

    Returns ``(verdict, failed_check_names)`` where verdict is one of a
    closed set:

      - ``"green"``,   ``[]``            — every completed run is in the pass
                                           set (success / neutral / skipped)
      - ``"failed"``,  ``[name, ...]``   — >=1 completed run is NOT in the
                                           pass set; names are returned so a
                                           caller can say "dev has N failures"
      - ``"pending"``, ``[]``            — runs exist but not all are
                                           completed (returned immediately —
                                           this helper never waits)
      - ``"unknown"``, ``[]``            — no check-runs recorded for this
                                           HEAD yet

    Faithful by construction: it reads GitHub's *recorded* conclusion for
    the workflow GitHub actually ran, so build/prepare order fidelity is
    inherited for free — there is no local re-run to drift from CI. Reads
    each run's ``conclusion`` EXPLICITLY (lesson #59) — never a chained
    exit code, so a build-step failure after a "completed" status cannot
    read as green.

    Reuses ``_gh_check_runs`` (the ``GHClient.check_runs`` port); it does
    NOT re-read CI by any other mechanism. The ``gh`` keyword is the
    existing injection seam for tests — no monkeypatching of internals.

    Distinct from ``_poll_ci`` on purpose: ``_poll_ci`` serves the train's
    wait-then-verdict need (it sleeps until in-flight runs complete, then
    returns ``green``/``failed``/``timeout``); this pre-flight read wants
    the latest *recorded* conclusion cheaply, with no wait, plus the failed
    names. The pass-set predicate is intentionally duplicated rather than
    shared: the train verdict and the pre-flight verdict are independently
    calibrated and must be free to diverge. If/when a third caller appears,
    extract a shared ``_classify_check_runs`` then — not now (two callers,
    deliberate independence).
    """
    runs = _gh_check_runs(repo, branch, gh=gh)["check_runs"]
    if not runs:
        return "unknown", []
    statuses = [(r["name"], r["status"], r["conclusion"]) for r in runs]
    if not all(s[1] == "completed" for s in statuses):
        return "pending", []
    _PASS = ("success", "neutral", "skipped")
    failed = [s[0] for s in statuses if s[2] not in _PASS]
    return ("green", []) if not failed else ("failed", failed)


def _poll_ci(repo: str, branch: str, interval: int, cap: int) -> str:
    """Poll CI on branch HEAD; return verdict 'green'|'failed'|'timeout'."""
    elapsed = 0
    last_status = "unknown"
    while elapsed < cap:
        runs = _gh_check_runs(repo, branch)["check_runs"]
        if not runs:
            _log(f"CI poll: no check-runs yet for {branch} (elapsed {elapsed}s)")
        else:
            statuses = [(r["name"], r["status"], r["conclusion"]) for r in runs]
            all_done = all(s[1] == "completed" for s in statuses)
            if all_done:
                if all(s[2] == "success" or s[2] == "neutral"
                       or s[2] == "skipped" for s in statuses):
                    _log(f"CI poll: all checks green ({len(statuses)} runs)")
                    return "green"
                failed = [s for s in statuses if s[2] not in
                          ("success", "neutral", "skipped")]
                _log(f"CI poll: failed checks: {failed}")
                return "failed"
            in_flight = [s[0] for s in statuses if s[1] != "completed"]
            last_status = f"in_flight={in_flight}"
            _log(f"CI poll: {last_status} (elapsed {elapsed}s)")
        time.sleep(interval)
        elapsed += interval
    _log(f"CI poll: TIMEOUT after {cap}s; last status: {last_status}")
    return "timeout"


def _rebase_on_dev(repo: str, branch: str, worktree: Path,
                   dev_sha_at_creation: str,
                   base_branch: str = "main") -> tuple[bool, str]:
    """If base_branch advanced past dev_sha_at_creation, rebase. Return (rebased, new_sha).

    `base_branch` parameterises the rebase target — defaults to "dev" for
    backward compatibility, but per CW-04 the executor inside a change
    worktree passes the change branch name here so the rebase target is
    the change branch's HEAD, not origin/dev.
    """
    current_base = _gh_ref_sha(repo, base_branch)
    if current_base == dev_sha_at_creation:
        return False, ""
    _log(f"{base_branch} advanced from {dev_sha_at_creation[:8]} to {current_base[:8]}; rebasing")
    rc, _, err = _run(["git", "fetch", "origin", base_branch], cwd=worktree)
    if rc != 0:
        raise RuntimeError(f"git fetch failed: {err}")
    rc, _, err = _run(["git", "rebase", f"origin/{base_branch}"], cwd=worktree)
    if rc != 0:
        _run(["git", "rebase", "--abort"], cwd=worktree)
        raise RuntimeError(f"git rebase failed: {err}")
    rc, _, err = _run(
        ["git", "push", "--force-with-lease", "origin", branch],
        cwd=worktree,
    )
    if rc != 0:
        raise RuntimeError(f"git push --force-with-lease failed: {err}")
    rc, out, _ = _run(["git", "rev-parse", "HEAD"], cwd=worktree)
    return True, out.strip()


def _merge_squash(repo: str, branch: str, wp: str,
                  base_branch: str = "main",
                  *, gh: GHClient | None = None) -> str:
    """Squash-merge branch into base_branch. Return merge SHA on base_branch.

    `base_branch` defaults to "dev" for backward compatibility, but per
    CW-04 the executor inside a change worktree passes the change branch
    name here so the merge target is the change branch, not dev.
    """
    client = _resolve_gh(gh)
    msg = f"feat({wp.lower()}): squash-merge from {branch}"
    sha = client.merge(repo, base=base_branch, head=branch, commit_message=msg)
    # Delete remote branch (best-effort; matches pre-HD-005 fire-and-forget).
    client.delete_branch(repo, branch)
    return sha


def _poll_deploy(repo: str, workflow: str, merge_sha: str,
                 interval: int, cap: int) -> tuple[str, str]:
    """Poll deploy workflow for merge_sha. Return (verdict, deploy_url)."""
    elapsed = 0
    while elapsed < cap:
        runs = _gh_deploy_runs(repo, workflow, merge_sha)
        if runs:
            r = runs[0]
            url = r.get("url", "")
            status = r.get("status")
            conclusion = r.get("conclusion")
            _log(f"Deploy poll: status={status} conclusion={conclusion} (elapsed {elapsed}s)")
            if status == "completed":
                if conclusion == "success":
                    return "green", url
                return f"failed({conclusion})", url
        else:
            _log(f"Deploy poll: no run yet for {merge_sha[:8]} (elapsed {elapsed}s)")
        time.sleep(interval)
        elapsed += interval
    _log(f"Deploy poll: TIMEOUT after {cap}s")
    return "timeout", ""


# --- Health path resolution ---------------------------------------------

def _extract_health_path_from_smoke(smoke_cmd: str) -> str:
    """Return the path component of the first URL in the smoke command.

    Used to auto-detect the health endpoint when the project's
    smoke_test already encodes the right path
    (e.g. `curl -sf https://staging.example.com/health`).

    Returns "" if no URL is found, or "/" if the URL has no path
    beyond the root.

    v0.10.7 — added to fix Step 10a hitting bare staging URL for APIs
    whose root returns 404 (e.g. APIs that only serve health at /health).
    """
    if not smoke_cmd:
        return ""
    # urlparse imported lazily to keep top-of-file imports tight
    from urllib.parse import urlparse

    match = _URL_RE.search(smoke_cmd)
    if not match:
        return ""
    parsed = urlparse(match.group(0))
    return parsed.path or ""


def _join_health_url(base: str, path: str) -> str:
    """Join staging URL + health path; tolerate trailing slashes.

    Examples:
        _join_health_url("https://x.com",  "/health") → "https://x.com/health"
        _join_health_url("https://x.com/", "/health") → "https://x.com/health"
        _join_health_url("https://x.com",  "health")  → "https://x.com/health"
        _join_health_url("https://x.com/", "")        → "https://x.com/"
    """
    if not path:
        return base.rstrip("/") + "/"
    return base.rstrip("/") + ("" if path.startswith("/") else "/") + path


def _poll_health(url: str, cap: int) -> str:
    """Poll health endpoint with exponential backoff (1m → 5m, capped at cap)."""
    elapsed = 0
    interval = HEALTH_MIN_INTERVAL
    while elapsed < cap:
        rc, out, err = _run(
            ["curl", "-sf", "-o", "/dev/null", "-w", "%{http_code}", url],
            timeout=30,
        )
        if rc == 0 and out.strip() == "200":
            _log(f"Health check: OK at {url} (elapsed {elapsed}s)")
            return "healthy"
        _log(f"Health check: rc={rc} http={out.strip() or '?'} (elapsed {elapsed}s)")
        time.sleep(interval)
        elapsed += interval
        interval = min(interval * 2, HEALTH_MAX_INTERVAL)
    return "unhealthy"


def _run_smoke(cmd: str, cwd: Path) -> tuple[str, str]:
    """Run smoke command (shell). Return (verdict, output_or_reason)."""
    if not cmd or cmd.strip() in ("—", "-", "none", "None"):
        return "PASS", "(no smoke command configured)"
    rc, out, err = _run(["bash", "-lc", cmd], cwd=cwd, timeout=300)
    if rc == 0:
        return "PASS", (out or "").strip()[:500]
    return f"FAIL — exit {rc}", ((err or out) or "").strip()[:500]


# --- Structured result helper -------------------------------------------

def emit_result(result: dict, exit_code: int = 0) -> None:
    """Emit final result line with completed_at timestamp + structured wrapper, then exit.

    Used by wpx-pipeline (per-WP run result) and wpx-train (per-train
    run result). The `result` dict is wrapped under `{"result": ...}`
    so the calling session reads `data.result` consistently across both
    tools.
    """
    if "completed_at" not in result:
        result["completed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    emit_ok(data={"result": result}, exit_code=exit_code)


# ─────────────────────────────────────────────────────────────────────────
# wpx-train helpers — INDEX parsing, eligibility, batching, overrides
# ─────────────────────────────────────────────────────────────────────────
#
# Used by wpx-train (per-batch path). The eligibility algorithm reads
# state that already exists (INDEX.md + origin branches + per-WP CI
# status) rather than maintaining a separate queue file. See ADR-212
# D6 (amended) for the rationale.
#


# Status values that indicate a WP has finished coding (Steps 1-7) and
# is waiting for batched integration (Steps 8-11).
TRAIN_ELIGIBLE_STATUS = "step-7-complete"
TRAIN_HELD_STATUS = "step-7-held"
TRAIN_BLOCKED_STATUS = "step-7-blocked"
TRAIN_DONE_STATUS = "done"  # Steps 8-11 complete; on dev


# WP table header signature. parse_index_md uses this to find tables.
# We match loosely — the WP table is any markdown table whose header
# row begins with `| ID | Title |`.
_WP_TABLE_HEADER_RE = re.compile(
    r"^\|\s*ID\s*\|\s*Title\s*\|", re.MULTILINE
)

# The canonical WP INDEX header — what plan-work's decompose template emits
# and what the lint reports as "expected". Kept here next to the regex so the
# message and the matcher can never drift apart.
CANONICAL_WP_INDEX_HEADER = (
    "| ID | Title | Primitive | Status | Depends On | Blocks |"
)


def validate_wp_index_header(index_text: str) -> str | None:
    """Decompose-time lint: does INDEX.md contain a recognisable WP table?

    Reuses ``_WP_TABLE_HEADER_RE`` — the SAME matcher ``parse_index_md`` uses
    to find tables — so the lint can never disagree with the parser (#60,
    EP-03 single source of truth). A drifted header like
    ``| WP | Title | kind | Primitive | ... |`` is invisible to that regex,
    so the table silently vanishes from the run-all loop (list-ready /
    flip-status fail mid-run with "Could not find WP table"). The lint turns
    that silent mid-run failure into a surgical decompose-time error.

    Returns ``None`` when the INDEX has at least one canonical-headed WP
    table, or an error message naming the expected header when it doesn't.
    """
    if _WP_TABLE_HEADER_RE.search(index_text) is not None:
        return None
    return (
        "INDEX.md has no recognisable WP table — its header must begin "
        f"`{CANONICAL_WP_INDEX_HEADER}` (ID first; no duplicate `kind` "
        "column). A drifted header (e.g. `| WP | Title | kind | "
        "Primitive | ... |`) is invisible to the run-all loop and fails "
        "silently mid-run. Fix the header to the canonical form above."
    )


@dataclass
class WPRow:
    """One Work Package row parsed from an INDEX.md table."""

    id: str
    title: str
    primitive: str = ""
    status: str = ""
    depends_on: list[str] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)
    # Extra columns the parser tolerates without using:
    extras: dict[str, str] = field(default_factory=dict)


def _split_csv_or_dash(cell: str) -> list[str]:
    """Parse a comma-separated list cell. Empty / dash → []."""
    s = cell.strip()
    if not s or s in ("—", "-", "none", "None"):
        return []
    return [item.strip() for item in s.split(",") if item.strip()]


def _normalise_wp_reference(
    ref: str, known_wps: set[str],
) -> tuple[str, str]:
    """Normalise a WP reference to its canonical full ID.

    Used to resolve short names in INDEX.md's "Depends On" / "Blocks"
    columns. Founders commonly write `PERMS, MANIFEST, MCP-STUB`
    instead of `WP-S2-PERMS, WP-S2-MANIFEST, WP-S2-MCP-STUB` for
    visual brevity. Without normalisation, dependency checks compare
    short-vs-full and silently treat deps as not-merged.

    Resolution rules:
    1. Already a full WP ID (starts with `WP-`) → pass through unchanged
    2. Exact match in known_wps → pass through unchanged
    3. Unique suffix match (e.g., `PERMS` matches `WP-S2-PERMS`) → normalise
    4. No match → return original; caller can warn
    5. Ambiguous (multiple suffix matches) → raise ValueError naming candidates

    Returns (normalised_ref, status) where status is one of:
    - "passthrough" — was already full or matched exactly
    - "normalised" — short name resolved to full ID
    - "unknown" — no match in known_wps (kept as-is)
    """
    if ref in known_wps:
        return (ref, "passthrough")
    if ref.startswith("WP-"):
        # Full-looking ID that isn't in known_wps — treat as unknown
        # but pass through (likely a typo or WP not yet added)
        return (ref, "unknown")
    # Short name — look for unique suffix match
    candidates = [
        wp_id for wp_id in known_wps
        if wp_id.endswith(f"-{ref}") or wp_id.endswith(ref)
    ]
    if len(candidates) == 1:
        return (candidates[0], "normalised")
    if len(candidates) == 0:
        return (ref, "unknown")
    # Ambiguous
    raise ValueError(
        f"Ambiguous WP reference {ref!r}: matches multiple WPs "
        f"({', '.join(sorted(candidates))}). Disambiguate in INDEX.md "
        f"by using the full WP ID."
    )


def parse_index_md(
    index_path: Path,
    verbose_normalisations: bool = False,
) -> list[WPRow]:
    """Parse all WP tables in an INDEX.md file. Returns flat list of rows.

    INDEX.md typically contains multiple WP tables — one per section
    (Cross-cutting Armor, Slice 1, Migration track, etc.). This walks
    the document, finds every table whose header begins with `| ID | Title |`,
    and concatenates their rows.

    Recognises the standard columns: ID, Title, Primitive, Status,
    Depends On (or "Depends on"), Blocks. Other columns (Token, TDD §,
    ADR) are tolerated and stored under `extras`.

    Raises FileNotFoundError if the path doesn't exist.
    """
    text = index_path.read_text(encoding="utf-8")
    rows: list[WPRow] = []

    # Find every WP table header position
    for match in _WP_TABLE_HEADER_RE.finditer(text):
        start = match.start()
        # Extract the table block: from header to first blank line or EOF
        end = text.find("\n\n", start)
        if end == -1:
            end = len(text)
        table_text = text[start:end]

        table = parse_md_table(table_text)
        if not table.headers:
            continue

        # Resolve columns once via the shared resolver (L-02): canonical key
        # → index. wpx-index uses the same resolver, so header spelling
        # variants ("Depends On" / "Depends") resolve identically across both.
        col_index = resolve_wp_columns(table.headers)
        resolved_indices = set(col_index.values())

        def get(row: list[str], name: str, default: str = "") -> str:
            i = col_index.get(name)
            if i is None or i >= len(row):
                return default
            return row[i].strip()

        for row in table.rows:
            if not row or not row[0].strip():
                continue
            wp_id = row[0].strip()
            # Skip rows that aren't actually WPs (e.g. summary rows)
            if not wp_id.startswith("WP-"):
                continue

            extras: dict[str, str] = {}
            for i, h in enumerate(table.headers):
                if i in resolved_indices or i >= len(row):
                    continue
                extras[h.strip()] = row[i].strip()

            rows.append(WPRow(
                id=wp_id,
                title=get(row, "title"),
                primitive=get(row, "primitive"),
                status=get(row, "status"),
                depends_on=_split_csv_or_dash(get(row, "depends")),
                blocks=_split_csv_or_dash(get(row, "blocks")),
                extras=extras,
            ))

    # v0.16.2 — normalise short WP references in deps + blocks to full IDs.
    # Without this, founders writing `PERMS, MANIFEST` (instead of
    # `WP-S2-PERMS, WP-S2-MANIFEST`) get silent dep-not-merged failures.
    known_wps = {row.id for row in rows}
    normalised_count = 0
    for row in rows:
        new_deps = []
        for dep in row.depends_on:
            resolved, status = _normalise_wp_reference(dep, known_wps)
            new_deps.append(resolved)
            if status == "normalised":
                normalised_count += 1
                if verbose_normalisations:
                    _log(f"INDEX: normalised dep {dep!r} → {resolved!r} in {row.id}")
            elif status == "unknown" and verbose_normalisations:
                _log(
                    f"INDEX: dep {dep!r} in {row.id} matches no known WP — "
                    f"left as-is (typo or WP not yet added?)"
                )
        row.depends_on = new_deps

        new_blocks = []
        for blk in row.blocks:
            resolved, status = _normalise_wp_reference(blk, known_wps)
            new_blocks.append(resolved)
            if status == "normalised":
                normalised_count += 1
                if verbose_normalisations:
                    _log(f"INDEX: normalised block {blk!r} → {resolved!r} in {row.id}")
        row.blocks = new_blocks

    if normalised_count > 0 and verbose_normalisations:
        _log(
            f"INDEX: normalised {normalised_count} short WP reference(s) "
            f"to full IDs. Consider rewriting INDEX.md to use full IDs for clarity."
        )

    return rows


# --- Overrides (force-include / hold) -----------------------------------

@dataclass
class TrainOverrides:
    """Force-include and hold-back markers for the next train run."""

    includes: list[str] = field(default_factory=list)
    holds: list[str] = field(default_factory=list)


def read_overrides(overrides_path: Path) -> TrainOverrides:
    """Read .architecture/{project}/train-overrides.yaml; tolerate absence.

    File format (YAML-lite, no pyyaml needed):

        includes:
          - WP-X
          - WP-Y
        holds:
          - WP-Z

    Missing file → empty overrides (the common case).
    """
    if not overrides_path.exists():
        return TrainOverrides()
    text = overrides_path.read_text(encoding="utf-8")
    includes: list[str] = []
    holds: list[str] = []
    current: list[str] | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.startswith("#"):
            continue
        if line == "includes:":
            current = includes
            continue
        if line == "holds:":
            current = holds
            continue
        if current is not None and line.startswith("  - "):
            value = line[4:].strip().strip("'\"")
            # Cells may be objects like `{wp: WP-X, reason: "..."}`. Pull the WP.
            if value.startswith("{") and "wp:" in value:
                # Tiny inline-object extraction
                m = re.search(r"wp\s*:\s*([A-Za-z0-9-]+)", value)
                if m:
                    current.append(m.group(1))
            else:
                current.append(value)
    return TrainOverrides(includes=includes, holds=holds)


def write_overrides(overrides_path: Path, overrides: TrainOverrides) -> None:
    """Write the overrides file. Creates parent directory if needed."""
    overrides_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = [
        "# wpx-train overrides — force-include / hold-back markers",
        "# Managed by wpx-train queue-add / queue-remove subcommands.",
        "# Eligibility derives from INDEX.md + origin branches + CI status;",
        "# overrides here are the explicit founder layer on top.",
        "",
    ]
    if overrides.includes:
        lines.append("includes:")
        for wp in overrides.includes:
            lines.append(f"  - {wp}")
        lines.append("")
    if overrides.holds:
        lines.append("holds:")
        for wp in overrides.holds:
            lines.append(f"  - {wp}")
        lines.append("")
    overrides_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --- Eligibility --------------------------------------------------------

@dataclass
class EligibilityResult:
    """One WP's eligibility verdict + reason."""

    wp: str
    branch: str
    eligible: bool
    reason: str
    primitive: str = ""
    forced: bool = False


def _wp_slug_from_file(wp_dir: Path, wp_id: str) -> str | None:
    """Derive the WP's branch slug from its WP file name.

    File convention: `WP-{ID}-{slug}.md`. Returns the slug, or None if
    no matching file exists.
    """
    matches = list(wp_dir.glob(f"{wp_id}-*.md"))
    matches = [
        m for m in matches
        if not m.name.startswith(".")
        and not m.name.startswith("BLOCKER-")
    ]
    if not matches:
        return None
    # Strip "WP-{ID}-" prefix and ".md" suffix
    name = matches[0].stem  # WP-AUTO-018-observability-adapter
    prefix = f"{wp_id}-"
    if not name.startswith(prefix):
        return None
    return name[len(prefix):]


def _branch_name(wp_id: str, slug: str) -> str:
    """Compose the feature-branch name from WP id + slug.

    Convention: `feat/wp-{id-lower}-{slug}`.
    """
    return f"feat/wp-{wp_id.lower().removeprefix('wp-')}-{slug}"


def _gh_branch_exists(repo: str, branch: str,
                      *, gh: GHClient | None = None) -> bool:
    """True if origin/{branch} exists. Best-effort; returns False on gh error."""
    return _resolve_gh(gh).branch_exists(repo, branch)


def _gh_list_matching_branches(
    repo: str, pattern: str, *, gh: GHClient | None = None,
) -> list[dict]:
    """List origin branches matching ``pattern`` (e.g. ``feat/wp-008-*``).

    Shim over ``GHClient.list_matching_branches`` so callers can monkeypatch
    this single function in tests (the same pattern used by
    ``_gh_branch_exists`` and ``_gh_branch_ci_green``).
    """
    return _resolve_gh(gh).list_matching_branches(repo, pattern)


def resolve_wp_branch(
    wp_id: str,
    repo: str,
    wp_dir: Path,
    *,
    gh: GHClient | None = None,
) -> str | None:
    """Resolve the feat-branch on origin that belongs to ``wp_id``.

    The historical contract (literal slug → branch name) breaks when the
    executor pushes a branch with a SHORTER slug than the WP filename
    expresses (an observed drift class — see the WP-008 / WP-010 / WP-011
    cases from the release-train-as-entities run). This helper restores
    eligibility on the READ side without forcing executors to use full slugs.

    Resolution order:

      1. **Slug-literal match.** If ``feat/wp-NNN-<slug-from-file>`` exists
         on origin, return it. Byte-for-byte preservation of the
         historical happy path.
      2. **Fuzzy single match.** If exactly one ``feat/wp-NNN-*`` branch
         exists on origin (NNN being ``wp_id`` minus the WP- prefix,
         lowercased), return it. A warning is emitted to stderr naming
         the WP, the expected literal, and the actual branch so the
         operator can see the drift.
      3. **Fuzzy multi-match.** Two or more ``feat/wp-NNN-*`` candidates →
         most-recent-by-``committerdate`` wins. The same warning fires,
         plus an explicit "ambiguous" note listing all candidates.
      4. **Zero candidates.** Return ``None``. The caller falls through
         to whatever "branch missing" handling it already had.

    Returns the branch name (no leading ``refs/heads/``) or ``None``.
    """
    slug = _wp_slug_from_file(wp_dir, wp_id)
    if slug is None:
        # No WP file → caller already handles this case via its own
        # "no WP file found" branch. Return None to be consistent.
        return None

    literal = _branch_name(wp_id, slug)
    # Only forward ``gh`` when the caller explicitly supplied one; passing
    # ``gh=None`` to the shims would break test monkeypatches that don't
    # accept the kw-arg (the existing test_wpx_train_eligibility.py stubs
    # use a 2-positional signature, and the shim's ``gh=None`` default
    # already routes to the module singleton).
    if gh is None:
        if _gh_branch_exists(repo, literal):
            return literal
    else:
        if _gh_branch_exists(repo, literal, gh=gh):
            return literal

    # Fuzzy lookup. Strip the WP- prefix and lowercase per _branch_name.
    nnn = wp_id.lower().removeprefix("wp-")
    pattern = f"feat/wp-{nnn}-*"
    if gh is None:
        matches = _gh_list_matching_branches(repo, pattern)
    else:
        matches = _gh_list_matching_branches(repo, pattern, gh=gh)
    if not matches:
        return None

    # Pick most-recent by committerdate. Empty/missing dates sort first
    # so any branch with a real date wins (the typical case is one
    # branch with a date and zero without).
    chosen = max(matches, key=lambda m: m.get("committerdate", ""))
    chosen_name = chosen["name"]

    if len(matches) == 1:
        _log(
            f"resolve_wp_branch: {wp_id} — expected '{literal}' on origin "
            f"but found '{chosen_name}' (fuzzy match). Using '{chosen_name}'. "
            f"Rename the WP file or the branch to silence this warning."
        )
    else:
        names = ", ".join(m["name"] for m in matches)
        _log(
            f"resolve_wp_branch: {wp_id} — expected '{literal}' but found "
            f"{len(matches)} candidates [{names}]; picked '{chosen_name}' "
            f"(most recent by committerdate). Choice may be ambiguous; "
            f"rename to disambiguate."
        )
    return chosen_name


def _gh_branch_ci_green(repo: str, branch: str) -> bool:
    """True if the branch's most recent CI run is green / completed-success.

    Returns False if checks are pending, failed, or absent. Pending checks
    are treated as "not green" — the train waits for them to complete on a
    future invocation.
    """
    try:
        data = _gh_check_runs(repo, branch)
    except RuntimeError:
        return False
    runs = data.get("check_runs", [])
    if not runs:
        # No CI configured → degenerate "green" (matches wpx-pipeline behaviour)
        return True
    all_done = all(r.get("status") == "completed" for r in runs)
    if not all_done:
        return False
    return all(
        r.get("conclusion") in ("success", "neutral", "skipped")
        for r in runs
    )


def _all_deps_merged(wp: WPRow, by_id: dict[str, WPRow]) -> bool:
    """True if every WP in wp.depends_on has status TRAIN_DONE_STATUS.

    A missing dependency (not in INDEX.md) is treated as a soft failure —
    we cannot prove it's merged, so we conservatively block. Surface this
    via doctor.
    """
    for dep_id in wp.depends_on:
        dep = by_id.get(dep_id)
        if dep is None:
            return False
        if dep.status != TRAIN_DONE_STATUS:
            return False
    return True


def find_eligible_branches(
    wps: list[WPRow],
    repo: str,
    wp_dir: Path,
    overrides: TrainOverrides | None = None,
    strict_ci: bool = False,
    *,
    paths: "WpxPaths | None" = None,
    base_branch: str = "main",
) -> list[EligibilityResult]:
    """Discover which WPs are eligible for the next train.

    Default criteria (optimistic; v0.18.0+):

      1. status == step-7-complete (or force-include override)
      2. branch exists on origin
      3. all dependencies have status == done
      4. WP is not hold-overridden

    The bundled-tip CI (Step 8 of the lifecycle) remains the real
    gate; per-WP branch CI status is informational only. This
    matches how modern merge queues work (GitHub Merge Queue,
    Bors, Shopify Shipit): the queue handles batching + integration
    CI; per-branch CI is a hint, not a gate.

    Strict mode (ADR-212 D6 original; backward-compatible):

      Set `strict_ci=True` to also require per-WP branch CI green
      before considering a WP eligible. Use this when you want
      pre-merge confidence on each individual branch (e.g., trains
      against very slow integration CI that can't afford to
      sequence flaky-but-passable branches together).

    Computed-status mode (HD-008, v0.24.0+):

      Pass ``paths`` (a WpxPaths) to consult ``compute_wp_status`` for
      both the eligibility status check AND the dependency-merged
      check. With ``paths`` set, the function treats the *computed*
      status as authoritative: a WP whose stored cell says ``done``
      but whose computed status is ``step-7-complete`` (because the
      merge SHA was reverted) is re-considered for eligibility; a WP
      whose dep's stored cell says ``done`` but whose computed value
      is not ``done`` is treated as having an unmet dep.

      Without ``paths`` (the historical signature), the function reads
      ``wp.status`` from the INDEX parse as it did pre-HD-008. This
      preserves the contract for the existing in-memory test suite
      (``test_wpx_train_eligibility.py``) which stubs WPRow.status
      directly and doesn't need network access.

    Returns one EligibilityResult per WP — both eligible and ineligible
    are returned so the caller (queue-list / status / doctor) can show
    the founder the full picture.
    """
    overrides = overrides or TrainOverrides()
    # by_id was historically a {wp.id: wp} index used for dep lookup; HD-008
    # replaced that with effective_status (dict[str, str]) so by_id became
    # dead. Removed (was F841 unused-variable lint flag).
    results: list[EligibilityResult] = []

    # HD-008 — compute effective status per WP up-front when paths is set,
    # so the loop below treats `effective_status[wp.id]` consistently for
    # both the candidate-skip check AND the eligibility check.
    if paths is not None:
        effective_status: dict[str, str] = {
            wp.id: compute_wp_status(
                wp.id, paths, repo, base_branch,
                stored_status=wp.status,
            )
            for wp in wps
        }
    else:
        effective_status = {wp.id: wp.status for wp in wps}

    for wp in wps:
        wp_status = effective_status[wp.id]

        # Skip WPs that aren't candidates at all (done, cancelled, blocked).
        if wp_status in (TRAIN_DONE_STATUS, "cancelled"):
            continue

        is_held = wp.id in overrides.holds
        is_forced = wp.id in overrides.includes

        # Derive branch — resolve_wp_branch tolerates executor-side slug
        # drift (literal match first; falls through to fuzzy ``feat/wp-NNN-*``
        # on origin so a short-slug push still ships). When the WP file
        # exists but no branch can be resolved, ``resolved`` is None and
        # we surface "branch missing" identically to the historical path.
        slug = _wp_slug_from_file(wp_dir, wp.id)
        if slug is None:
            results.append(EligibilityResult(
                wp=wp.id, branch="", eligible=False,
                reason=f"no WP file found at {wp_dir}/{wp.id}-*.md",
                primitive=wp.primitive,
            ))
            continue
        # Reported branch defaults to the slug-literal for messaging; the
        # actual resolved branch (which may be fuzzy-matched) replaces it
        # once we know we have a hit on origin.
        branch = _branch_name(wp.id, slug)

        if is_held:
            results.append(EligibilityResult(
                wp=wp.id, branch=branch, eligible=False,
                reason="held by override (train-overrides.yaml)",
                primitive=wp.primitive,
            ))
            continue

        # Status check
        if wp_status != TRAIN_ELIGIBLE_STATUS and not is_forced:
            results.append(EligibilityResult(
                wp=wp.id, branch=branch, eligible=False,
                reason=f"status is '{wp_status}', not '{TRAIN_ELIGIBLE_STATUS}'",
                primitive=wp.primitive,
            ))
            continue

        # Branch existence — fuzzy-tolerant. resolve_wp_branch returns
        # the literal when it exists on origin, or a fuzzy ``feat/wp-NNN-*``
        # match (single → use; multi → most-recent-by-committerdate with
        # a warning), or None when no branch matches.
        resolved = resolve_wp_branch(wp.id, repo, wp_dir)
        if resolved is None:
            results.append(EligibilityResult(
                wp=wp.id, branch=branch, eligible=False,
                reason="status step-7-complete but origin branch missing",
                primitive=wp.primitive,
            ))
            continue
        branch = resolved

        # CI check — gated only in strict mode (v0.18.0+: bundled-tip CI
        # is the gate by default; per-WP CI is informational).
        if strict_ci and not is_forced and not _gh_branch_ci_green(repo, branch):
            results.append(EligibilityResult(
                wp=wp.id, branch=branch, eligible=False,
                reason="branch CI not green (pending or failed); strict-ci mode",
                primitive=wp.primitive,
            ))
            continue

        # Dependency check — uses effective_status when paths is set so a
        # reverted dep (stored=done, computed=step-7-complete) correctly
        # blocks downstream WPs from shipping on a false done signal.
        unmet = [
            d for d in wp.depends_on
            if d not in effective_status
            or effective_status[d] != TRAIN_DONE_STATUS
        ]
        if unmet:
            results.append(EligibilityResult(
                wp=wp.id, branch=branch, eligible=False,
                reason=f"dependencies not merged: {', '.join(unmet)}",
                primitive=wp.primitive,
            ))
            continue

        results.append(EligibilityResult(
            wp=wp.id, branch=branch, eligible=True,
            reason="ready" + (" (force-included)" if is_forced else ""),
            primitive=wp.primitive,
            forced=is_forced,
        ))

    return results


# --- Batch packing ------------------------------------------------------

def pack_batches(
    eligible: list[EligibilityResult],
    max_per_batch: int = 5,
) -> list[list[EligibilityResult]]:
    """Pack eligible WPs into batches respecting the max_per_batch ceiling.

    For Phase 2: batches honour the order in `eligible` (which is INDEX.md
    order — already topologically sorted by SEA's decompose).

    Phase 5 (deferred) will refine this to use per-primitive batch_hint
    ceilings (CONTRACT-Delete=1, REORGANISE=2-3, EXPAND=5-8). For now,
    flat max_per_batch.
    """
    ready = [e for e in eligible if e.eligible]
    batches: list[list[EligibilityResult]] = []
    current: list[EligibilityResult] = []
    for e in ready:
        if len(current) >= max_per_batch:
            batches.append(current)
            current = []
        current.append(e)
    if current:
        batches.append(current)
    return batches


# --- Train run helpers (Phase 2) ---------------------------------------

# Trigger thresholds. Documented in ADR-212 D1. The amendment notes
# these should be revisited once the DAG-level batch unit is in
# (PH-research follow-up item 6).
TRAIN_TRIGGER_MIN_SIZE = 3
TRAIN_TRIGGER_STALENESS_SECONDS = 4 * 60 * 60  # 4 hours


def check_train_trigger(
    eligible: list[EligibilityResult],
    force: bool = False,
    queued_at_lookup: dict[str, str] | None = None,
    now: datetime | None = None,
) -> tuple[bool, str]:
    """Decide whether the train should fire.

    Triggers (any one is sufficient):
      - force:        --force flag passed
      - size:         >= TRAIN_TRIGGER_MIN_SIZE eligible WPs
      - staleness:    >= 1 eligible WP older than TRAIN_TRIGGER_STALENESS_SECONDS

    Returns (should_fire, reason).

    `queued_at_lookup` maps wp_id → ISO 8601 UTC timestamp string.
    Missing entries are treated as "just queued" (no staleness pressure).

    `now` is for testability — defaults to datetime.now(UTC).
    """
    if force:
        return True, "force"
    if not eligible:
        return False, "no eligible WPs"
    if len(eligible) >= TRAIN_TRIGGER_MIN_SIZE:
        return True, f"size trigger: {len(eligible)} >= {TRAIN_TRIGGER_MIN_SIZE}"
    # Staleness check
    now = now or datetime.now(timezone.utc)
    queued_at_lookup = queued_at_lookup or {}
    for e in eligible:
        ts_str = queued_at_lookup.get(e.wp)
        if not ts_str:
            continue
        try:
            ts = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc,
            )
        except (ValueError, TypeError):
            continue
        age = (now - ts).total_seconds()
        if age >= TRAIN_TRIGGER_STALENESS_SECONDS:
            return True, (
                f"staleness trigger: {e.wp} queued "
                f"{int(age // 60)}m ago "
                f"(>= {TRAIN_TRIGGER_STALENESS_SECONDS // 60}m)"
            )
    return False, (
        f"{len(eligible)} eligible (need {TRAIN_TRIGGER_MIN_SIZE} for size "
        f"or >={TRAIN_TRIGGER_STALENESS_SECONDS // 60}m staleness on one WP)"
    )


def clone_repo_to_temp(repo: str, dest: Path,
                       *, gh: GHClient | None = None) -> None:
    """Clone the repo to `dest` for the duration of a train run.

    Uses `gh repo clone` (preferred — handles auth) with a fallback to
    `git clone` from origin via the GITHUB_TOKEN env var if available.

    Raises RuntimeError on failure.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    rc, err = _resolve_gh(gh).clone(repo, dest)
    if rc == 0:
        return
    # Fallback: direct git clone using GITHUB_TOKEN if present
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        url = f"https://x-access-token:{token}@github.com/{repo}.git"
    else:
        url = f"https://github.com/{repo}.git"
    rc, _, err = _run(["git", "clone", "--depth", "100", url, str(dest)],
                     timeout=120)
    if rc != 0:
        raise RuntimeError(f"clone failed for {repo}: {err}")


class PatchesAlreadyAppliedError(RuntimeError):
    """Raised when a feature branch's patches are already in the base
    branch's history.

    Typically happens after an earlier train merged the branch and was
    then reverted: the revert commit neutralises the content but the
    original squash commits remain in the graph with their patch-ids
    intact. `git rebase` would silently drop the already-applied
    patches, leaving the branch HEAD equal to base HEAD; GitHub's
    `/merges` endpoint would then return 204 No Content; the train
    fails opaquely.

    Detect this case BEFORE rebase so we can emit a useful BLOCKER with
    the manual recovery command instead of a confusing late-failure.

    Subclasses RuntimeError so existing rebase-failure handling still
    catches it; callers that want to handle this case specifically can
    `except PatchesAlreadyAppliedError`.
    """

    def __init__(
        self, branch: str, base_branch: str, applied_shas: list[str]
    ) -> None:
        self.branch = branch
        self.base_branch = base_branch
        self.applied_shas = applied_shas
        super().__init__(
            f"{len(applied_shas)} patch(es) from {branch} are already in "
            f"{base_branch}'s history; rebase would drop them. SHAs: "
            f"{', '.join(sha[:8] for sha in applied_shas)}"
        )


def detect_already_applied_patches(
    clone_dir: Path, base_branch: str, feature_branch: str,
) -> list[str]:
    """Return commit SHAs from `feature_branch` whose patch-ids are
    already present in `base_branch`'s history.

    Uses `git cherry origin/<base> origin/<feature>`. Output lines:
      `+ <sha>` → patch NOT yet in base (would land cleanly via rebase)
      `- <sha>` → patch ALREADY in base (would be dropped silently)

    Empty result list means it's safe to rebase. Non-empty means the
    caller must decide what to do (typically: emit a BLOCKER with
    manual revert-the-revert instructions).

    Assumes `origin/<base>` and `origin/<feature>` are present in
    `clone_dir` (caller has already fetched).
    """
    rc, out, err = _run(
        ["git", "cherry",
         f"origin/{base_branch}",
         f"origin/{feature_branch}"],
        cwd=clone_dir, timeout=30,
    )
    if rc != 0:
        raise RuntimeError(f"git cherry failed: {err}")
    applied: list[str] = []
    for line in out.strip().splitlines():
        line = line.strip()
        if line.startswith("- "):
            sha = line[2:].strip()
            if sha:
                applied.append(sha)
    return applied


def rebase_branch_in_clone(
    clone_dir: Path,
    branch: str,
    onto: str,
    base_branch: str = "main",
) -> str:
    """Within an existing clone: fetch, checkout, rebase, push --force-with-lease.

    `onto` is a SHA or ref the branch should be rebased on top of.
    `base_branch` is the merge target (default "dev"; pass the change
    branch name when training inside a change worktree). Used for the
    patch-id-already-applied detection before rebase.

    Returns the new HEAD SHA after rebase + push.

    Raises:
        PatchesAlreadyAppliedError: branch's patches are already in
            base_branch's history (typically post-revert).
        RuntimeError: any other rebase conflict.
    """
    # Fetch latest of both. Use explicit refspec for the branch so the
    # remote-tracking ref refs/remotes/origin/<branch> is created even
    # when the clone was made with --depth/--single-branch (which is
    # how `gh repo clone --depth 100` works). Without the explicit
    # refspec, `git fetch origin <branch>` updates FETCH_HEAD but does
    # NOT create the tracking ref under those clone modes, and the
    # subsequent `git checkout -B <branch> origin/<branch>` then fails.
    rc, _, err = _run(["git", "fetch", "origin",
                       f"{branch}:refs/remotes/origin/{branch}"],
                     cwd=clone_dir, timeout=60)
    if rc != 0:
        raise RuntimeError(f"git fetch {branch} failed: {err}")
    rc, _, err = _run(["git", "fetch", "origin",
                       f"{base_branch}:refs/remotes/origin/{base_branch}"],
                     cwd=clone_dir, timeout=60)
    if rc != 0:
        raise RuntimeError(f"git fetch {base_branch} failed: {err}")

    # v0.15.3 — patch-id-already-applied detection. If any of this
    # branch's patches are already in base_branch's history (typically
    # because an earlier train merged it and was reverted), bail out
    # with a specific exception so the caller can emit a useful
    # BLOCKER instead of failing opaquely later (rebase would drop
    # the patches → empty branch → GitHub merge returns 204).
    already_applied = detect_already_applied_patches(
        clone_dir, base_branch, branch,
    )
    if already_applied:
        raise PatchesAlreadyAppliedError(
            branch=branch,
            base_branch=base_branch,
            applied_shas=already_applied,
        )

    # Capture the pre-rebase SHA so we can use --force-with-lease with
    # an explicit expected value (safer than plain --force; also works
    # around an implicit-comparison bug when the remote-tracking ref
    # was just created via refspec-form fetch above).
    rc, out, _ = _run(["git", "rev-parse", f"origin/{branch}"],
                     cwd=clone_dir, timeout=10)
    if rc != 0:
        raise RuntimeError(f"git rev-parse origin/{branch} failed")
    pre_rebase_sha = out.strip()

    # Checkout the branch (creating a local tracking branch if needed)
    rc, _, err = _run(["git", "checkout", "-B", branch,
                       f"origin/{branch}"], cwd=clone_dir, timeout=30)
    if rc != 0:
        raise RuntimeError(f"git checkout {branch} failed: {err}")

    # Rebase onto the target SHA / ref
    rc, _, err = _run(["git", "rebase", onto], cwd=clone_dir, timeout=120)
    if rc != 0:
        _run(["git", "rebase", "--abort"], cwd=clone_dir, timeout=30)
        raise RuntimeError(f"git rebase {branch} onto {onto[:8]} failed: {err}")

    # Push --force-with-lease with explicit expected SHA (refuses if
    # someone else pushed to origin/<branch> between our fetch and
    # this push).
    rc, _, err = _run(
        ["git", "push",
         f"--force-with-lease={branch}:{pre_rebase_sha}",
         "origin", branch],
        cwd=clone_dir, timeout=60,
    )
    if rc != 0:
        raise RuntimeError(f"git push --force-with-lease {branch} failed: {err}")

    # Read the new HEAD SHA
    rc, out, _ = _run(["git", "rev-parse", "HEAD"], cwd=clone_dir, timeout=10)
    if rc != 0:
        raise RuntimeError(f"git rev-parse HEAD failed in {clone_dir}")
    return out.strip()


# ─── v0.17.0: train state machine (Phase 1.1) ───────────────────────────
#
# In-flight train state lives at .architecture/{project}/train-runs/
# {train_id}.state.json — separate from the historical .yaml record so
# the YAML stays the audit-trail format (unchanged) and JSON gives us
# trivial nested round-tripping without adding pyyaml as a dep.
#
# State file lifecycle:
# - Created at the start of `wpx-train run` (phase=pending)
# - Updated at every phase boundary + every per-WP outcome
# - On terminal state (success / failed / aborted): YAML record written
#   as the historical archive; state file DELETED (no longer needed)
# - On non-terminal pause (phase=paused): state file retained;
#   `wpx-train resume <id>` reads it to pick up
#
# Concurrency: a sibling lock file train-runs/{train_id}.lock is held
# via flock for the duration of any mutating wpx-train command. Second
# concurrent invocation gets a clear "already being acted on by PID
# <N>" error.


PHASES = (
    "pending",          # train_id assigned; bundle selected; no work yet
    "rebasing",         # cloning + sequential rebases in temp clone
    "ci_running",       # bundled-tip CI polling
    "merging",          # sequential squash-merges to base branch
    "deploying",        # deploy workflow polling
    "verifying",        # health + smoke
    "verifying_gates",  # HD-007 — deploy/health/smoke done; Step 10.5 + Step 11 pending
    "success",          # terminal success
    "failed",           # terminal failure (ADR-212 revert completed)
    "paused",           # needs attention; resume possible
    "aborted",          # founder-initiated abort completed
)

TERMINAL_PHASES = frozenset({"success", "failed", "aborted"})


# ─────────────────────────────────────────────────────────────────────────
# HD-001 — Phase-result dataclasses for cmd_run's plan / commit / verify split.
#
# Each phase function in scripts/wpx-train returns one of these (or raises;
# failure handlers terminate the process via emit_result, so the dataclasses
# are populated only on success). They flow forward between phases so the
# orchestration in cmd_run reduces to four function calls + a finaliser.
# ─────────────────────────────────────────────────────────────────────────


@dataclass
class PlanResult:
    """Output of _plan_phase. Read-only-against-base-branch work complete:
    bundle assembled, sequential rebases done, bundled-tip CI green.

    The base branch itself has not been mutated yet — that happens in
    _commit_phase. Feature branches in the bundle HAVE been force-pushed
    with their rebased tips (this is mutating, but only to branches the
    train owns)."""
    bundle: list[dict]
    base_branch: str
    bundle_tip_branch: str
    ci_verdict: str
    rebase_failures: list[dict]


@dataclass
class CommitResult:
    """Output of _commit_phase. Squash-merges have landed on the base
    branch; bundle entries are updated in-place with merge_sha_on_dev."""
    merge_shas: dict[str, str]
    final_merge_sha: str


@dataclass
class VerifyResult:
    """Output of _verify_phase. Deploy + health + smoke have all returned
    green verdicts (failure paths terminate the process via the existing
    _handle_post_merge_failure / _pause_train_state helpers).

    ``ready_for_gates`` is HD-007's signal: when the caller passed
    --enable-gate-handoff, this flag is True and cmd_run transitions to
    the verifying_gates phase instead of going directly to terminal
    success. The calling LLM session then dispatches Step 10.5 + Step 11
    and invokes ``wpx-train mark-gates-complete`` to finalise."""
    deploy_url: str | None
    deploy_verdict: str
    health_status: str
    smoke_verdict: str
    ready_for_gates: bool = False


def train_state_path(train_runs_dir: Path, train_id: str) -> Path:
    """Path to a train's in-flight state JSON."""
    return train_runs_dir / f"{train_id}.state.json"


def train_lock_path(train_runs_dir: Path, train_id: str) -> Path:
    """Path to a train's flock file."""
    return train_runs_dir / f"{train_id}.lock"


def read_train_state(state_path: Path) -> dict:
    """Read an in-flight train state. Returns the dict (raises on missing/corrupt)."""
    if not state_path.exists():
        raise FileNotFoundError(
            f"Train state file not found: {state_path}. "
            f"Either the train was never started, or it completed and "
            f"the state file was cleaned up (check the .yaml record)."
        )
    try:
        with state_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Train state file at {state_path} is corrupt: {exc}. "
            f"This is a bug — please report with the file contents."
        ) from exc


def write_train_state(state_path: Path, state: dict) -> None:
    """Atomic write: write to tmp + rename. Caller MUST hold the lock."""
    state_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = state_path.with_suffix(state_path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=False)
        f.write("\n")
    tmp.replace(state_path)


def _utcnow_iso() -> str:
    """Current UTC time as ISO 8601 with seconds precision."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class TrainLock:
    """Context manager for the train's flock file.

    Usage:
        with TrainLock(train_runs_dir, train_id):
            state = read_train_state(...)
            ... mutate state ...
            write_train_state(...)

    Second concurrent acquisition raises RuntimeError with the existing
    holder's PID (best-effort; PID may be stale if the previous holder
    died without releasing).
    """

    def __init__(self, train_runs_dir: Path, train_id: str) -> None:
        self.lock_path = train_lock_path(train_runs_dir, train_id)
        self.train_id = train_id
        self._fh = None

    def __enter__(self) -> "TrainLock":
        import fcntl
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self.lock_path, "w", encoding="utf-8")
        try:
            fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            existing_pid = self.lock_path.read_text().strip() or "unknown"
            self._fh.close()
            self._fh = None
            raise RuntimeError(
                f"Train {self.train_id} is being acted on by PID "
                f"{existing_pid}. Wait or kill that process before retrying."
            )
        self._fh.write(f"{os.getpid()}\n")
        self._fh.flush()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        import fcntl
        if self._fh is not None:
            try:
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
            finally:
                self._fh.close()
                self._fh = None
                try:
                    self.lock_path.unlink()
                except FileNotFoundError:
                    pass


def init_train_state(
    train_runs_dir: Path,
    train_id: str,
    bundle: list[dict],
    args_repr: dict,
) -> dict:
    """Create the initial train state at phase=pending.

    `bundle` is the list of WPs selected for the train (each dict with
    wp + branch + pre_train_sha keys, matching the existing bundle
    schema). `args_repr` is a dict of the wpx-train run arguments
    (project, repo, deploy_workflow, etc.) used by resume to re-invoke
    the same parameters.

    Caller MUST hold the TrainLock before calling.
    """
    now = _utcnow_iso()
    state = {
        "train_id": train_id,
        "started_at": now,
        "phase": "pending",
        "phase_started_at": now,
        "phase_history": [
            {"phase": "pending", "started_at": now, "ended_at": None, "outcome": None},
        ],
        "pause_reason": None,
        "recovery_hint": None,
        "args": args_repr,  # for resume to re-invoke with same params
        "bundle": [
            {
                "wp": item.get("wp", ""),
                "branch": item.get("branch", ""),
                "pre_train_sha": item.get("pre_train_sha"),
                "rebased_to_sha": item.get("rebased_to_sha"),
                "merge_sha_on_dev": item.get("merge_sha_on_dev"),
                "phase_outcomes": {},
            }
            for item in bundle
        ],
    }
    write_train_state(train_state_path(train_runs_dir, train_id), state)
    return state


def update_train_phase(
    state_path: Path,
    new_phase: str,
    outcome: str = "advanced",
    pause_reason: str | None = None,
    recovery_hint: str | None = None,
) -> dict:
    """Atomically transition the train to a new phase.

    Closes out the previous phase in `phase_history` (sets ended_at +
    outcome) and opens a new entry for `new_phase`. Caller MUST hold
    the TrainLock.

    For paused/failed/aborted phases, set pause_reason + recovery_hint
    so `wpx-train inspect` shows a clear next action.

    Returns the updated state dict.
    """
    if new_phase not in PHASES:
        raise ValueError(
            f"Unknown phase {new_phase!r}; must be one of {PHASES}"
        )
    state = read_train_state(state_path)
    now = _utcnow_iso()
    # Close out the previous phase
    if state.get("phase_history"):
        last = state["phase_history"][-1]
        if last.get("ended_at") is None:
            last["ended_at"] = now
            last["outcome"] = outcome
    # Open the new phase (unless it's the same as current — idempotent)
    if state.get("phase") != new_phase:
        state["phase"] = new_phase
        state["phase_started_at"] = now
        state["phase_history"].append({
            "phase": new_phase,
            "started_at": now,
            "ended_at": None,
            "outcome": None,
        })
    if pause_reason is not None:
        state["pause_reason"] = pause_reason
    if recovery_hint is not None:
        state["recovery_hint"] = recovery_hint
    # Terminal phases get an ended_at + completed_at marker
    if new_phase in TERMINAL_PHASES:
        state["completed_at"] = now
        state["phase_history"][-1]["ended_at"] = now
        state["phase_history"][-1]["outcome"] = new_phase
    write_train_state(state_path, state)
    return state


def update_wp_phase_outcome(
    state_path: Path,
    wp: str,
    phase: str,
    outcome: str,
) -> dict:
    """Atomically record a per-WP outcome for the named phase.

    E.g., after WP-001's rebase completes:
        update_wp_phase_outcome(path, "WP-001", "rebasing", "rebased")

    Or after its rebase conflicts:
        update_wp_phase_outcome(path, "WP-001", "rebasing", "conflict")

    Caller MUST hold the TrainLock. Returns the updated state dict.
    """
    if phase not in PHASES:
        raise ValueError(
            f"Unknown phase {phase!r}; must be one of {PHASES}"
        )
    state = read_train_state(state_path)
    for entry in state.get("bundle", []):
        if entry.get("wp") == wp:
            entry.setdefault("phase_outcomes", {})[phase] = outcome
            write_train_state(state_path, state)
            return state
    raise ValueError(
        f"WP {wp!r} not in train state's bundle "
        f"(bundle: {[e.get('wp') for e in state.get('bundle', [])]})"
    )


def list_train_runs(train_runs_dir: Path) -> list[dict]:
    """Enumerate trains in train_runs_dir. Returns most-recent first.

    Each entry has: train_id, started_at, phase (if state file exists)
    or terminal_outcome (if only the .yaml record exists).

    Used by `wpx-train inspect` (no --train-id) to show recent trains.
    """
    if not train_runs_dir.exists():
        return []
    runs: list[dict] = []
    # State files (in-flight trains)
    for state_file in train_runs_dir.glob("train-*.state.json"):
        try:
            state = read_train_state(state_file)
        except Exception:
            continue
        runs.append({
            "train_id": state.get("train_id"),
            "started_at": state.get("started_at"),
            "phase": state.get("phase"),
            "pause_reason": state.get("pause_reason"),
            "in_flight": True,
        })
    # Historical YAML records (terminal trains)
    in_flight_ids = {r["train_id"] for r in runs}
    for yaml_file in train_runs_dir.glob("train-*.yaml"):
        # Extract train_id from filename: train-2026-01-01T120000Z.yaml
        train_id = yaml_file.stem
        if train_id in in_flight_ids:
            continue  # in-flight version takes precedence
        # Parse out a few fields from the YAML-lite format
        outcome = None
        started_at = None
        for line in yaml_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("outcome:"):
                outcome = line.split(":", 1)[1].strip().strip('"')
            elif line.startswith("started_at:"):
                started_at = line.split(":", 1)[1].strip().strip('"')
        runs.append({
            "train_id": train_id,
            "started_at": started_at,
            "phase": outcome,  # terminal phase from .yaml
            "pause_reason": None,
            "in_flight": False,
        })
    # Most-recent first by started_at (None → tail)
    runs.sort(key=lambda r: r.get("started_at") or "", reverse=True)
    return runs


def render_train_state_plain_english(state: dict) -> str:
    """Render a train-state dict as a founder-friendly plain-English summary.

    FE-06 compliant: no internal IDs, no jargon. Translates phase names
    to action-oriented language; surfaces pause_reason + recovery_hint
    when present.

    Used by `wpx-train inspect <train_id>` for the default rendering.
    """
    train_id = state.get("train_id", "unknown")
    phase = state.get("phase", "unknown")
    started_at = state.get("started_at", "?")
    bundle = state.get("bundle", [])

    lines = [
        f"Train {train_id}",
        f"  Started: {started_at}",
        f"  Phase: {phase}",
    ]

    phase_descriptions = {
        "pending": "Selected the bundle of work; about to start rebasing.",
        "rebasing": "Rebasing the feature branches onto each other in a temp clone.",
        "ci_running": "Waiting for the bundled-tip CI to come back.",
        "merging": "Squash-merging each branch to the base in order.",
        "deploying": "Waiting for the deploy workflow to complete.",
        "verifying": "Running health + smoke checks against the deploy.",
        "verifying_gates": (
            "Deploy + health + smoke green. Waiting on the calling "
            "session to dispatch Step 10.5 (code-review against the "
            "bundled diff) and Step 11 (per-WP security review). When "
            "both gates complete, the session runs `wpx-train "
            "mark-gates-complete` to finalise this train to success."
        ),
        "success": "Done. All work merged + deployed + verified.",
        "failed": "Failed. The revert path ran; branches restored.",
        "paused": "Paused. Needs attention before it can continue.",
        "aborted": "Aborted by founder. Branches restored to their pre-train state.",
    }
    description = phase_descriptions.get(phase)
    if description:
        lines.append(f"    → {description}")

    if state.get("pause_reason"):
        lines.append(f"  Pause reason: {state['pause_reason']}")
    if state.get("recovery_hint"):
        lines.append(f"  What to do: {state['recovery_hint']}")

    if bundle:
        lines.append("")
        lines.append(f"  Bundle ({len(bundle)} work packages):")
        for entry in bundle:
            wp = entry.get("wp", "?")
            outcomes = entry.get("phase_outcomes", {})
            merge_sha = entry.get("merge_sha_on_dev")
            outcome_summary = (
                f"merged as {merge_sha[:8]}" if merge_sha
                else _summarise_wp_outcomes(outcomes)
            )
            lines.append(f"    - {wp}: {outcome_summary}")

    history = state.get("phase_history", [])
    if history and len(history) > 1:
        lines.append("")
        lines.append("  Phase history:")
        for entry in history:
            outcome = entry.get("outcome") or "in progress"
            lines.append(
                f"    - {entry['phase']}: {entry.get('started_at', '?')} "
                f"→ {entry.get('ended_at') or 'now'} ({outcome})"
            )

    return "\n".join(lines)


def _summarise_wp_outcomes(outcomes: dict) -> str:
    """Compact summary of a WP's per-phase outcomes for the bundle listing."""
    if not outcomes:
        return "pending"
    # Show the latest phase reached
    phase_order = (
        "rebasing", "ci_running", "merging", "deploying", "verifying"
    )
    for phase in reversed(phase_order):
        if phase in outcomes:
            return f"{phase}: {outcomes[phase]}"
    return ", ".join(f"{k}={v}" for k, v in outcomes.items())


def cleanup_train_state(train_runs_dir: Path, train_id: str) -> None:
    """Delete the in-flight state file (called on terminal phases after
    the .yaml record has been written). Lock file is cleaned up by
    TrainLock's __exit__."""
    state_path = train_state_path(train_runs_dir, train_id)
    try:
        state_path.unlink()
    except FileNotFoundError:
        pass


# ─── Existing record writer (unchanged) ─────────────────────────────────


# Top-level scalar keys the YAML-lite emitter writes (in order). HD-007
# added awaiting_gates_at, final_merge_sha, gate_findings_path so the
# gate-handoff record carries enough state for downstream tools.
_TRAIN_RECORD_SCALAR_KEYS: tuple[str, ...] = (
    "train_id", "started_at", "completed_at", "outcome",
    "outcome_reason", "batch_size", "deploy_url",
    "deploy_workflow_run", "health_status", "smoke_verdict",
    "awaiting_gates_at", "final_merge_sha", "gate_findings_path",
)

# Per-bundle-entry keys (in order).
_TRAIN_RECORD_BUNDLE_KEYS: tuple[str, ...] = (
    "branch", "pre_train_sha", "rebased_to_sha", "merge_sha_on_dev",
)


def write_train_run_record(record_path: Path, record: dict) -> None:
    """Write a train run record to .architecture/{project}/train-runs/train-{ts}.yaml.

    Uses a YAML-lite emitter (no pyyaml dep). The record schema:

        train_id: train-{TIMESTAMP}
        started_at: ISO 8601 UTC
        completed_at: ISO 8601 UTC
        outcome: success | blocker | error | awaiting_gates | gate_blocker
        outcome_reason: str (when not success)
        batch_size: N
        bundle:
          - wp: WP-X
            branch: feat/wp-x-slug
            pre_train_sha: <sha>
            rebased_to_sha: <sha>
            merge_sha_on_dev: <sha or null>
        deploy_url: str | null
        deploy_workflow_run: str | null
        health_status: str | null
        smoke_verdict: str | null
        awaiting_gates_at: ISO 8601 UTC (HD-007 — when paused for gates)
        final_merge_sha: <sha> | null (HD-007 — last bundled merge SHA)
        gate_findings_path: str | null (HD-007 — path to gate findings JSON)
    """
    record_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for k in _TRAIN_RECORD_SCALAR_KEYS:
        if k in record:
            value = record[k]
            if value is None:
                lines.append(f"{k}: null")
            elif isinstance(value, (int, float)):
                lines.append(f"{k}: {value}")
            else:
                # Quote strings to be safe
                escaped = str(value).replace('"', '\\"')
                lines.append(f'{k}: "{escaped}"')
    bundle = record.get("bundle", [])
    if bundle:
        lines.append("bundle:")
        for item in bundle:
            lines.append(f"  - wp: {item.get('wp', '')}")
            for k in _TRAIN_RECORD_BUNDLE_KEYS:
                v = item.get(k)
                if v is None:
                    lines.append(f"    {k}: null")
                else:
                    lines.append(f"    {k}: {v}")
    record_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_train_run_record(record_path: Path) -> dict:
    """Read a train run record produced by ``write_train_run_record``.

    Inverse of the YAML-lite emitter above. Parses the top-level scalar
    keys (with quoted strings, numeric scalars, and ``null`` for None)
    and the ``bundle:`` list of per-WP entries.

    HD-010 — added so ``cmd_mark_gates_complete`` can read the
    awaiting-gates record stub before re-writing it. Without this reader,
    the previous implementation truncated the file on every successful
    gate-handoff finalisation (silent data loss on bundle / deploy_url /
    final_merge_sha / started_at / batch_size). Mirrors the YAML-lite
    subset parser used by ``find_wp_merge_sha`` but returns the full
    record rather than a single field.

    Returns ``{}`` if the file is missing. Raises ``OSError`` /
    ``ValueError`` on read errors — callers MUST handle the failure
    rather than swallow it (the previous swallow-and-truncate pattern
    was the root cause of HD-010).
    """
    if not record_path.exists():
        return {}
    text = record_path.read_text(encoding="utf-8")
    out: dict = {}
    bundle: list[dict] = []
    cur_item: dict | None = None
    in_bundle = False
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line == "bundle:":
            in_bundle = True
            continue
        if in_bundle:
            # End of bundle: any flush-left non-blank line that is not a
            # bundle indent. Bundle items are indented at least 2 spaces.
            if line and not raw_line.startswith(" "):
                in_bundle = False
                # Fall through to scalar-key handling for this line.
            else:
                stripped = line.strip()
                if stripped.startswith("- wp:"):
                    if cur_item is not None:
                        bundle.append(cur_item)
                    cur_item = {"wp": stripped[len("- wp:"):].strip()}
                    continue
                if cur_item is not None and ":" in stripped:
                    k, _, v = stripped.partition(":")
                    v = v.strip()
                    cur_item[k.strip()] = None if v == "null" else v
                continue
        # Top-level scalar key.
        if ":" in line and not line.startswith(" "):
            k, _, v = line.partition(":")
            v = v.strip()
            if v == "null":
                out[k.strip()] = None
            elif v.startswith('"') and v.endswith('"') and len(v) >= 2:
                # Quoted string — unescape \" → "
                out[k.strip()] = v[1:-1].replace('\\"', '"')
            else:
                # Numeric or unquoted scalar.
                try:
                    out[k.strip()] = int(v)
                except ValueError:
                    try:
                        out[k.strip()] = float(v)
                    except ValueError:
                        out[k.strip()] = v
    if cur_item is not None:
        bundle.append(cur_item)
    if bundle:
        out["bundle"] = bundle
    return out


# --- Phase 3: failure handling helpers ----------------------------------

def flip_index_status_via_cli(
    scripts_dir: Path,
    paths: WpxPaths,
    wp_id: str,
    to_status: str,
    expected: str | None = None,
) -> tuple[bool, str]:
    """Shell out to wpx-index flip-status. Returns (success, message).

    Doesn't raise — the caller (failure-path code in wpx-train) wants
    to keep going even if one INDEX flip fails. The error is returned
    so the caller can surface it in the train BLOCKER record.

    .. deprecated:: 0.24.0 (HD-008)
       Status for the computed-eligible set ({done, step-7-shipping,
       step-7-complete}) is now derived from authoritative sources
       (origin git state + train-runs/ records) via
       ``compute_wp_status``. This function still writes the INDEX.md
       cache for backward compatibility — readers that haven't migrated
       yet continue to see an approximately-correct stored cell — but
       new callers should compute status and rely on
       ``compute_wp_status`` rather than treating the cache as
       authoritative.

       Removal target: when all 8 existing callsites in ``wpx-train``
       and ``skills/run-all/SKILL.md`` have been migrated to rely on
       computed status instead of cache writes. Tracking via HD-008's
       follow-on deltas (one per callsite group).

       A ``DeprecationWarning`` is emitted on every call to make the
       drift visible in CI logs without breaking production paths.
    """
    import warnings
    warnings.warn(
        "flip_index_status_via_cli is deprecated as of HD-008 (v0.24.0). "
        "Status for the computed-eligible set is now derived from origin + "
        "train-runs via compute_wp_status; this function still writes the "
        "cache for backward compatibility but new callers should not rely "
        "on it.",
        DeprecationWarning,
        stacklevel=2,
    )
    _log(
        f"flip_index_status_via_cli: deprecated call site flipping "
        f"{wp_id} -> {to_status} (HD-008: prefer computed status via "
        f"compute_wp_status)"
    )
    args = [
        str(scripts_dir / "wpx-index"), "flip-status",
        "--project", paths.project,
        "--repo-root", str(paths.repo_root),
        "--wp", wp_id,
        "--to", to_status,
    ]
    if expected:
        args.extend(["--expected", expected])
    rc, out, err = _run(args, timeout=30)
    if rc == 0:
        return True, ""
    return False, err or out or f"wpx-index flip-status rc={rc}"


def write_wp_blocker_via_cli(
    scripts_dir: Path,
    paths: WpxPaths,
    wp_id: str,
    title: str,
    observation: str,
    root_cause: str,
    plain_english: str,
    suggested_next: str,
    step: str = "Step 8 (train run)",
    trigger: str = "wpx-train",
) -> tuple[bool, str]:
    """Shell out to wpx-blocker write. Returns (success, message)."""
    args = [
        str(scripts_dir / "wpx-blocker"), "write",
        "--project", paths.project,
        "--repo-root", str(paths.repo_root),
        "--wp", wp_id,
        "--title", title,
        "--step", step,
        "--trigger", trigger,
        "--observation", observation,
        "--root-cause", root_cause,
        "--scope", "indeterminate",
        "--scope-reason", "Identified by train failure-path; needs human triage",
        "--plain-english", plain_english,
        "--suggested-next", suggested_next,
        "--force",
    ]
    rc, out, err = _run(args, timeout=30)
    if rc == 0:
        return True, ""
    return False, err or out or f"wpx-blocker write rc={rc}"


def write_train_blocker(
    paths: WpxPaths,
    train_id: str,
    reason: str,
    bundle: list[dict],
    suspected_wp_id: str | None = None,
    evidence: str = "",
) -> Path:
    """Write a train-level BLOCKER-train-{ts}.md.

    Distinct from per-WP BLOCKER files: this records the train as a
    whole, lists all bundled WPs and which (if any) was flagged as the
    likely culprit by the file-overlap heuristic.
    """
    blocker_path = paths.wp_dir / f"BLOCKER-{train_id}.md"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines = [
        f"# BLOCKER-{train_id}",
        "",
        f"> Created: {now} by sulis-execution wpx-train",
        f"> Scope: train run {train_id}",
        f"> Reason: {reason}",
        "",
        "## What happened",
        "",
        reason,
        "",
        "## Bundled Work Packages",
        "",
        "| WP | Branch | Pre-train SHA | Merged? |",
        "|---|---|---|---|",
    ]
    for entry in bundle:
        merge_sha = entry.get("merge_sha_on_dev") or "—"
        lines.append(
            f"| {entry.get('wp', '?')} | {entry.get('branch', '?')} | "
            f"{(entry.get('pre_train_sha') or '?')[:8]} | {merge_sha[:8] if merge_sha != '—' else '—'} |"
        )

    lines.extend(["", "## Suggested culprit (file-overlap heuristic)", ""])
    if suspected_wp_id:
        lines.append(f"**Most likely culprit: {suspected_wp_id}**")
        lines.append("")
        lines.append(
            "The file-overlap heuristic compared each WP's changed-file set "
            "to file names mentioned in the failure output. The WP with the "
            "most overlap is named above. This is a starting point — verify "
            "before holding the WP back from the next train."
        )
    else:
        lines.append(
            "The file-overlap heuristic could not identify a specific "
            "culprit. Investigate each WP in the bundle individually."
        )

    if evidence:
        lines.extend(["", "## Evidence", "", "```", evidence[:4000], "```"])

    lines.extend([
        "",
        "## Plain-English summary (for the founder)",
        "",
        f"The train run {train_id} did not complete. {reason}. "
        f"All {len(bundle)} WPs in the batch have been moved to "
        f"`step-7-blocked` status. Investigate the suspected culprit "
        f"first, then re-queue the rest for the next train.",
        "",
        "## Suggested next step",
        "",
        "1. Read the evidence above to confirm the suspected culprit",
        "2. Investigate that WP's branch locally if needed",
        "3. Flip its status back to `step-7-complete` (or fix and re-push) "
        "when ready",
        "4. The next `wpx-train run` will pick up the remaining WPs",
        "",
    ])
    blocker_path.parent.mkdir(parents=True, exist_ok=True)
    blocker_path.write_text("\n".join(lines), encoding="utf-8")
    return blocker_path


def compute_culprit_heuristic(
    bundle: list[dict],
    clone_dir: Path,
    failure_text: str,
) -> str | None:
    """Best-effort: which WP in the bundle most likely caused the failure?

    For each WP, lists files changed by its branch (via git diff against
    its pre_train_sha base). Counts overlap with file names mentioned in
    failure_text. The WP with the most overlap wins.

    Returns the WP id, or None if no overlap detected.

    This is heuristic — it's right often enough to save investigation
    time; not right enough to auto-eject a WP silently. The train
    BLOCKER surfaces it as a "suggested" culprit only.
    """
    if not bundle or not failure_text:
        return None
    best_wp: str | None = None
    best_score = 0
    for entry in bundle:
        branch = entry.get("branch")
        pre_sha = entry.get("pre_train_sha")
        if not branch or not pre_sha:
            continue
        rc, out, _ = _run(
            ["git", "diff", "--name-only", pre_sha, "HEAD"],
            cwd=clone_dir, timeout=30,
        )
        if rc != 0:
            continue
        files = [f.strip() for f in out.splitlines() if f.strip()]
        score = sum(1 for f in files if f and f in failure_text)
        if score > best_score:
            best_score = score
            best_wp = entry.get("wp")
    return best_wp


def is_sha_on_branch(repo: str, sha: str, branch: str = "main",
                     *, gh: GHClient | None = None) -> bool:
    """Check whether `sha` is reachable from origin/<branch>.

    Uses GitHub's compare API: `gh api repos/{repo}/compare/{branch}...{sha}`.
    Status "identical" or "behind" means sha is reachable from branch
    (identical = same commit; behind = sha is in branch's history with
    branch having more commits on top). Status "ahead" or "diverged"
    means sha is NOT reachable from branch.

    Returns False on any API error (conservative — caller decides what
    to do; a True return must be trustworthy).

    Used by `wpx-train doctor` to detect INDEX status drift (v0.21.2+):
    a WP with status=done whose merge_sha_on_dev is not on origin/dev
    means the work has been reverted or never landed — the INDEX
    state is wrong.
    """
    try:
        data = _resolve_gh(gh).compare(repo, branch, sha)
    except RuntimeError as exc:
        _log(
            f"is_sha_on_branch: compare API failed for "
            f"{branch}...{sha[:8]}; returning False conservatively. "
            f"err: {exc}"
        )
        return False
    if not isinstance(data, dict):
        _log(f"is_sha_on_branch: compare API returned non-dict. data: {data!r}")
        return False
    return data.get("status", "") in ("identical", "behind")


def find_wp_merge_sha(train_runs_dir: Path, wp_id: str) -> str | None:
    """Find a WP's most-recent merge_sha_on_dev across all train records.

    Walks train-runs/{*.yaml, *.state.json} in reverse chronological order
    (by file mtime). For each file, parses the `bundle` list looking for
    an entry where wp == wp_id; returns the first matching entry's
    merge_sha_on_dev if populated. Returns None if no such entry exists.

    JSON files (.state.json, v0.17.0+ in-flight) parsed via json.load.
    YAML files (.yaml, historical archive) parsed via a small bespoke
    parser matching the format `write_train_run_record` emits — see that
    function's docstring for the schema.

    Used by `wpx-train doctor` to detect drift: a WP with status=done
    that has no merge_sha in any train record means it was never shipped
    via the train (either manually flipped or shipped via wpx-pipeline);
    a WP whose merge_sha exists but is no longer on dev means it was
    shipped and reverted.
    """
    if not train_runs_dir.exists():
        return None
    candidates: list[Path] = []
    candidates.extend(train_runs_dir.glob("*.state.json"))
    candidates.extend(train_runs_dir.glob("*.yaml"))
    # Most recent first
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for path in candidates:
        try:
            if path.suffix == ".json":
                with path.open("r", encoding="utf-8") as f:
                    state = json.load(f)
                for entry in state.get("bundle", []):
                    if entry.get("wp") == wp_id:
                        sha = entry.get("merge_sha_on_dev")
                        if sha:
                            return sha
            else:
                # Bespoke YAML — only need the bundle entries.
                # Schema: top-level keys, then `bundle:` followed by
                # lines like `  - wp: WP-NNN` and `    merge_sha_on_dev: <sha>`.
                in_bundle = False
                current_wp: str | None = None
                current_sha: str | None = None
                with path.open("r", encoding="utf-8") as f:
                    for raw_line in f:
                        line = raw_line.rstrip("\n")
                        if line.rstrip() == "bundle:":
                            in_bundle = True
                            continue
                        if not in_bundle:
                            continue
                        # Bundle entries are indented 2 spaces for `- wp:`
                        # and 4 spaces for fields. Out-of-bundle would
                        # be flush-left.
                        if line and not line.startswith(" "):
                            in_bundle = False
                            continue
                        stripped = line.strip()
                        if stripped.startswith("- wp:"):
                            # Commit previous entry if it matched
                            if current_wp == wp_id and current_sha:
                                return current_sha
                            current_wp = stripped[len("- wp:"):].strip()
                            current_sha = None
                        elif stripped.startswith("merge_sha_on_dev:"):
                            val = stripped[len("merge_sha_on_dev:"):].strip()
                            if val and val != "null":
                                current_sha = val
                    # End of file: commit any pending entry
                    if current_wp == wp_id and current_sha:
                        return current_sha
        except (json.JSONDecodeError, OSError, ValueError) as exc:
            _log(f"find_wp_merge_sha: skipping {path.name} (parse error: {exc})")
            continue
    return None


# ─────────────────────────────────────────────────────────────────────────
# HD-008 — Status as a computed view
#
# Status for the computed-eligible set ({done, step-7-shipping,
# step-7-complete}) is derived from authoritative sources (origin git
# state + train-runs/ records). The stored INDEX.md cell remains the
# source for operator/executor-intent states (pending, in_progress,
# auto-draft, cancelled, dependency_blocked, blocked, step-7-blocked,
# step-7-held) that have no authoritative-state correlate.
#
# See HD-008 for the full rationale; this is the load-bearing helper
# that callers (wpx-index status, find_eligible_branches, cmd_doctor)
# delegate to. The function is read-only — it does not mutate INDEX.md.
# ─────────────────────────────────────────────────────────────────────────


# In-flight phases — a train in any of these is still actively shipping
# its bundle. A WP in such a bundle is in step-7-shipping. Terminal
# phases (success / failed / aborted) are not in-flight; paused is also
# considered "still owns the WP" because the bundle hasn't been merged
# or unwound. verifying_gates is in-flight (HD-007 — deploy landed but
# Step 10.5 + Step 11 still pending).
_IN_FLIGHT_TRAIN_PHASES: frozenset[str] = frozenset({
    "pending", "rebasing", "ci_running", "merging",
    "deploying", "verifying", "verifying_gates", "paused",
})


def _in_flight_train_has_wp(train_runs_dir: Path, wp_id: str) -> bool:
    """True if any *.state.json in train_runs_dir is in-flight and
    its ``bundle`` lists ``wp_id``.

    Walks `*.state.json` files only (terminal trains delete their state
    file and leave only the `*.yaml` archive — HD-008 cares only about
    in-flight, so we scan the JSON tier exclusively).

    Returns False on any IO / parse error per-file (logs and continues);
    a single corrupt state file MUST NOT mask other in-flight trains.
    Returns False if the directory does not exist.
    """
    if not train_runs_dir.exists():
        return False
    for path in train_runs_dir.glob("*.state.json"):
        try:
            with path.open("r", encoding="utf-8") as f:
                state = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            _log(f"_in_flight_train_has_wp: skipping {path.name} ({exc})")
            continue
        phase = state.get("phase", "")
        if phase not in _IN_FLIGHT_TRAIN_PHASES:
            continue
        for entry in state.get("bundle", []):
            if entry.get("wp") == wp_id:
                return True
    return False


def compute_wp_status(
    wp_id: str,
    paths: "WpxPaths",
    repo: str,
    base_branch: str = "main",
    *,
    gh: GHClient | None = None,
    stored_status: str | None = None,
) -> str:
    """Return the computed status for ``wp_id``.

    Resolution order — the four authoritative-derivable cases first,
    falling through to ``stored_status`` for operator/executor-intent
    states that have no authoritative-state correlate:

    1. **done** — ``find_wp_merge_sha`` returns a SHA AND
       ``is_sha_on_branch`` confirms it is reachable from
       ``origin/<base_branch>``. The work landed and has not been
       reverted.
    2. **step-7-shipping** — an in-flight ``*.state.json`` in
       ``paths.train_runs_dir`` lists this WP in its ``bundle``
       (regardless of merge-SHA presence — the train is mid-flight and
       the WP's authoritative state is owned by the train, not the
       INDEX cell).
    3. **step-7-complete** — ``origin/<feature-branch>`` exists AND
       cases 1 + 2 are both False. The WP's work is pushed but not
       merged (or shipped via wpx-pipeline and lacking a train record).
    4. **fall-through** — none of the above. Return ``stored_status``
       if provided, otherwise ``"pending"``. The stored cell remains
       the source of truth for operator/executor intent (pending,
       in_progress, auto-draft, cancelled, dependency_blocked, blocked,
       step-7-blocked, step-7-held).

    The function is conservative: a True return for ``done`` is
    trustworthy (``is_sha_on_branch`` returns False on any API error),
    but step-7-complete may degrade to the stored value when the
    branch-exists check fails transiently. Callers MUST pass
    ``stored_status`` if they want the cached value as the fallback;
    omitting it defaults the fallback to ``"pending"``.

    Read-only — does not write INDEX.md, does not call
    ``flip_index_status_via_cli``. The caller decides whether to
    reconcile a stored/computed disagreement.

    Args:
        wp_id: The full WP ID (e.g., ``WP-S2-LOADER``).
        paths: A WpxPaths instance (provides train_runs_dir + wp_dir).
        repo: ``OWNER/REPO`` GitHub slug used by gh API calls.
        base_branch: Branch to check merge-SHA reachability against;
            defaults to ``dev``.
        gh: Optional GHClient injection; default uses the module-level
            ``_default_gh_client``.
        stored_status: The INDEX.md cell value to fall back to when no
            authoritative signal is present. Pass the parsed cell from
            ``parse_index_md``; defaults to ``None`` → ``"pending"``.

    Returns:
        One of: ``"done"``, ``"step-7-shipping"``, ``"step-7-complete"``,
        or ``stored_status`` / ``"pending"``.
    """
    # Case 1: done — merge SHA recorded AND reachable from base branch.
    merge_sha = find_wp_merge_sha(paths.train_runs_dir, wp_id)
    if merge_sha and is_sha_on_branch(repo, merge_sha, base_branch, gh=gh):
        return "done"

    # Case 2: step-7-shipping — in-flight train has this WP in its bundle.
    # Checked before step-7-complete because a WP whose branch exists AND
    # is mid-flight is owned by the train, not the cache.
    if _in_flight_train_has_wp(paths.train_runs_dir, wp_id):
        return "step-7-shipping"

    # Case 3: step-7-complete — origin branch exists, no train signal.
    # Use resolve_wp_branch so a fuzzy-matched (short-slug) push counts
    # as step-7-complete just the same as a literal-slug push.
    if resolve_wp_branch(wp_id, repo, paths.wp_dir, gh=gh) is not None:
        return "step-7-complete"

    # Case 4: fall-through — defer to the stored cell (operator intent).
    return stored_status if stored_status else "pending"


def revert_train_on_dev(
    repo: str,
    clone_dir: Path,
    bundle: list[dict],
    reason: str,
    train_id: str,
    base_branch: str = "main",
) -> tuple[bool, str]:
    """Revert all merged WPs in the bundle in reverse order, push to the trunk.

    `base_branch` is the integration line the merges landed on (the trunk,
    `main`, by default; pass the change branch when reverting a change-bounded
    train). The function name keeps the historical `_on_dev` suffix for
    call-site stability; the operation targets `base_branch`.

    Produces a single wrapper commit
    `revert(train-{ts}): rollback {WPs} — {reason}` on `dev`.

    Returns (success, message). On failure, the caller should NOT
    attempt branch restoration — investigate manually.
    """
    merged = [e for e in bundle if e.get("merge_sha_on_dev")]
    if not merged:
        return True, "no merged WPs to revert"

    # Checkout the trunk, fetch latest
    rc, _, err = _run(["git", "fetch", "origin", base_branch], cwd=clone_dir,
                     timeout=60)
    if rc != 0:
        return False, f"git fetch {base_branch} failed: {err}"
    rc, _, err = _run(["git", "checkout", "-B", base_branch, f"origin/{base_branch}"],
                     cwd=clone_dir, timeout=30)
    if rc != 0:
        return False, f"git checkout {base_branch} failed: {err}"

    # Revert each merge SHA in reverse order; --no-commit to stage all
    # changes into a single wrapper commit
    for entry in reversed(merged):
        sha = entry["merge_sha_on_dev"]
        rc, _, err = _run(
            ["git", "revert", "--no-commit", "-m", "1", sha],
            cwd=clone_dir, timeout=60,
        )
        if rc != 0:
            # If it's not a merge commit (-m fails), try plain revert
            rc, _, err = _run(["git", "revert", "--no-commit", sha],
                             cwd=clone_dir, timeout=60)
            if rc != 0:
                return False, f"git revert {sha[:8]} failed: {err}"

    wp_list = ", ".join(e.get("wp", "?") for e in merged)
    msg = f"revert({train_id}): rollback {wp_list} — {reason}"
    rc, _, err = _run(["git", "commit", "-m", msg], cwd=clone_dir, timeout=30)
    if rc != 0:
        return False, f"git commit (revert wrapper) failed: {err}"
    rc, _, err = _run(["git", "push", "origin", base_branch], cwd=clone_dir,
                     timeout=60)
    if rc != 0:
        return False, f"git push {base_branch} (revert) failed: {err}"
    return True, f"reverted {len(merged)} merges under wrapper commit"


def restore_branch_with_guard(
    repo: str,
    clone_dir: Path,
    branch: str,
    pre_train_sha: str,
    rebased_to_sha: str,
) -> tuple[bool, str]:
    """Restore a branch to its pre_train_sha — but only if no new push happened.

    Three paths:
    1. Branch missing on origin (GitHub's delete-branch-on-merge fired after
       the train's squash-merge, then the train decided to revert).
       → Push pre_train_sha as a fresh branch create. No guard needed
       because there's nothing on origin to clobber.
    2. Branch present on origin and matches `rebased_to_sha` (what the train
       left after rebase + push).
       → Force-push pre_train_sha. Standard restore.
    3. Branch present but doesn't match — someone else pushed since the
       train left it.
       → Abort with "newer push" warning; caller surfaces in BLOCKER.

    Returns (success, message). Success=False with message="newer push"
    is the guard firing.
    """
    # Path 1 check: is the branch still on origin at all? Use ls-remote
    # (read-only; doesn't care about local clone state).
    rc, out, _ = _run(
        ["git", "ls-remote", "--heads", "origin", branch],
        cwd=clone_dir, timeout=30,
    )
    if rc != 0:
        return False, f"git ls-remote origin {branch} failed"
    branch_on_origin = bool(out.strip())

    if not branch_on_origin:
        # GitHub auto-deleted the branch after squash-merge; restore via
        # fresh create-push of pre_train_sha. No --force needed.
        rc, _, err = _run(
            ["git", "push", "origin",
             f"{pre_train_sha}:refs/heads/{branch}"],
            cwd=clone_dir, timeout=60,
        )
        if rc != 0:
            return False, (
                f"branch missing on origin (likely auto-deleted by "
                f"delete-branch-on-merge); fresh-create push of "
                f"{pre_train_sha[:8]} failed: {err}"
            )
        return True, (
            f"branch was auto-deleted on origin; restored via fresh-create "
            f"push of pre_train_sha {pre_train_sha[:8]}"
        )

    # Path 2 / 3: branch exists on origin. Fetch with explicit refspec
    # (single-branch shallow clones don't auto-create the tracking ref).
    rc, _, err = _run(["git", "fetch", "origin",
                       f"{branch}:refs/remotes/origin/{branch}"],
                     cwd=clone_dir, timeout=60)
    if rc != 0:
        return False, f"git fetch {branch} failed: {err}"
    rc, out, _ = _run(
        ["git", "rev-parse", f"origin/{branch}"],
        cwd=clone_dir, timeout=10,
    )
    if rc != 0:
        return False, f"git rev-parse origin/{branch} failed"
    current = out.strip()

    if current != rebased_to_sha:
        return False, (
            f"newer push detected: origin/{branch} is at {current[:8]}, "
            f"train left {rebased_to_sha[:8]}. Skipping force-reset to "
            f"avoid overwriting unrelated work."
        )

    # Safe to restore
    rc, _, err = _run(
        ["git", "push", "--force-with-lease="
         f"{branch}:{rebased_to_sha}",
         "origin", f"+{pre_train_sha}:refs/heads/{branch}"],
        cwd=clone_dir, timeout=60,
    )
    if rc != 0:
        return False, f"git push --force-with-lease failed: {err}"
    return True, "restored"


# ─────────────────────────────────────────────────────────────────────────
# sulis-change helpers (CW-01..CW-08)
# ─────────────────────────────────────────────────────────────────────────
#
# The Change Work Standard at plugins/sulis/references/change-work-standard.md
# defines a change as the unit of work — every piece of work that evolves
# the system is bounded by a change/{primitive}-{slug} branch with a
# dedicated git worktree. The helpers below support the sulis-change CLI.
#


# CW-02: allowed primitives. Full 22 from change-primitives.md +
# Conventional Commits fallbacks for unclassified work.
_CHANGE_PRIMITIVES_EXPAND = ("create", "extend", "reuse", "compose", "generate")
_CHANGE_PRIMITIVES_REORGANISE = ("move", "refactor", "inline", "merge",
                                  "decompose", "abstract")
_CHANGE_PRIMITIVES_SUBSTITUTE = ("replace", "strangle", "wrap")
_CHANGE_PRIMITIVES_CONTRACT = ("deprecate", "delete")
_CHANGE_PRIMITIVES_REINFORCE = ("test", "instrument", "secure", "harden",
                                 "gate", "document")
_CHANGE_PRIMITIVES_CC_FALLBACK = ("feat", "fix", "chore")

ALLOWED_CHANGE_PRIMITIVES = (
    _CHANGE_PRIMITIVES_EXPAND
    + _CHANGE_PRIMITIVES_REORGANISE
    + _CHANGE_PRIMITIVES_SUBSTITUTE
    + _CHANGE_PRIMITIVES_CONTRACT
    + _CHANGE_PRIMITIVES_REINFORCE
    + _CHANGE_PRIMITIVES_CC_FALLBACK
)

# CW-02 slug rule: 2-5 kebab-case words. First word must start with a
# letter; subsequent words may be alphanumeric (so `wp-001` is valid).
_CHANGE_SLUG_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+){1,4}$")


# ─── Phase 5: ULID + handle generation (change-as-primitive design) ────────
#
# Per WORK_PACKAGE_STANDARD v1.1.0 + the change-as-primitive design doc:
# every change gets a 26-character Crockford-base32 ULID + a 6-character
# display handle (first 6 chars of the ULID). The ULID is the canonical
# identity (SaaS-ready by construction; sortable; collision-free); the
# handle is what humans + CLIs show ("CH-01HQ8X" — jj-style
# enough-to-disambiguate). The author-chosen slug remains the
# branch-friendly name.
#
# Implementation: inline ULID generator (no external dep). 48-bit ms
# timestamp + 80 bits of randomness, Crockford-base32 encoded.

import secrets as _secrets
import time as _time

_CROCKFORD_BASE32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _encode_crockford(value: int, length: int) -> str:
    """Encode an integer as Crockford-base32, left-padded to `length` chars."""
    if value < 0:
        raise ValueError("value must be non-negative")
    chars: list[str] = []
    for _ in range(length):
        chars.append(_CROCKFORD_BASE32[value & 0x1F])
        value >>= 5
    if value:
        raise ValueError(f"value too large for {length}-char Crockford-base32")
    return "".join(reversed(chars))


def generate_change_ulid(*, _now_ms: int | None = None,
                          _random_bytes: bytes | None = None) -> str:
    """Generate a 26-character Crockford-base32 ULID.

    The two underscore-prefixed parameters are for deterministic testing
    (inject a fixed timestamp and randomness). Production callers pass
    neither — the function reads the current time + secrets.token_bytes(10).
    """
    # 48 bits of timestamp (ms since epoch) → 10 Crockford chars
    timestamp_ms = _now_ms if _now_ms is not None else int(_time.time() * 1000)
    if timestamp_ms.bit_length() > 48:
        raise ValueError("timestamp exceeds 48 bits")
    timestamp_part = _encode_crockford(timestamp_ms, 10)

    # 80 bits of randomness → 16 Crockford chars
    random_bytes = _random_bytes if _random_bytes is not None else _secrets.token_bytes(10)
    if len(random_bytes) != 10:
        raise ValueError("randomness must be exactly 10 bytes (80 bits)")
    random_int = int.from_bytes(random_bytes, "big")
    random_part = _encode_crockford(random_int, 16)

    return timestamp_part + random_part


def ulid_handle(ulid: str) -> str:
    """Return the 6-character display handle for a ULID.

    The handle is `CH-{first-6-chars}` — "CH" for "change", then the
    first 6 Crockford-base32 characters of the ULID. The first 6 are
    derived from the timestamp portion (28 bits encoded across 6
    chars), so handles sort chronologically + collisions are rare in
    practice (would require two changes started in the same ~1-second
    window).
    """
    if len(ulid) != 26:
        raise ValueError(f"ULID must be 26 characters, got {len(ulid)}: {ulid!r}")
    return "CH-" + ulid[:6]


def validate_change_ulid(ulid: str) -> tuple[bool, str]:
    """Return (ok, reason). ULID must be 26 Crockford-base32 characters."""
    if not ulid:
        return False, "ULID is empty"
    if len(ulid) != 26:
        return False, f"ULID must be exactly 26 characters, got {len(ulid)}"
    for i, ch in enumerate(ulid):
        if ch not in _CROCKFORD_BASE32:
            return False, f"ULID has non-Crockford-base32 character {ch!r} at position {i}"
    return True, ""


def validate_change_slug(slug: str) -> tuple[bool, str]:
    """Return (ok, reason). Slug must be 2-5 kebab-case words."""
    if not slug:
        return False, "slug is empty"
    if not _CHANGE_SLUG_RE.match(slug):
        return False, (
            f"slug '{slug}' is not 2-5 kebab-case words "
            f"(e.g. 'introduce-payments', 'extract-http-client')"
        )
    return True, ""


def validate_change_primitive(primitive: str) -> tuple[bool, str]:
    """Return (ok, reason). Primitive must be one of ALLOWED_CHANGE_PRIMITIVES."""
    if not primitive:
        return False, "primitive is empty"
    if primitive.lower() not in ALLOWED_CHANGE_PRIMITIVES:
        return False, (
            f"primitive '{primitive}' not in allowed set: "
            f"{', '.join(ALLOWED_CHANGE_PRIMITIVES)}"
        )
    return True, ""


def compose_change_branch(primitive: str, slug: str) -> str:
    """Compose a CW-02 branch name: change/{primitive}-{slug}.

    Raises ValueError on invalid primitive or slug.
    """
    ok, reason = validate_change_primitive(primitive)
    if not ok:
        raise ValueError(reason)
    ok, reason = validate_change_slug(slug)
    if not ok:
        raise ValueError(reason)
    return f"change/{primitive.lower()}-{slug.lower()}"


def parse_change_branch(branch: str) -> tuple[str, str] | None:
    """Inverse of compose_change_branch. Returns (primitive, slug) or None."""
    if not branch.startswith("change/"):
        return None
    rest = branch[len("change/"):]
    # The primitive is the first dash-separated token; the slug is the rest.
    if "-" not in rest:
        return None
    first, _, slug = rest.partition("-")
    if first not in ALLOWED_CHANGE_PRIMITIVES:
        return None
    return (first, slug)


def change_worktree_path(repo_root: Path, primitive: str, slug: str) -> Path:
    """Compose the worktree path for a change.

    Convention: sibling of the main repo at
    `<repo-parent>/<repo-name>-change-<primitive>-<slug>/`.
    """
    return repo_root.parent / f"{repo_root.name}-change-{primitive}-{slug}"


def write_change_metadata(metadata_path: Path, data: dict) -> None:
    """Write a .changes/{primitive}-{slug}.yaml metadata file.

    Uses the same YAML-lite emitter pattern as write_train_run_record.
    Schema fields:
      slug: str
      primitive: str
      branch: str
      worktree_path: str
      base_branch: str
      base_sha: str
      started_at: ISO 8601 UTC
      adopted_from_sha: str | null   (only present for adopt)
      adopt_mode: str | null         (forward | rewrite)
    """
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for k in ("change_id", "handle", "slug", "primitive", "intent", "branch",
              "worktree_path", "base_branch", "base_sha", "started_at",
              "adopted_from_sha", "adopt_mode"):
        if k not in data:
            continue
        v = data[k]
        if v is None:
            lines.append(f"{k}: null")
        elif isinstance(v, (int, float)):
            lines.append(f"{k}: {v}")
        else:
            escaped = str(v).replace('"', '\\"')
            lines.append(f'{k}: "{escaped}"')
    metadata_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_change_metadata(metadata_path: Path) -> dict:
    """Read a metadata file written by write_change_metadata. Returns {} if missing."""
    if not metadata_path.exists():
        return {}
    out: dict = {}
    for raw in metadata_path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, rest = line.partition(":")
        key = key.strip()
        rest = rest.strip()
        if rest == "null":
            out[key] = None
        elif rest.startswith('"') and rest.endswith('"'):
            out[key] = rest[1:-1]
        else:
            try:
                out[key] = int(rest)
            except ValueError:
                out[key] = rest
    return out


def git_worktree_add(repo_root: Path, branch: str, dest: Path,
                     base_ref: str = "main") -> tuple[bool, str]:
    """Create a worktree at `dest` for a new branch off `base_ref`.

    If the branch already exists, the worktree is added on the existing
    branch. If `dest` already exists, returns (False, "destination exists").

    Returns (ok, message_or_error).
    """
    if dest.exists():
        return False, f"destination already exists: {dest}"

    # Check if branch already exists locally
    rc, out, _ = _run(["git", "rev-parse", "--verify", f"refs/heads/{branch}"],
                     cwd=repo_root, timeout=10)
    branch_exists = rc == 0

    if branch_exists:
        rc, _, err = _run(["git", "worktree", "add", str(dest), branch],
                         cwd=repo_root, timeout=60)
    else:
        rc, _, err = _run(["git", "worktree", "add", "-b", branch,
                          str(dest), base_ref],
                         cwd=repo_root, timeout=60)
    if rc != 0:
        return False, f"git worktree add failed: {err}"
    return True, str(dest)


def git_worktree_remove(repo_root: Path, dest: Path,
                        force: bool = False) -> tuple[bool, str]:
    """Remove a worktree at `dest`. Tolerates a missing worktree.

    Returns (ok, message).
    """
    if not dest.exists():
        # Try `git worktree prune` in case the worktree was deleted manually
        _run(["git", "worktree", "prune"], cwd=repo_root, timeout=10)
        return True, "worktree already absent (pruned)"
    args = ["git", "worktree", "remove", str(dest)]
    if force:
        args.append("--force")
    rc, _, err = _run(args, cwd=repo_root, timeout=30)
    if rc != 0:
        return False, f"git worktree remove failed: {err}"
    return True, "removed"


def detect_adopt_state(repo_root: Path,
                      remote_ref: str = "origin/main") -> dict:
    """Inspect the current repo state for `sulis-change adopt`.

    Returns a dict:
      {
        "current_branch": str,
        "has_uncommitted": bool,
        "uncommitted_files": list[str],
        "local_commits_ahead": list[str],   # commit SHAs
        "pushed_commits_can_rewrite": bool, # only true when current branch = remote tracking branch and there's no work upstream
        "base_sha": str,                     # remote_ref's SHA
      }

    Used by sulis-change adopt to pick the right retrofit flavour.
    """
    out: dict = {
        "current_branch": "",
        "has_uncommitted": False,
        "uncommitted_files": [],
        "local_commits_ahead": [],
        "pushed_commits_can_rewrite": False,
        "base_sha": "",
    }

    # Current branch
    rc, branch_out, _ = _run(["git", "branch", "--show-current"],
                             cwd=repo_root, timeout=10)
    if rc == 0:
        out["current_branch"] = branch_out.strip()

    # Uncommitted changes
    rc, status_out, _ = _run(["git", "status", "--porcelain"],
                             cwd=repo_root, timeout=10)
    if rc == 0 and status_out.strip():
        out["has_uncommitted"] = True
        out["uncommitted_files"] = [
            line[3:].strip() for line in status_out.splitlines()
            if line.strip()
        ]

    # Fetch the remote ref's SHA (best-effort)
    rc, remote_sha_out, _ = _run(["git", "rev-parse", remote_ref],
                                 cwd=repo_root, timeout=10)
    if rc == 0:
        out["base_sha"] = remote_sha_out.strip()

    # Commits ahead of remote
    rc, ahead_out, _ = _run(
        ["git", "rev-list", f"{remote_ref}..HEAD"],
        cwd=repo_root, timeout=10,
    )
    if rc == 0 and ahead_out.strip():
        out["local_commits_ahead"] = [
            sha.strip() for sha in ahead_out.splitlines() if sha.strip()
        ]

    # "Pushed commits to retrofit" requires --mode rewrite; we don't auto-detect
    # this state because it's ambiguous without intent. The caller passes
    # --mode rewrite to enter that path.

    return out


# ─── Worktree-safe uncommitted-work transfer (issue #53) ──────────────────
#
# ``git stash`` operates on a single stack PER REPOSITORY, shared across ALL
# of that repo's worktrees. The change-as-primitive model spawns many
# sibling worktrees per repo, so a positional ``git stash pop`` in one
# worktree can silently consume an *unrelated* sibling worktree's stash
# (the DC-04 incident: an adopt popped a hardening stash pushed from a
# different worktree and dumped its files in as cruft).
#
# These helpers transfer uncommitted work between trees with EXPLICIT,
# worktree-local file movement — never the shared stash stack — so a
# sibling worktree's stash is never observed, applied, or dropped.


def _capture_worktree_changes(source_root: Path) -> tuple[bool, str, dict]:
    """Capture the source tree's uncommitted work without moving it.

    Returns (ok, message, capture) where ``capture`` is a dict with:
      - ``patch``: the ``git diff HEAD --binary`` text (staged + unstaged
        delta relative to HEAD), or "" if there is none.
      - ``untracked``: list of {"path": rel, "bytes": <file content>} for
        each untracked, non-ignored regular file. The content is snapshotted
        at capture time so the capture remains valid even after the source
        tree is cleaned (the combined local-commits path cleans the source
        BEFORE applying to the worktree).
      - ``untracked_symlinks``: list of {"path": rel, "target": <link
        target>} for each untracked, non-ignored symlink (whether it points
        at a file OR a directory). Captured as the link target string so the
        symlink is re-materialised AS A SYMLINK at apply time — never
        followed-and-transmuted into a regular file, never silently dropped.

    Does NOT modify the source tree — pair with :func:`_clean_source_worktree`
    after the captured work has been applied to the destination.
    """
    rc, patch_text, err = _run(["git", "diff", "HEAD", "--binary"],
                               cwd=source_root, timeout=60)
    if rc != 0:
        return False, f"git diff HEAD failed: {err}", {}

    rc, others_out, err = _run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=source_root, timeout=30,
    )
    if rc != 0:
        return False, f"git ls-files --others failed: {err}", {}

    untracked: list[dict] = []
    untracked_symlinks: list[dict] = []
    for rel in others_out.splitlines():
        rel = rel.strip()
        if not rel:
            continue
        src_path = source_root / rel
        # Check symlink-ness FIRST: a symlink-to-file would otherwise pass
        # is_file() (which follows the link) and get transmuted into a
        # regular file; a symlink-to-directory would be skipped entirely.
        if src_path.is_symlink():
            untracked_symlinks.append(
                {"path": rel, "target": os.readlink(src_path)}
            )
            continue
        if not src_path.is_file():
            continue
        untracked.append({"path": rel, "bytes": src_path.read_bytes()})

    return True, "captured", {
        "patch": patch_text,
        "untracked": untracked,
        "untracked_symlinks": untracked_symlinks,
    }


def _apply_worktree_changes(
    source_root: Path,
    dest_worktree: Path,
    capture: dict,
) -> tuple[bool, str]:
    """Apply a capture from :func:`_capture_worktree_changes` into a clean
    destination worktree: ``git apply`` the tracked delta and write each
    snapshotted untracked file to the same relative path. Does not touch the
    source tree.

    ``source_root`` is accepted for call-site symmetry with the other
    transfer helpers; the capture is self-contained (it snapshots untracked
    content), so this function never reads from the source tree.
    """
    _ = source_root  # capture is self-contained; source no longer read here
    patch_text = capture.get("patch", "")
    untracked = capture.get("untracked", [])
    untracked_symlinks = capture.get("untracked_symlinks", [])

    if patch_text.strip():
        # A temp file (not stdin) keeps binary hunks intact and avoids any
        # shell-quoting hazard on the diff text.
        fd, patch_path = tempfile.mkstemp(prefix="sulis-adopt-", suffix=".patch")
        try:
            with os.fdopen(fd, "w") as fh:
                fh.write(patch_text)
            rc, _, err = _run(["git", "apply", patch_path],
                             cwd=dest_worktree, timeout=60)
            if rc != 0:
                return False, f"git apply of tracked delta failed: {err}"
        finally:
            try:
                os.unlink(patch_path)
            except OSError:
                pass

    for entry in untracked:
        dest_file = dest_worktree / entry["path"]
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        dest_file.write_bytes(entry["bytes"])

    # Re-materialise untracked symlinks AS symlinks (preserve fidelity).
    for entry in untracked_symlinks:
        dest_link = dest_worktree / entry["path"]
        dest_link.parent.mkdir(parents=True, exist_ok=True)
        if dest_link.is_symlink() or dest_link.exists():
            dest_link.unlink()
        os.symlink(entry["target"], dest_link)

    return True, "applied"


def _clean_source_worktree(
    source_root: Path,
    capture: dict,
) -> tuple[bool, str]:
    """Clear the captured work from the source tree: restore tracked files
    to HEAD and remove the moved untracked files. This matches the old
    stash-push semantics (push cleared the source tree) — it is the adopt
    contract, not new destructive behaviour.
    """
    untracked = capture.get("untracked", [])
    untracked_symlinks = capture.get("untracked_symlinks", [])

    # Tracked files: restore to HEAD (drops staged + unstaged edits).
    rc, _, err = _run(["git", "restore", "--staged", "--worktree", "."],
                     cwd=source_root, timeout=30)
    if rc != 0:
        # Older gits without `git restore`: fall back to reset + checkout.
        _run(["git", "reset", "--quiet", "HEAD", "."],
             cwd=source_root, timeout=30)
        rc, _, err = _run(["git", "checkout", "--", "."],
                         cwd=source_root, timeout=30)
        if rc != 0:
            return False, f"failed to restore source tree: {err}"

    # Untracked files + symlinks: remove the ones we moved.
    for entry in (*untracked, *untracked_symlinks):
        rel = entry["path"]
        src_path = source_root / rel
        try:
            if src_path.is_symlink() or src_path.is_file():
                src_path.unlink()
        except OSError as exc:  # pragma: no cover - defensive
            return False, f"failed to remove moved untracked file {rel}: {exc}"

    return True, "source cleaned"


def persist_capture_durably(capture: dict) -> tuple[bool, str, Path | None]:
    """Write an in-memory :func:`_capture_worktree_changes` capture to a
    durable on-disk location OUTSIDE any worktree, so the founder's
    uncommitted work survives a failure between source-clean and apply.

    The combined local-commits adopt path cleans the source tree while the
    ONLY surviving copy of the uncommitted work is the in-memory ``capture``
    dict. A cherry-pick or apply failure after that point would discard the
    capture on process exit — silent data loss. This mirrors the durability
    the old ``git stash push -u`` gave (an on-disk park recoverable via
    ``git stash list``): persist before destroying the source, surface the
    location on failure, discard on success.

    Layout under the recovery dir:
      - ``tracked.patch``  — the ``git diff HEAD --binary`` text (if any).
      - ``untracked/<rel>`` — each snapshotted untracked regular file.
      - ``symlinks.txt``   — one ``<rel> -> <target>`` line per untracked
        symlink (recorded as text since a symlink target may point outside
        the recovery dir).

    Returns (ok, message, recovery_dir). On success the caller owns the dir
    and MUST either surface it (failure path) or
    :func:`discard_persisted_capture` it (success path).
    """
    patch_text = capture.get("patch", "")
    untracked = capture.get("untracked", [])
    untracked_symlinks = capture.get("untracked_symlinks", [])

    try:
        recovery_dir = Path(
            tempfile.mkdtemp(prefix="sulis-adopt-recovery-")
        )
    except OSError as exc:
        return False, f"could not create durable recovery dir: {exc}", None

    try:
        if patch_text.strip():
            (recovery_dir / "tracked.patch").write_text(patch_text)

        for entry in untracked:
            dest = recovery_dir / "untracked" / entry["path"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(entry["bytes"])

        if untracked_symlinks:
            lines = [
                f"{e['path']} -> {e['target']}" for e in untracked_symlinks
            ]
            (recovery_dir / "symlinks.txt").write_text(
                "\n".join(lines) + "\n"
            )
    except OSError as exc:
        # Best-effort cleanup of the half-written dir; report the failure so
        # the caller does NOT destroy the source (the durable copy is the
        # safety net and it failed).
        shutil.rmtree(recovery_dir, ignore_errors=True)
        return False, f"failed to persist capture durably: {exc}", None

    return True, "persisted", recovery_dir


def discard_persisted_capture(recovery_dir: Path | None) -> None:
    """Remove a durable recovery dir created by
    :func:`persist_capture_durably`. Called on the adopt success path — the
    durable copy exists only as a failure safety net, not as cruft.
    """
    if recovery_dir is None:
        return
    shutil.rmtree(recovery_dir, ignore_errors=True)


def transfer_worktree_changes(
    source_root: Path,
    dest_worktree: Path,
) -> tuple[bool, str]:
    """Move the source tree's *uncommitted* working-tree work into a clean
    destination worktree, WITHOUT touching git's shared per-repo stash stack.

    Single shared primitive for the adopt path (issue #53, EP-03): capture
    the tracked delta + untracked files, apply them into ``dest_worktree``,
    then clean the source tree. No ``git stash`` is used anywhere, so a
    sibling worktree's stash on the shared stack is never observed, applied,
    or dropped.

    Returns (ok, message_or_error). On any failure before the source tree is
    cleaned, the source tree is left intact (the caller can re-try).
    """
    ok, msg, capture = _capture_worktree_changes(source_root)
    if not ok:
        return False, msg

    ok, msg = _apply_worktree_changes(source_root, dest_worktree, capture)
    if not ok:
        return False, msg

    ok, msg = _clean_source_worktree(source_root, capture)
    if not ok:
        return False, msg

    n = (1 if capture["patch"].strip() else 0) + len(capture["untracked"])
    return True, f"transferred {n} working-tree change(s) via explicit file movement"


def adopt_uncommitted_into_change(
    repo_root: Path,
    branch: str,
    base_ref: str,
    worktree_dest: Path,
    uncommitted_files: list[str],
) -> tuple[bool, str]:
    """Retrofit case 1: move uncommitted changes into a new change worktree.

    Worktree-safe (issue #53): instead of ``git stash push``/positional
    ``git stash pop`` — which share a per-repo stack and can grab a sibling
    worktree's stash — this creates the change worktree off ``base_ref``
    (clean) and transfers the uncommitted work via
    :func:`transfer_worktree_changes` (explicit file movement, never the
    shared stash stack).

    Returns (ok, message).
    """
    if not uncommitted_files:
        # Nothing to move — caller should not call this
        return True, "no uncommitted changes; nothing to adopt"

    # Create the change branch + worktree off the base ref (clean state).
    # We do this BEFORE capturing/clearing the source tree so a worktree-add
    # failure leaves the source work untouched.
    ok, msg = git_worktree_add(repo_root, branch, worktree_dest, base_ref)
    if not ok:
        return False, f"worktree creation failed: {msg}"

    # Move the uncommitted work into the worktree without using the stash.
    ok, msg = transfer_worktree_changes(repo_root, worktree_dest)
    if not ok:
        return False, f"worktree-safe transfer failed: {msg}"

    return True, f"adopted {len(uncommitted_files)} uncommitted change(s) into {branch}"


def adopt_local_commits_into_change(
    repo_root: Path,
    branch: str,
    base_ref: str,
    worktree_dest: Path,
    local_commits: list[str],
) -> tuple[bool, str]:
    """Retrofit case 2: cherry-pick local-only commits onto the change
    branch, then reset local dev to the remote.

    Returns (ok, message).
    """
    if not local_commits:
        return True, "no local commits to retrofit"

    current_branch = ""
    rc, branch_out, _ = _run(["git", "branch", "--show-current"],
                             cwd=repo_root, timeout=10)
    if rc == 0:
        current_branch = branch_out.strip()

    # Create change branch + worktree (off the base ref, which is the
    # remote tip — the place we want to relocate FROM)
    ok, msg = git_worktree_add(repo_root, branch, worktree_dest, base_ref)
    if not ok:
        return False, f"worktree creation failed: {msg}"

    # Cherry-pick the local commits (in chronological order) into the worktree.
    # local_commits is newest-first from rev-list, so reverse for cherry-pick order.
    for sha in reversed(local_commits):
        rc, _, err = _run(["git", "cherry-pick", sha],
                         cwd=worktree_dest, timeout=60)
        if rc != 0:
            # Abort + return; user can investigate
            _run(["git", "cherry-pick", "--abort"], cwd=worktree_dest, timeout=10)
            return False, f"cherry-pick {sha[:8]} failed: {err}"

    # Reset local current_branch (the place we relocated FROM) to the remote tip
    if current_branch:
        rc, _, err = _run(
            ["git", "reset", "--hard", base_ref],
            cwd=repo_root, timeout=30,
        )
        if rc != 0:
            return False, (
                f"reset {current_branch} to {base_ref} failed: {err}. "
                f"Change branch was created; you may need to manually reset "
                f"{current_branch}."
            )

    return True, (
        f"retrofitted {len(local_commits)} commit(s) from "
        f"{current_branch} onto {branch}; {current_branch} reset to {base_ref}"
    )


def find_change_branches(repo_root: Path) -> list[dict]:
    """List all change/* branches in the local repo with basic state.

    Returns a list of dicts:
      [{"branch": str, "primitive": str, "slug": str, "current": bool}, ...]
    """
    rc, out, _ = _run(["git", "branch", "--list", "change/*"],
                     cwd=repo_root, timeout=10)
    if rc != 0:
        return []

    result: list[dict] = []
    seen: set[str] = set()
    for raw in out.splitlines():
        line = raw.rstrip()
        if not line:
            continue
        # git branch output: "* branch" (current), "+ branch" (other
        # worktree), "  branch" (uncheckout). Strip the marker.
        is_current = line.startswith("* ")
        branch = line.lstrip("*+ \t").strip()
        if not branch:
            continue
        parsed = parse_change_branch(branch)
        if parsed is None:
            continue
        primitive, slug = parsed
        seen.add(branch)
        result.append({
            "branch": branch,
            "primitive": primitive,
            "slug": slug,
            "current": is_current,
        })

    # Also surface origin-only change branches (a teammate's change pulled but
    # not checked out locally). Strip the `origin/` prefix to the logical
    # branch name; skip any already listed as a local branch. (L-01)
    rrc, rout, _ = _run(
        ["git", "branch", "--list", "--remotes", "origin/change/*"],
        cwd=repo_root, timeout=10,
    )
    if rrc == 0:
        for raw in rout.splitlines():
            line = raw.strip()
            if not line or "->" in line:  # skip "origin/HEAD -> origin/dev"
                continue
            if line.startswith("origin/"):
                branch = line[len("origin/"):]
            else:
                continue
            if branch in seen:
                continue
            parsed = parse_change_branch(branch)
            if parsed is None:
                continue
            primitive, slug = parsed
            seen.add(branch)
            result.append({
                "branch": branch,
                "primitive": primitive,
                "slug": slug,
                "current": False,
            })
    return result


# ─── Phase 5: SULIS_CHANGE_ID env-var binding + back-integration ──────────
#
# Per the change-as-primitive design + lifecycle.md Step 0 / Step 12.5
# amendments. The calling session reads SULIS_CHANGE_ID to know which
# change context it's operating in, and invokes back_integrate_change_branch
# at Step 0 (defence in depth, before WP starts) and Step 12.5 (active
# driver, after WP merges back to change).

SULIS_CHANGE_ID_ENV_VAR = "SULIS_CHANGE_ID"


def resolve_current_change(repo_root: Path | None = None) -> dict | None:
    """Resolve the current change context from the SULIS_CHANGE_ID env var.

    Returns the change metadata dict ({change_id, handle, branch, primitive,
    slug, worktree_path, ...}) when the env var is set AND a matching change's
    metadata is found. Returns None when the env var is unset, or set but no
    match.

    Resolution order (L-01 — cwd-first, then fall back):

      1. **Self** — the common case where this is invoked from INSIDE the
         change worktree (cwd == the worktree). Metadata travels ON the
         change branch, so it's already at `repo_root/.changes/`. Read the
         current branch directly and the committed metadata beside it. The
         pre-L-01 code only computed a SIBLING worktree path and so returned
         None here even with the env var set and a valid manifest.
      2. **`.changes/` scan** — scan `repo_root/.changes/*.yaml` for any whose
         change_id matches (covers a detached HEAD / odd branch name but
         committed metadata).
      3. **Sibling worktree iteration** — the original path: driving from the
         MAIN repo, the metadata lives in the sibling change worktree. Now
         also covers origin-only change branches via find_change_branches.

    When the env var is set but nothing matches, a breadcrumb of the paths
    checked is written to stderr (debugging aid; never pollutes stdout JSON).
    """
    change_id = os.environ.get(SULIS_CHANGE_ID_ENV_VAR)
    if not change_id:
        return None

    if repo_root is None:
        repo_root = Path.cwd().resolve()
    else:
        repo_root = Path(repo_root).resolve()

    checked: list[str] = []

    # 1. Self: current branch + metadata committed at repo_root/.changes/.
    rc, branch_out, _ = _run(
        ["git", "branch", "--show-current"], cwd=repo_root, timeout=10,
    )
    if rc == 0:
        parsed = parse_change_branch(branch_out.strip())
        if parsed is not None:
            primitive, slug = parsed
            self_meta = repo_root / ".changes" / f"{primitive}-{slug}.yaml"
            checked.append(str(self_meta))
            if self_meta.exists():
                metadata = read_change_metadata(self_meta)
                if metadata.get("change_id") == change_id:
                    return metadata

    # 2. Scan repo_root/.changes/ for any manifest matching this change_id.
    changes_dir = repo_root / ".changes"
    if changes_dir.is_dir():
        for meta_file in sorted(changes_dir.glob("*.yaml")):
            checked.append(str(meta_file))
            metadata = read_change_metadata(meta_file)
            if metadata.get("change_id") == change_id:
                return metadata

    # 2.5 Co-located worktree (ADE relocation): the worktree lives at
    #     ~/.sulis/changes/{change_id}/worktree, so its committed manifest is
    #     at .../worktree/.changes/{primitive}-{slug}.yaml. Read it directly by
    #     change_id — this resolves a co-located change when driving from
    #     anywhere (the main repo, an unrelated dir), without iterating siblings.
    try:
        from _change_state import change_worktree_dir  # lazy: avoid import coupling
        co_changes = change_worktree_dir(change_id) / ".changes"
        if co_changes.is_dir():
            for meta_file in sorted(co_changes.glob("*.yaml")):
                checked.append(str(meta_file))
                metadata = read_change_metadata(meta_file)
                if metadata.get("change_id") == change_id:
                    return metadata
    except Exception:
        pass  # best-effort; fall through to sibling iteration

    # 3. Sibling worktree iteration (driving from the main repo; includes
    #    origin-only change branches via find_change_branches).
    for entry in find_change_branches(repo_root):
        primitive = entry["primitive"]
        slug = entry["slug"]
        worktree_dest = change_worktree_path(repo_root, primitive, slug)
        metadata_path = worktree_dest / ".changes" / f"{primitive}-{slug}.yaml"
        checked.append(str(metadata_path))
        if not metadata_path.exists():
            continue
        metadata = read_change_metadata(metadata_path)
        if metadata.get("change_id") == change_id:
            return metadata

    # Env var set but nothing matched — leave a breadcrumb for debugging.
    print(
        f"resolve_current_change: SULIS_CHANGE_ID={change_id} set but no "
        f"matching metadata found. Checked: {checked or '(no candidates)'}",
        file=sys.stderr,
    )
    return None


def back_integrate_change_branch(
    repo_root: Path,
    change_branch: str,
    dev_ref: str = "origin/main",
    *,
    fetch_first: bool = True,
) -> dict:
    """Auto back-integration mechanic per CW-04 + lifecycle Step 0 / Step 12.5.

    Runs `git fetch origin dev` (unless fetch_first=False) + checks whether
    `dev_ref` is ancestor of the change branch HEAD; if not, runs
    `git merge --no-edit origin/dev` to bring the change branch current.

    Per CW-04: merge-not-rebase (preserves commit SHAs so in-flight WP
    worktrees stay valid).

    The function MUST be called from within the change worktree (HEAD ==
    change branch). Caller is responsible for ensuring this.

    Returns a structured result dict:

    - {"status": "already_current", "change_branch": ...}
    - {"status": "merged_ok", "change_branch": ..., "merged_commits": N}
    - {"status": "fetch_failed", "error": "..."}
    - {"status": "merge_conflict", "files": [...], "guidance": "..."}
    - {"status": "internal_error", "error": "..."}

    The caller is expected to handle each status:
    - "already_current" → proceed normally (no-op)
    - "merged_ok" → push the merged change branch, proceed
    - "fetch_failed" → retry or surface as BLOCKER
    - "merge_conflict" → surface to founder per CW-04 three-option dialog
    - "internal_error" → BLOCKER

    See lifecycle.md Step 0 + Step 12.5 for the full failure-handling OODA.
    """
    repo_root = Path(repo_root).resolve()

    # Step 1: fetch dev (unless caller said don't — useful in tests)
    if fetch_first:
        rc, _, stderr = _run(
            ["git", "fetch", "origin", dev_ref.split("/", 1)[-1] if "/" in dev_ref else "dev"],
            cwd=repo_root,
            timeout=60,
        )
        if rc != 0:
            return {
                "status": "fetch_failed",
                "change_branch": change_branch,
                "error": stderr.strip() or "git fetch returned non-zero",
            }

    # Step 2: is dev_ref already an ancestor of HEAD?
    rc, _, _ = _run(
        ["git", "merge-base", "--is-ancestor", dev_ref, "HEAD"],
        cwd=repo_root,
        timeout=10,
    )
    if rc == 0:
        # Already an ancestor → change branch is at or ahead of dev
        return {
            "status": "already_current",
            "change_branch": change_branch,
            "dev_ref": dev_ref,
        }

    # Step 3: count how many commits are coming in (informational)
    rc_count, count_out, _ = _run(
        ["git", "rev-list", "--count", f"HEAD..{dev_ref}"],
        cwd=repo_root,
        timeout=10,
    )
    merged_commits = int(count_out.strip()) if rc_count == 0 and count_out.strip().isdigit() else 0

    # Step 4: merge (no rebase — preserves SHAs for in-flight WP worktrees)
    rc, _, stderr = _run(
        ["git", "merge", "--no-edit", dev_ref],
        cwd=repo_root,
        timeout=120,
    )
    if rc == 0:
        return {
            "status": "merged_ok",
            "change_branch": change_branch,
            "dev_ref": dev_ref,
            "merged_commits": merged_commits,
        }

    # Step 5: merge failed → check for conflict
    rc_diff, diff_out, _ = _run(
        ["git", "diff", "--name-only", "--diff-filter=U"],
        cwd=repo_root,
        timeout=10,
    )
    if rc_diff == 0 and diff_out.strip():
        conflict_files = [line.strip() for line in diff_out.splitlines() if line.strip()]
        return {
            "status": "merge_conflict",
            "change_branch": change_branch,
            "dev_ref": dev_ref,
            "files": conflict_files,
            "guidance": (
                "Per CW-04, three options: (1) resolve interactively, (2) "
                "defer (continue on stale branch; surfaces again next time), "
                "(3) abort this WP. Do NOT auto-resolve."
            ),
        }

    # Step 6: merge failed but not a conflict — internal error
    return {
        "status": "internal_error",
        "change_branch": change_branch,
        "dev_ref": dev_ref,
        "error": stderr.strip() or "git merge returned non-zero with no conflict files",
    }


def ff_local_change_branch_from_origin(
    repo_root: Path,
    change_branch: str,
    *,
    fetch_first: bool = True,
) -> dict:
    """Fast-forward the change worktree's HEAD to `origin/<change_branch>`.

    #141: after wpx-pipeline squash-merges a WP into the change branch via
    the GitHub API, the squash commit lands on `origin/<change_branch>` but
    the LOCAL change worktree (where the calling session and subsequent
    agents read files from) is still at the pre-merge SHA. The next agent
    (e.g. the Step 11 security-review) reads stale files and reports a false
    "CANNOT REVIEW" verdict. Fast-forwarding the worktree here closes that
    gap before any post-pipeline agent dispatches.

    Caller MUST invoke this from inside the change worktree (HEAD ==
    change branch).

    Returns:
    - {"status": "already_current", "change_branch": ...}
    - {"status": "fast_forwarded", "change_branch": ..., "advanced_commits": N}
    - {"status": "fetch_failed", "error": "..."}
    - {"status": "ff_not_possible", "error": "..."}  # local diverged
    - {"status": "internal_error", "error": "..."}

    The caller is expected to handle each status:
    - "already_current" / "fast_forwarded" → proceed
    - "fetch_failed" / "ff_not_possible" → log + continue (defence in depth:
      the next Step 0 will retry); the merge already landed on origin.
    - "internal_error" → log + continue (same rationale).
    """
    repo_root = Path(repo_root).resolve()
    origin_ref = f"origin/{change_branch}"

    # Step 1: fetch the change branch from origin so the local tracking ref
    # carries any merge commits pushed there since.
    if fetch_first:
        rc, _, stderr = _run(
            ["git", "fetch", "origin", change_branch],
            cwd=repo_root,
            timeout=60,
        )
        if rc != 0:
            return {
                "status": "fetch_failed",
                "change_branch": change_branch,
                "error": stderr.strip() or "git fetch returned non-zero",
            }

    # Step 2: is origin/<change_branch> already an ancestor of HEAD? Then
    # the local worktree is at or ahead of origin — nothing to do.
    rc, _, _ = _run(
        ["git", "merge-base", "--is-ancestor", origin_ref, "HEAD"],
        cwd=repo_root,
        timeout=10,
    )
    if rc == 0:
        return {
            "status": "already_current",
            "change_branch": change_branch,
        }

    # Step 3: count how many commits we're about to advance (informational).
    rc_count, count_out, _ = _run(
        ["git", "rev-list", "--count", f"HEAD..{origin_ref}"],
        cwd=repo_root,
        timeout=10,
    )
    advanced_commits = (
        int(count_out.strip())
        if rc_count == 0 and count_out.strip().isdigit()
        else 0
    )

    # Step 4: fast-forward. --ff-only refuses to create a merge commit, so
    # local divergence is surfaced explicitly rather than silently merged.
    rc, _, stderr = _run(
        ["git", "merge", "--ff-only", origin_ref],
        cwd=repo_root,
        timeout=60,
    )
    if rc == 0:
        return {
            "status": "fast_forwarded",
            "change_branch": change_branch,
            "advanced_commits": advanced_commits,
        }

    # Step 5: --ff-only refused → local has diverged from origin.
    return {
        "status": "ff_not_possible",
        "change_branch": change_branch,
        "error": (
            stderr.strip()
            or "git merge --ff-only refused; local change branch has diverged"
        ),
    }
