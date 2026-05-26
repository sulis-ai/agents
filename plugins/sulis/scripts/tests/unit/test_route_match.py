"""Unit tests for _route_match — rules-based candidate matching + scoring.

Test-first (RGB / Non-Negotiable #1): every behaviour below is written to fail
before _route_match.py exists.

WP-006 / TDD §5 / ADR-002. The matcher consumes WP-002's value objects
(`InventoryEntry`, `Route`) and WP-003's `RubricData` (trigger keywords) — it
reimplements neither. It scores a plain-language intent against the route-set
using keyword/phrase rules over invocation, trigger phrases, name tokens, and
description-token overlap, returning ranked `Candidate`s with the matched
signals that produced each score. It is a candidate *ranker*, not a classifier
(TDD §5.4) — the decision is the later B3 layer's job.

The route-set here is built directly from `InventoryEntry` instances (the pure
domain type from WP-002) so the scoring weights can be exercised precisely; the
fixture skills/agents tree (`_route_fixtures`) feeds the discovery seam, which
WP-002 already proves. Matching is pure rules over the in-memory objects.
"""

from _route_inventory import InventoryEntry, Route
from _route_rubric import RubricData

from _route_match import (
    W_INVOCATION,
    W_TRIGGER,
    Candidate,
    match,
    normalise,
    score,
)


# --- helpers ---------------------------------------------------------------


def _entry(name, *, description, kind="skill", routes=()):
    """Build an InventoryEntry with the invocation derived per convention."""
    invocation = f"/sulis:{name}" if kind == "skill" else name
    return InventoryEntry(
        name=name,
        kind=kind,
        invocation=invocation,
        description=description,
        source_path=f"plugins/sulis/skills/{name}/SKILL.md",
        routes=routes,
    )


def _route_set():
    """A small, hand-built route-set covering the scoring signal sources.

    - specify: description rich in requirements/spec vocabulary.
    - design: description rich in architecture/blueprint vocabulary.
    - check-security: thin description; relies on rubric trigger keywords.
    """
    return [
        _entry(
            "specify",
            description=(
                "Write down what a piece of work should do. Produces a "
                "requirements document with flows for a new feature."
            ),
        ),
        _entry(
            "design",
            description=(
                "Turn requirements into a technical blueprint with the "
                "architecture decisions behind it."
            ),
        ),
        _entry(
            "check-security",
            description="Audit the code.",
        ),
    ]


def _rubric(trigger_keywords=None):
    return RubricData(
        exclusions=frozenset(),
        trigger_keywords=trigger_keywords or {},
    )


# --- normalise floor test --------------------------------------------------


def test_normalise_drops_stopwords_and_punctuation():
    """normalise lowercases, strips punctuation to spaces, splits, drops
    stopwords. The floor test for the single shared tokeniser (TDD §5.1)."""
    tokens = normalise("Write DOWN the Requirements, audit-code!")
    # lowercased
    assert all(t == t.lower() for t in tokens)
    # punctuation stripped to spaces: "Requirements," → "requirements" (no
    # trailing comma), "audit-code!" → "audit" + "code" (hyphen/bang stripped).
    assert "requirements" in tokens
    assert "audit" in tokens
    assert "code" in tokens
    assert "requirements," not in tokens
    # stopword "the" dropped
    assert "the" not in tokens
    # no empty tokens from collapsed punctuation
    assert "" not in tokens


# --- R7: invocation dominates ----------------------------------------------


def test_match_ranks_invocation_first():
    """An intent containing the verbatim invocation `/sulis:specify` ranks the
    `specify` entry top — W_INVOCATION dominates every other signal (R7)."""
    routes = _route_set()
    # The intent mentions architecture/blueprint vocabulary (favouring design
    # on description overlap) BUT contains the explicit /sulis:specify token.
    intent = "use /sulis:specify for this technical blueprint architecture work"
    candidates = match(intent, routes, _rubric())

    assert candidates, "expected at least one candidate"
    assert candidates[0].entry.name == "specify"
    # The top score must reflect the invocation weight.
    assert candidates[0].score >= W_INVOCATION


# --- R8: description-token fallback ----------------------------------------


def test_match_uses_description_tokens():
    """A plain-language intent with NO trigger keyword and NO invocation still
    returns the right route via description-token overlap (the A4 fallback
    signal, R8)."""
    routes = _route_set()
    # "requirements document feature" overlaps the specify description tokens;
    # no invocation token, no rubric triggers configured.
    intent = "I want to write a requirements document for a new feature"
    candidates = match(intent, routes, _rubric())

    assert candidates, "expected at least one candidate"
    assert candidates[0].entry.name == "specify"
    # Pure description-overlap score: below the invocation floor, above zero.
    assert 0 < candidates[0].score < W_INVOCATION


# --- R9: trigger keywords boost --------------------------------------------


def test_match_trigger_keywords_boost():
    """A rubric trigger keyword lifts the right route above a description-only
    competitor (R9). check-security has a thin description but a rubric trigger
    phrase that matches the intent; it must outrank a route that only shares a
    description token."""
    routes = _route_set()
    rubric = _rubric(
        trigger_keywords={
            "check-security": ("secrets", "vulnerability", "leak", "exposed"),
        }
    )
    # The intent mentions "secrets" (a check-security trigger) plus a generic
    # word "code" that overlaps check-security's thin description. Without the
    # trigger boost, check-security would score only on description overlap.
    intent = "audit the code for exposed secrets"
    candidates = match(intent, routes, rubric)

    assert candidates, "expected at least one candidate"
    assert candidates[0].entry.name == "check-security"
    # A trigger hit contributes at least W_TRIGGER, far above a 1-token desc
    # overlap.
    assert candidates[0].score >= W_TRIGGER


def test_match_trigger_includes_route_triggers():
    """Trigger phrases come from BOTH rubric.trigger_keywords AND the
    orchestrator's declared Route.triggers (TDD §5.2). A Route.triggers phrase
    that is a substring of the intent scores W_TRIGGER."""
    cartographer = _entry(
        "context-cartographer",
        kind="agent",
        description="Discover existing context.",
        routes=(
            Route(
                slug="context-cartographer",
                description="Discover existing context, conventions, prior art",
                triggers=("scan the codebase", "what already exists"),
            ),
        ),
    )
    routes = [cartographer, *_route_set()]
    intent = "please scan the codebase before we start"
    candidates = match(intent, routes, _rubric())

    assert candidates[0].entry.name == "context-cartographer"
    assert candidates[0].score >= W_TRIGGER


# --- matched_signals records the WHY ---------------------------------------


def test_match_returns_matched_signals():
    """Each Candidate.matched_signals is non-empty and names the actual signals
    that scored — the evidence the later B3 layer consumes (TDD §5.3)."""
    routes = _route_set()
    rubric = _rubric(
        trigger_keywords={"check-security": ("secrets",)},
    )
    intent = "audit the code for secrets"
    candidates = match(intent, routes, rubric)

    assert candidates
    for cand in candidates:
        assert isinstance(cand, Candidate)
        assert cand.matched_signals, f"{cand.entry.name} has empty matched_signals"
        assert isinstance(cand.matched_signals, tuple)
    # The top candidate's signals should reference the trigger that fired.
    top = candidates[0]
    assert top.entry.name == "check-security"
    assert any("secrets" in sig for sig in top.matched_signals)


# --- zero-score dropped, top_n capped --------------------------------------


def test_match_drops_zero_score_and_caps_top_n():
    """Entries scoring 0 are excluded; result length <= top_n."""
    routes = _route_set()
    # An intent that overlaps ONLY the specify description; design and
    # check-security share no tokens/triggers/invocation → score 0 → dropped.
    intent = "requirements"
    candidates = match(intent, routes, _rubric())

    names = [c.entry.name for c in candidates]
    assert "specify" in names
    # design + check-security score zero on the word "requirements".
    assert all(c.score > 0 for c in candidates)

    # top_n cap: ask for at most 2 from a route-set whose entries all score.
    rich_intent = "requirements blueprint audit code feature architecture"
    capped = match(rich_intent, routes, _rubric(), top_n=2)
    assert len(capped) <= 2


# --- tie-break by name, deterministic --------------------------------------


def test_match_tie_break_is_name_stable():
    """Two equal-score candidates order by `name`; repeated calls return
    identical order (determinism — Armor §9)."""
    # Two entries with identical single-token descriptions → identical scores
    # for an intent that hits exactly that token.
    zebra = _entry("zebra", description="shared")
    alpha = _entry("alpha", description="shared")
    routes = [zebra, alpha]  # deliberately not name-sorted in input
    intent = "shared"

    candidates = match(intent, routes, _rubric())
    names = [c.entry.name for c in candidates]
    assert names == ["alpha", "zebra"], "ties must order by name ascending"

    # Determinism: repeated calls identical.
    again = [c.entry.name for c in match(intent, routes, _rubric())]
    assert again == names


# --- score() unit: weighted sum --------------------------------------------


def test_score_is_weighted_sum_of_signal_sources():
    """score() returns (int, matched_signals); the int is the weighted sum of
    invocation + trigger + name-token + description-token hits (TDD §5.2)."""
    entry = _entry(
        "specify",
        description="requirements document feature",
    )
    rubric = _rubric(trigger_keywords={"specify": ("write it down",)})
    # Intent hits: invocation (/sulis:specify), trigger ("write it down"),
    # name token ("specify"), and description tokens (requirements, document).
    intent = "write it down with /sulis:specify the requirements document"
    value, signals = score(intent, entry, rubric)

    assert isinstance(value, int)
    assert isinstance(signals, tuple)
    # Must include at least the invocation weight.
    assert value >= W_INVOCATION + W_TRIGGER
    assert signals
