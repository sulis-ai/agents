"""Deterministic depth classifier for /sulis:specify (Phase 6b).

Proposes one of three Specify depth modes — "lite" / "standard" / "deep" —
from three deterministic signals the caller gathers:

  - primitive    : the change's kind, from the change manifest (one of the
                   22 change primitives, the 3 Conventional-Commits fallbacks,
                   or None / unknown).
  - file_count   : how many files the change touches. Best-effort: at specify
                   time there may be zero commits, so this can be None.
  - founder_facing: does the change touch a user-visible surface? Computed by
                   the caller, e.g. via paths_touch_founder_surface().

Per the change-as-primitive design (§ "Depth modes for Specify (always on)"):
**on uncertainty, default to standard.** The classifier only *proposes*; the
founder confirms or overrides in the skill. Lite is the escape valve for
trivial mechanical work; deep is reserved for new features / new systems /
anything user-facing or cross-team.

Pure function — no I/O, no git, no env reads. Stdlib only. The skill is
responsible for gathering the signals and for the confirm/override dialog.

See:
  - plugins/sulis/docs/change-as-primitive-design.md
  - plugins/sulis/references/change-primitives.md
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ─── Primitive → base-depth lean ───────────────────────────────────────────
#
# Primitives that are usually trivial and self-contained (single mechanical
# unit of work). When small + internal they propose lite.
LITE_PRIMITIVES: frozenset[str] = frozenset(
    {
        "fix",       # bug fix, often one file
        "chore",     # housekeeping / typo / config
        "delete",    # remove confirmed-dead code
        "inline",    # remove one indirection
        "document",  # docs touch-up
    }
)

# Primitives that introduce net-new behaviour, a new surface, or a structural
# replacement strategy — full-SRD territory. When large or founder-facing they
# propose deep.
DEEP_PRIMITIVES: frozenset[str] = frozenset(
    {
        "create",    # net-new module / capability / surface
        "compose",   # orchestrate existing pieces into new behaviour
        "generate",  # scaffold a new surface
        "strangle",  # strangler-fig replacement of a legacy surface
    }
)

# Thresholds (deterministic). A change touching more files than the lite
# ceiling is no longer a single mechanical unit; a change at or above the deep
# floor that is also founder-facing is full-SRD territory.
LITE_FILE_CEILING = 3   # > this many files → not lite
DEEP_FILE_FLOOR = 5     # >= this many files (with founder-facing) → deep

# ─── Founder-surface path heuristic ─────────────────────────────────────────
#
# Path fragments that signal a user-visible surface. Lower-cased substring
# match against each touched path. Conservative on purpose: a false negative
# (missing a surface) is corrected by the founder at confirm time; the goal is
# a sensible *proposal*, never a silent commitment.
_FOUNDER_SURFACE_FRAGMENTS: tuple[str, ...] = (
    "component",   # src/components/...
    "/pages/",
    "/page/",
    "/views/",
    "/view/",
    "/screens/",
    "/routes/",
    "/route/",
    "/templates/",
    "/template/",
    "/email/",
    "/emails/",
    "/ui/",
    "/public/",
    "/static/",
    ".tsx",
    ".jsx",
    ".vue",
    ".svelte",
    ".html",
)

# Path fragments that mark internal-only work — never a founder surface by
# themselves. Checked first so a test or lib file does not trip a broad
# surface fragment.
_INTERNAL_ONLY_FRAGMENTS: tuple[str, ...] = (
    "/tests/",
    "/test/",
    "test_",
    "_test.",
    ".spec.",
    "/migrations/",
)


def _is_internal_only(path: str) -> bool:
    low = path.lower()
    return any(frag in low for frag in _INTERNAL_ONLY_FRAGMENTS)


def paths_touch_founder_surface(paths: list[str]) -> bool:
    """Return True if any path looks like a user-visible surface.

    A path that matches an internal-only fragment (tests, migrations) does not
    on its own count as a founder surface. A path matching a surface fragment
    and *not* internal-only counts.
    """
    for path in paths:
        if _is_internal_only(path):
            continue
        low = path.lower()
        if any(frag in low for frag in _FOUNDER_SURFACE_FRAGMENTS):
            return True
    return False


# ─── Decision ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class DepthDecision:
    """A proposed Specify depth + the reason + the signals it was based on."""

    depth: str               # "lite" | "standard" | "deep"
    reason: str              # plain-English why (founder-readable)
    signals: dict = field(default_factory=dict)


def classify_depth(
    *,
    primitive: str | None,
    file_count: int | None,
    founder_facing: bool,
) -> DepthDecision:
    """Propose a Specify depth from the three deterministic signals.

    Rules (deterministic, evaluated in order; on uncertainty → standard):

    1. Founder-facing + sizeable (>= deep floor) → **deep**.
       User-visible, multi-file work is full-SRD territory.
    2. A deep-leaning primitive (create / compose / generate / strangle) that
       is not a one-file stub → **deep**.
    3. A lite-leaning primitive (fix / chore / delete / inline / document),
       small (<= lite ceiling), and internal → **lite**.
       If it sprawls past the ceiling or touches a user surface → **standard**.
    4. Everything else, and every unknown / uncertain case → **standard**
       (the safe default).
    """
    signals = {
        "primitive": primitive,
        "file_count": file_count,
        "founder_facing": founder_facing,
    }
    fc = file_count if isinstance(file_count, int) else None
    prim = (primitive or "").strip().lower()

    # Rule 1 — user-visible + sizeable → deep.
    if founder_facing and fc is not None and fc >= DEEP_FILE_FLOOR:
        return DepthDecision(
            depth="deep",
            reason=(
                "This touches what your users see and spans several files, so "
                "it's worth specifying fully before building."
            ),
            signals=signals,
        )

    # Rule 2 — net-new / replacement primitive that isn't a one-file stub.
    if prim in DEEP_PRIMITIVES and (fc is None or fc > 1):
        return DepthDecision(
            depth="deep",
            reason=(
                "This adds something new to the product, so a full spec — with "
                "the flows drawn out — pays off here."
            ),
            signals=signals,
        )

    # Rule 3 — small mechanical primitive, internal, few files → lite.
    if prim in LITE_PRIMITIVES and not founder_facing:
        if fc is not None and fc > LITE_FILE_CEILING:
            return DepthDecision(
                depth="standard",
                reason=(
                    "This started out small but spreads across several files, "
                    "so a short spec keeps it on track."
                ),
                signals=signals,
            )
        return DepthDecision(
            depth="lite",
            reason=(
                "This looks like a small, contained change, so a quick "
                "three-line spec should be plenty."
            ),
            signals=signals,
        )

    # A lite-leaning primitive that IS founder-facing → at least standard.
    if prim in LITE_PRIMITIVES and founder_facing:
        return DepthDecision(
            depth="standard",
            reason=(
                "It's a small change, but it touches what your users see, so "
                "let's capture the scope properly."
            ),
            signals=signals,
        )

    # Rule 4 — the safe default. Covers unknown primitives, mid-size work,
    # and every uncertain case.
    return DepthDecision(
        depth="standard",
        reason=(
            "This sits in the middle — not trivial, not a whole new system — "
            "so the standard spec (a few questions) is the right fit. "
            "Defaulting to standard when it's not clear-cut."
        ),
        signals=signals,
    )


# ─── Plain-English proposal sentence (founder-mode) ─────────────────────────


# FR-04: these describe the INTERVIEW size (how many questions I'll ask), never
# the document's completeness. The document is always the full, comprehensive
# one; depth only sizes the conversation. So no "three lines" / "flows drawn
# out" / section talk here — just how long the chat will be.
_DEPTH_PHRASE = {
    "lite": "a few quick questions (about thirty seconds)",
    "standard": "a few questions (a couple of minutes)",
    "deep": "a fuller set of questions (a longer conversation)",
}

_DEPTH_ALT = {
    "lite": "answer a few more questions",
    "standard": "fewer questions or a fuller conversation",
    "deep": "a shorter set of questions",
}


def proposal_sentence(decision: DepthDecision) -> str:
    """Render the founder-facing depth proposal — echo-before-act, invite override.

    Founder English only: no internal IDs, no signal-names, no jargon. Always
    ends with a question so the founder can confirm or override.
    """
    phrase = _DEPTH_PHRASE.get(decision.depth, _DEPTH_PHRASE["standard"])
    alt = _DEPTH_ALT.get(decision.depth, _DEPTH_ALT["standard"])
    return (
        f"{decision.reason} I'd do {phrase}. "
        f"Sound right, or would you rather {alt}?"
    )
