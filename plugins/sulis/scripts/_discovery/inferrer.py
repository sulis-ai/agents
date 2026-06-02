"""Infer phase — ``ConfigurationInferrer`` port + adapters.

Per TDD §Form §Ports & Adapters Port 2 + §Armor §External deps (LLM) +
ADR-006 (probabilistic-inference token budget).

Canonical Step ULID (TDD §Canonical Identifiers — Step 5):
    ``dna:step:01KT1WDSST05PR0P0SEC0NFG00``

Canonical Tool ULID (the only ``kind: side-effect`` Tool in this change):
    ``dna:tool:01KT1WT1061NFERC0NF1G00000``

Port + adapters
---------------

The discovery domain owns the ``ConfigurationInferrer`` Protocol. Two
adapters satisfy it:

- :class:`LLMConfigurationInferrer` — production adapter. Calls an LLM
  via the minimal :class:`LLMClient` Protocol; enforces the 10k token
  budget per ADR-006; raises :class:`TokenBudgetExceeded` when the
  budget is exceeded.

- :class:`NullConfigurationInferrer` — graceful-degradation adapter
  (NFR-006). Returns an empty :class:`InferenceResult` immediately. Used
  when the LLM is unavailable OR when :class:`TokenBudgetExceeded` is
  caught at the composition root. The skill then falls back to
  all-human-ask.

Per the Ports-vs-Wrappers discriminator: both adapters are **Create**,
not Wrap — the port is domain-owned (the discovery domain defines what
"propose configuration values" means).

Input-shape compatibility with WP-003
-------------------------------------

This module mirrors WP-003's ``inspector.py`` input dataclass shape so
WP-008 (skill prose composition) can wire them together without a
shim layer. Until WP-003's adapter ships, these dataclasses ARE the
contract; once WP-003 lands the composition root can adopt the
``inspector.py`` types directly (structurally identical, frozen
dataclasses with the same field names).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

# --------------------------------------------------------------------------
# Detection-result input shape (mirrors WP-003's `inspector.py` types)
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class RepoRoot:
    """The repository's root metadata. Mirrors WP-003 inspector.RepoRoot."""

    is_git: bool
    remote_url: str | None
    primary_branch: str | None
    has_remote: bool


@dataclass(frozen=True)
class Manifest:
    """A package manifest (e.g., package.json, pyproject.toml). Mirrors WP-003."""

    path: str
    language: str
    parsed: dict[str, Any]


@dataclass(frozen=True)
class CiWorkflow:
    """A CI workflow file. Mirrors WP-003."""

    path: str
    parsed: dict[str, Any]


@dataclass(frozen=True)
class RepoContract:
    """The ``.sulis/repo-contract.yml`` contents, if present. Mirrors WP-003."""

    parsed: dict[str, Any]


@dataclass(frozen=True)
class DetectionResult:
    """The aggregated output of the Detect phase, consumed by Infer."""

    repo_root: RepoRoot
    manifests: list[Manifest]
    ci_workflows: list[CiWorkflow]
    repo_contract: RepoContract | None


# --------------------------------------------------------------------------
# Inference-result output shape
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class InferredValue:
    """A single inferred Configuration Vocabulary field value + confidence.

    ``confidence`` is in ``[0.0, 1.0]``. The Ask phase uses this score to
    decide whether to surface the field for confirmation or override.
    """

    value: str
    confidence: float


@dataclass(frozen=True)
class InferenceResult:
    """The Infer phase's output.

    ``inferences`` is keyed by Configuration Vocabulary field name (a
    plain ``str``). ``tokens_consumed`` is the total LLM input+output
    token count for the call (or ``0`` for the Null adapter); the
    composition root logs this for NFR-002 observability.
    """

    inferences: dict[str, InferredValue] = field(default_factory=dict)
    tokens_consumed: int = 0


# --------------------------------------------------------------------------
# Errors
# --------------------------------------------------------------------------


class InferenceError(Exception):
    """Common base for Infer-phase errors so callers can catch the family."""


class TokenBudgetExceeded(InferenceError):
    """The LLM call exceeded the configured token budget (ADR-006).

    Carries the over-budget count so the composition root can log it
    (TDD §Armor §Observability) and the caller can decide whether to
    fall back to :class:`NullConfigurationInferrer`. Boundary is ``>``,
    not ``>=`` — equality with the cap is permitted (see ADR-006).
    """

    def __init__(self, consumed: int, budget: int) -> None:
        self.consumed = consumed
        self.budget = budget
        super().__init__(f"Token budget exceeded: {consumed} > {budget}")


class LLMResponseShapeError(InferenceError):
    """The LLM returned a response that did not parse as the expected JSON shape.

    Surfaces as a typed error rather than letting a raw
    :class:`json.JSONDecodeError` (or :class:`KeyError`) leak up to the
    composition root.
    """


# --------------------------------------------------------------------------
# Ports
# --------------------------------------------------------------------------


# canonical-source: TDD.md §Form §Ports & Adapters — Port 2 (ConfigurationInferrer)
@runtime_checkable
class ConfigurationInferrer(Protocol):
    """The Infer phase port — propose values for Configuration Vocabulary fields.

    Adapters MAY consult an LLM, look up static fixtures, or return
    nothing at all (the Null adapter). The port's only contract: given
    a :class:`DetectionResult`, return an :class:`InferenceResult`.
    """

    def infer(
        self, detected: DetectionResult, token_budget: int
    ) -> InferenceResult: ...


class LLMClient(Protocol):
    """Minimal LLM client surface the LLM adapter depends on.

    Kept deliberately small (one method) so callers can supply any
    provider's client by shimming to this Protocol. Returns an object
    with ``text`` (str) and ``usage.total_tokens`` (int).
    """

    def call(self, prompt: str, timeout_s: float) -> Any: ...


# --------------------------------------------------------------------------
# Prompt-template loading
# --------------------------------------------------------------------------


_PROMPT_TEMPLATE_PATH = Path(__file__).parent / "_prompts" / "infer.txt"


def _load_prompt_template() -> str:
    """Reads the Infer-phase prompt template from disk.

    Called once per adapter instance at construction time (see
    :class:`LLMConfigurationInferrer.__init__`); never re-read per call.
    """
    return _PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")


def _format_detected_for_prompt(detected: DetectionResult) -> str:
    """Renders a compact, deterministic summary of the Detect output for the LLM.

    Output is JSON-shaped so the LLM can ground its inferences in
    structured data rather than free text.
    """
    summary = {
        "repo_root": {
            "is_git": detected.repo_root.is_git,
            "remote_url": detected.repo_root.remote_url,
            "primary_branch": detected.repo_root.primary_branch,
            "has_remote": detected.repo_root.has_remote,
        },
        "manifests": [
            {"path": m.path, "language": m.language, "parsed": m.parsed}
            for m in detected.manifests
        ],
        "ci_workflows": [
            {"path": w.path, "parsed": w.parsed} for w in detected.ci_workflows
        ],
        "repo_contract": (
            detected.repo_contract.parsed
            if detected.repo_contract is not None
            else None
        ),
    }
    return json.dumps(summary, indent=2, sort_keys=True)


# --------------------------------------------------------------------------
# Token accounting
# --------------------------------------------------------------------------


def _extract_tokens_consumed(response: Any) -> int:
    """Reads ``response.usage.total_tokens`` defensively.

    Single helper so the boundary check in
    :meth:`LLMConfigurationInferrer.infer` and any future
    streaming-token check use the same extraction logic — no duplication
    between input-side estimation and output-side enforcement.
    """
    try:
        return int(response.usage.total_tokens)
    except (AttributeError, TypeError, ValueError) as exc:
        raise LLMResponseShapeError(
            f"LLM response missing or malformed usage.total_tokens: {exc!r}"
        ) from exc


# --------------------------------------------------------------------------
# LLM adapter
# --------------------------------------------------------------------------


class LLMConfigurationInferrer:
    """Production adapter — calls the LLM with a strict prompt template.

    Token-counted via the LLM provider's ``usage.total_tokens`` response
    field. Raises :class:`TokenBudgetExceeded` when consumed > budget
    (strict ``>``; equality permitted per ADR-006). Raises
    :class:`LLMResponseShapeError` when the response doesn't parse as
    JSON of the expected shape.

    The 90-second wall-time bound (NFR-001) is passed to the
    :class:`LLMClient` as ``timeout_s``; the client owns the actual
    cancellation mechanism.

    # canonical:step:propose-configuration-values
    """

    LLM_TIMEOUT_S = 90  # NFR-001 wall-time bound

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm = llm_client
        self._prompt_template = _load_prompt_template()

    def infer(self, detected: DetectionResult, token_budget: int) -> InferenceResult:
        prompt = self._prompt_template.replace(
            "{{detected_summary}}", _format_detected_for_prompt(detected)
        )
        response = self._llm.call(prompt, timeout_s=self.LLM_TIMEOUT_S)

        consumed = _extract_tokens_consumed(response)
        if consumed > token_budget:
            raise TokenBudgetExceeded(consumed=consumed, budget=token_budget)

        inferences = _parse_llm_inferences(response.text)
        return InferenceResult(inferences=inferences, tokens_consumed=consumed)


def _parse_llm_inferences(response_text: str) -> dict[str, InferredValue]:
    """Parses the LLM's JSON output into ``dict[str, InferredValue]``.

    Expected shape::

        {"field_name": {"value": "...", "confidence": 0.0..1.0}, ...}

    Any deviation raises :class:`LLMResponseShapeError` — never lets a
    raw :class:`json.JSONDecodeError` or :class:`KeyError` leak.
    """
    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise LLMResponseShapeError(
            f"LLM response is not valid JSON: {exc.msg}"
        ) from exc

    if not isinstance(payload, dict):
        raise LLMResponseShapeError(
            f"LLM response JSON must be an object, got {type(payload).__name__}"
        )

    inferences: dict[str, InferredValue] = {}
    # JSON object keys are always strings per RFC 8259, so the iterator
    # yields str keys unconditionally — no key-type guard needed here.
    for key, raw_value in payload.items():
        if not isinstance(raw_value, dict):
            raise LLMResponseShapeError(
                f"LLM response value for {key!r} is not an object"
            )
        try:
            value = raw_value["value"]
            confidence = float(raw_value["confidence"])
        except (KeyError, TypeError, ValueError) as exc:
            raise LLMResponseShapeError(
                f"LLM response field {key!r} missing value/confidence: {exc!r}"
            ) from exc
        if not isinstance(value, str):
            raise LLMResponseShapeError(
                f"LLM response field {key!r} value is not a string"
            )
        inferences[key] = InferredValue(value=value, confidence=confidence)
    return inferences


# --------------------------------------------------------------------------
# Null adapter
# --------------------------------------------------------------------------


class NullConfigurationInferrer:
    """Graceful-degradation adapter (NFR-006).

    Returns an empty :class:`InferenceResult` immediately — no LLM call,
    no token consumption. Used when the LLM is unavailable at boot
    (network/auth/rate-limit error) or when :class:`TokenBudgetExceeded`
    is caught at the composition root mid-run. The skill then falls
    back to all-human-ask.

    # canonical:step:propose-configuration-values
    """

    def infer(self, detected: DetectionResult, token_budget: int) -> InferenceResult:
        del detected, token_budget  # explicit no-op
        return InferenceResult(inferences={}, tokens_consumed=0)
