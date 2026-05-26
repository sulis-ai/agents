"""Rules-based candidate matching + scoring for the routing spine.

WP-006 / TDD §5 / ADR-002. Given a plain-language intent string, score it
against the route-set (the `InventoryEntry` list from WP-002, minus exclusions)
using keyword/phrase rules over four signal sources — the explicit invocation
token, authored trigger phrases (rubric + the orchestrator's `Route.triggers`),
the entry name tokens, and description-token overlap. Return ranked
`Candidate`s, each carrying the matched signals that produced its score.

This module is **pure, stdlib-only, no embeddings, no third-party deps**
(ADR-002): matching is deterministic keyword/phrase rules, never semantic
similarity. Identical input yields identical output (Armor §9) — required for a
matcher whose evidence feeds a CI-adjacent, reproducible pipeline. Ties break by
`name`, so ordering is stable.

It consumes WP-002's `InventoryEntry` / `Route` and WP-003's `RubricData`
verbatim; it reimplements neither. It is a candidate **ranker**, not a
classifier (TDD §5.4): the decision of "which one, or none" is the later B3
LLM layer's job. `match` always returns a list of scored candidates — never a
single "answer".
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from _route_inventory import InventoryEntry
from _route_rubric import RubricData

# Scoring weights — named constants, never magic numbers (TDD §5.2). Tuning a
# weight means changing the constant here, never sprinkling literals at the
# call sites (WP Notes).
W_INVOCATION = 100  # explicit "/sulis:specify" in the intent is near-certain
W_TRIGGER = 10  # per authored high-signal trigger phrase that hits
W_NAME = 3  # per entry-name token appearing in the intent
W_DESC_TOKEN = 1  # per shared token between intent and description

# A small, fixed stopword set (TDD §5.1) — explicit beats inferred; no NLTK,
# no external corpus. Module-level frozenset so it has exactly one definition.
STOPWORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "but",
        "by",
        "do",
        "for",
        "from",
        "i",
        "in",
        "into",
        "is",
        "it",
        "its",
        "me",
        "my",
        "of",
        "on",
        "or",
        "please",
        "should",
        "that",
        "the",
        "this",
        "to",
        "use",
        "want",
        "we",
        "what",
        "will",
        "with",
        "you",
        "your",
    }
)

# Punctuation → spaces: anything that is not a word character or whitespace.
_PUNCT = re.compile(r"[^\w\s]+")


@dataclass(frozen=True)
class Candidate:
    """One scored route-set entry with the evidence behind its score.

    `matched_signals` is the WHY (TDD §5.3): which trigger phrases hit, which
    tokens overlapped — the evidence the later B3 layer consumes.
    """

    entry: InventoryEntry
    score: int
    matched_signals: tuple[str, ...]


def normalise(text: str) -> list[str]:
    """Lowercase → strip punctuation to spaces → split → drop STOPWORDS.

    The single tokeniser (TDD §5.1) used by BOTH the description-overlap signal
    and the name-token signal — there is no second tokenising path. Returns a
    list of non-empty, non-stopword tokens.
    """
    lowered = text.lower()
    spaced = _PUNCT.sub(" ", lowered)
    return [tok for tok in spaced.split() if tok and tok not in STOPWORDS]


def _invocation_signal(
    intent_lower: str, entry: InventoryEntry
) -> tuple[int, list[str]]:
    """W_INVOCATION if the entry's invocation token appears verbatim."""
    if entry.invocation and entry.invocation.lower() in intent_lower:
        return W_INVOCATION, [f"invocation:{entry.invocation}"]
    return 0, []


def _trigger_phrases(entry: InventoryEntry, rubric: RubricData) -> tuple[str, ...]:
    """All authored trigger phrases for an entry: rubric keywords for its name
    ∪ the orchestrator-declared Route.triggers (TDD §5.2). Deduplicated,
    order-stable."""
    phrases: list[str] = list(rubric.trigger_keywords.get(entry.name, ()))
    for route in entry.routes:
        phrases.extend(route.triggers)
    # Preserve first-seen order while removing duplicates (determinism).
    seen: set[str] = set()
    unique: list[str] = []
    for phrase in phrases:
        if phrase and phrase not in seen:
            seen.add(phrase)
            unique.append(phrase)
    return tuple(unique)


def _trigger_signal(
    intent_lower: str, entry: InventoryEntry, rubric: RubricData
) -> tuple[int, list[str]]:
    """W_TRIGGER per authored trigger phrase that is a substring of the intent."""
    value = 0
    signals: list[str] = []
    for phrase in _trigger_phrases(entry, rubric):
        if phrase.lower() in intent_lower:
            value += W_TRIGGER
            signals.append(f"trigger:{phrase}")
    return value, signals


def _name_signal(
    intent_tokens: set[str], entry: InventoryEntry
) -> tuple[int, list[str]]:
    """W_NAME per entry-name token appearing in the intent tokens."""
    value = 0
    signals: list[str] = []
    for token in normalise(entry.name):
        if token in intent_tokens:
            value += W_NAME
            signals.append(f"name:{token}")
    return value, signals


def _description_signal(
    intent_tokens: set[str], entry: InventoryEntry
) -> tuple[int, list[str]]:
    """W_DESC_TOKEN per token shared between intent and description.

    Each shared token counts once (set intersection); ordering of the recorded
    signals is sorted for deterministic matched_signals output.
    """
    shared = sorted(intent_tokens.intersection(normalise(entry.description)))
    value = W_DESC_TOKEN * len(shared)
    signals = [f"desc:{token}" for token in shared]
    return value, signals


def score(
    intent: str, entry: InventoryEntry, rubric: RubricData
) -> tuple[int, tuple[str, ...]]:
    """Weighted sum of signal hits for one entry; returns (score, signals).

    score = W_INVOCATION·[invocation in intent]
          + W_TRIGGER·|trigger phrases hit|
          + W_NAME·|name tokens in intent|
          + W_DESC_TOKEN·|desc tokens ∩ intent tokens|

    Each branch is explicit per signal source (boring-code, WP Green): no
    clever one-liner folds the four sources into something less readable. The
    returned `signals` name exactly the hits that scored (TDD §5.3).
    """
    intent_lower = intent.lower()
    intent_tokens = set(normalise(intent))

    total = 0
    signals: list[str] = []

    for delta, sigs in (
        _invocation_signal(intent_lower, entry),
        _trigger_signal(intent_lower, entry, rubric),
        _name_signal(intent_tokens, entry),
        _description_signal(intent_tokens, entry),
    ):
        total += delta
        signals.extend(sigs)

    return total, tuple(signals)


def match(
    intent: str,
    route_set: list[InventoryEntry],
    rubric: RubricData,
    top_n: int = 5,
) -> list[Candidate]:
    """Rank the route-set by descending score; drop zero-score; return top_n.

    Ties break by `entry.name` ascending (stable, deterministic — Armor §9).
    Returns a list of candidates with their matched-signal evidence — never a
    single "answer" (TDD §5.4): this ranks and explains; B3 decides.
    """
    candidates: list[Candidate] = []
    for entry in route_set:
        value, signals = score(intent, entry, rubric)
        if value > 0:
            candidates.append(
                Candidate(entry=entry, score=value, matched_signals=signals)
            )

    # Descending score, then name ascending for stable tie-breaking. A single
    # sort key composes both: negate the score so higher scores sort first
    # while name stays ascending.
    candidates.sort(key=lambda c: (-c.score, c.entry.name))
    return candidates[:top_n]
