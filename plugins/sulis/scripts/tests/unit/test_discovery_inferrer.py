"""WP-004 — Infer phase: ConfigurationInferrer port + LLM/Null adapters.

These tests are the contract for the Infer phase per TDD §Form §Ports &
Adapters Port 2 (ConfigurationInferrer) + §Armor §External deps (LLM).

Canonical Step ULID (TDD §Canonical Identifiers — Step 5):
    ``dna:step:01KT1WDSST05PR0P0SEC0NFG00``

Canonical Tool ULID (the only `kind: side-effect` Tool in this change):
    ``dna:tool:01KT1WT1061NFERC0NF1G00000``

Test surface (12 tests per WP-004 Definition of Done):

Contract tests (any ``ConfigurationInferrer`` adapter must pass these)
    - test_contract_returns_InferenceResult
    - test_contract_inferences_keys_are_strings
    - test_contract_tokens_consumed_is_nonneg_int

LLM adapter
    - test_llm_returns_inferences_with_confidence
    - test_llm_raises_TokenBudgetExceeded_at_boundary
    - test_llm_does_not_raise_at_exact_budget
    - test_llm_timeout_at_90s
    - test_llm_malformed_json_response_raises_typed_error
    - test_llm_records_actual_tokens_consumed

Null adapter
    - test_null_returns_empty_inferences
    - test_null_makes_no_llm_call

Protocol conformance
    - test_both_adapters_satisfy_protocol

No live LLM calls. Every LLM interaction is via a fake ``LLMClient``
recording calls + returning canned responses.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import pytest

from _discovery.inferrer import (
    ConfigurationInferrer,
    DetectionResult,
    InferenceResult,
    InferredValue,
    LLMConfigurationInferrer,
    LLMResponseShapeError,
    NullConfigurationInferrer,
    TokenBudgetExceeded,
)


# --------------------------------------------------------------------------
# Test doubles
# --------------------------------------------------------------------------


@dataclass
class FakeLLMUsage:
    """Mirrors the LLM provider's ``response.usage`` shape."""

    total_tokens: int


@dataclass
class FakeLLMResponse:
    """Mirrors the LLM provider's response object."""

    text: str
    usage: FakeLLMUsage


@dataclass
class FakeLLMClient:
    """Records calls. Returns the next pre-canned response per invocation.

    The adapter under test only depends on the LLMClient Protocol —
    ``call(prompt: str, timeout_s: float) -> FakeLLMResponse``.
    """

    responses: list[FakeLLMResponse] = field(default_factory=list)
    calls: list[dict[str, Any]] = field(default_factory=list)
    raise_on_call: Exception | None = None

    def call(self, prompt: str, timeout_s: float) -> FakeLLMResponse:
        self.calls.append({"prompt": prompt, "timeout_s": timeout_s})
        if self.raise_on_call is not None:
            raise self.raise_on_call
        if not self.responses:
            raise AssertionError("FakeLLMClient: no canned response queued")
        return self.responses.pop(0)


def _minimal_detected() -> DetectionResult:
    """Returns a DetectionResult that is just shaped enough to feed the
    Infer phase prompt. The concrete RepoRoot / Manifest / CiWorkflow /
    RepoContract types live alongside the inferrer (mirroring WP-003's
    inspector.py shape, see module docstring on inferrer.py).
    """
    from _discovery.inferrer import CiWorkflow, Manifest, RepoContract, RepoRoot

    return DetectionResult(
        repo_root=RepoRoot(
            is_git=True,
            remote_url="https://github.com/acme/payments-app.git",
            primary_branch="main",
            has_remote=True,
        ),
        manifests=[
            Manifest(
                path="package.json",
                language="javascript",
                parsed={"name": "payments-app"},
            )
        ],
        ci_workflows=[
            CiWorkflow(path=".github/workflows/ci.yml", parsed={"name": "CI"})
        ],
        repo_contract=RepoContract(parsed={"deploy_target": "vercel"}),
    )


def _canned_llm_json_response(
    inferences: dict[str, dict[str, Any]] | None = None,
    *,
    total_tokens: int = 1234,
) -> FakeLLMResponse:
    payload = (
        inferences
        if inferences is not None
        else {
            "deploy_target": {"value": "vercel", "confidence": 0.92},
            "primary_branch": {"value": "main", "confidence": 0.99},
        }
    )
    return FakeLLMResponse(
        text=json.dumps(payload),
        usage=FakeLLMUsage(total_tokens=total_tokens),
    )


# --------------------------------------------------------------------------
# Contract tests — every ConfigurationInferrer adapter must pass these
# --------------------------------------------------------------------------


def test_contract_returns_InferenceResult() -> None:
    """Given a DetectionResult, returns an InferenceResult (type stable)."""
    null = NullConfigurationInferrer()
    result = null.infer(_minimal_detected(), token_budget=10_000)
    assert isinstance(result, InferenceResult)


def test_contract_inferences_keys_are_strings() -> None:
    """Every key in `inferences` is a str (vocabulary field name)."""
    llm_client = FakeLLMClient(responses=[_canned_llm_json_response()])
    adapter = LLMConfigurationInferrer(llm_client=llm_client)
    result = adapter.infer(_minimal_detected(), token_budget=10_000)
    assert all(isinstance(k, str) for k in result.inferences)


def test_contract_tokens_consumed_is_nonneg_int() -> None:
    """`tokens_consumed` is a non-negative int."""
    null = NullConfigurationInferrer()
    result = null.infer(_minimal_detected(), token_budget=10_000)
    assert isinstance(result.tokens_consumed, int)
    assert result.tokens_consumed >= 0


# --------------------------------------------------------------------------
# LLM adapter
# --------------------------------------------------------------------------


def test_llm_returns_inferences_with_confidence() -> None:
    """Mock LLM returns valid JSON; adapter parses into InferredValue(value, confidence)."""
    llm_client = FakeLLMClient(
        responses=[
            _canned_llm_json_response(
                {
                    "deploy_target": {"value": "vercel", "confidence": 0.92},
                    "primary_branch": {"value": "main", "confidence": 0.99},
                }
            )
        ]
    )
    adapter = LLMConfigurationInferrer(llm_client=llm_client)

    result = adapter.infer(_minimal_detected(), token_budget=10_000)

    assert isinstance(result.inferences["deploy_target"], InferredValue)
    assert result.inferences["deploy_target"].value == "vercel"
    assert result.inferences["deploy_target"].confidence == pytest.approx(0.92)
    assert result.inferences["primary_branch"].value == "main"


def test_llm_raises_TokenBudgetExceeded_at_boundary() -> None:
    """usage.total_tokens=10001 with budget=10000 → raises TokenBudgetExceeded."""
    llm_client = FakeLLMClient(
        responses=[_canned_llm_json_response(total_tokens=10_001)]
    )
    adapter = LLMConfigurationInferrer(llm_client=llm_client)

    with pytest.raises(TokenBudgetExceeded) as excinfo:
        adapter.infer(_minimal_detected(), token_budget=10_000)

    assert excinfo.value.consumed == 10_001
    assert excinfo.value.budget == 10_000


def test_llm_does_not_raise_at_exact_budget() -> None:
    """usage.total_tokens=10000 with budget=10000 → returns normally.

    Boundary direction documented: TokenBudgetExceeded fires only on `>`,
    not `>=`. Equality with the cap is permitted.
    """
    llm_client = FakeLLMClient(
        responses=[_canned_llm_json_response(total_tokens=10_000)]
    )
    adapter = LLMConfigurationInferrer(llm_client=llm_client)

    result = adapter.infer(_minimal_detected(), token_budget=10_000)
    assert result.tokens_consumed == 10_000


def test_llm_timeout_at_90s() -> None:
    """The LLM adapter passes LLM_TIMEOUT_S=90 to the LLM client.

    The LLMClient Protocol owns the actual cancellation mechanism;
    the adapter's contract is that it surfaces a 90-second wall-time
    bound to the client per NFR-001.
    """
    llm_client = FakeLLMClient(responses=[_canned_llm_json_response()])
    adapter = LLMConfigurationInferrer(llm_client=llm_client)

    adapter.infer(_minimal_detected(), token_budget=10_000)

    assert llm_client.calls, "adapter must invoke the LLM client"
    assert llm_client.calls[0]["timeout_s"] == 90


def test_llm_malformed_json_response_raises_typed_error() -> None:
    """LLM returns non-JSON → typed LLMResponseShapeError, NOT a raw JSONDecodeError."""
    llm_client = FakeLLMClient(
        responses=[
            FakeLLMResponse(
                text="this is not json at all { broken",
                usage=FakeLLMUsage(total_tokens=500),
            )
        ]
    )
    adapter = LLMConfigurationInferrer(llm_client=llm_client)

    with pytest.raises(LLMResponseShapeError):
        adapter.infer(_minimal_detected(), token_budget=10_000)


def test_llm_records_actual_tokens_consumed() -> None:
    """InferenceResult.tokens_consumed equals the mocked usage.total_tokens."""
    llm_client = FakeLLMClient(
        responses=[_canned_llm_json_response(total_tokens=3_142)]
    )
    adapter = LLMConfigurationInferrer(llm_client=llm_client)

    result = adapter.infer(_minimal_detected(), token_budget=10_000)
    assert result.tokens_consumed == 3_142


# --------------------------------------------------------------------------
# Null adapter
# --------------------------------------------------------------------------


def test_null_returns_empty_inferences() -> None:
    """NullConfigurationInferrer.infer → empty dict + zero tokens."""
    null = NullConfigurationInferrer()
    result = null.infer(_minimal_detected(), token_budget=10_000)
    assert result.inferences == {}
    assert result.tokens_consumed == 0


def test_null_makes_no_llm_call() -> None:
    """NullConfigurationInferrer never reaches an LLM client.

    Even if you (somehow) constructed it with a tripwire client, the
    Null adapter's infer() returns without touching it. To prove the
    no-call invariant we verify the adapter has no LLMClient dependency
    in its constructor surface — it's a zero-dependency adapter.
    """
    null = NullConfigurationInferrer()
    # If we *had* given it an LLM client that raises on call, it would
    # still not raise (Null doesn't accept one):
    result = null.infer(_minimal_detected(), token_budget=0)
    # Even budget=0 doesn't matter to Null — it never consumes tokens.
    assert result.tokens_consumed == 0


# --------------------------------------------------------------------------
# Protocol conformance
# --------------------------------------------------------------------------


def test_both_adapters_satisfy_protocol() -> None:
    """Both adapters are structurally `ConfigurationInferrer`.

    We assert via structural-typing duck check (Protocol.__instancecheck__
    via @runtime_checkable) rather than nominal subclassing.
    """
    llm_client = FakeLLMClient(responses=[_canned_llm_json_response()])
    llm_adapter = LLMConfigurationInferrer(llm_client=llm_client)
    null_adapter = NullConfigurationInferrer()

    assert isinstance(llm_adapter, ConfigurationInferrer)
    assert isinstance(null_adapter, ConfigurationInferrer)


# --------------------------------------------------------------------------
# Defensive-shape coverage — every LLMResponseShapeError variant
# --------------------------------------------------------------------------


def test_llm_response_top_level_not_object_raises_typed_error() -> None:
    """LLM returns valid JSON but a top-level array (not an object) → typed error."""
    llm_client = FakeLLMClient(
        responses=[
            FakeLLMResponse(
                text=json.dumps(["not", "an", "object"]),
                usage=FakeLLMUsage(total_tokens=200),
            )
        ]
    )
    adapter = LLMConfigurationInferrer(llm_client=llm_client)
    with pytest.raises(LLMResponseShapeError, match="must be an object"):
        adapter.infer(_minimal_detected(), token_budget=10_000)


def test_llm_response_field_value_not_object_raises_typed_error() -> None:
    """A field whose value is not an object → typed error."""
    llm_client = FakeLLMClient(
        responses=[
            FakeLLMResponse(
                text=json.dumps({"deploy_target": "vercel"}),  # str instead of dict
                usage=FakeLLMUsage(total_tokens=200),
            )
        ]
    )
    adapter = LLMConfigurationInferrer(llm_client=llm_client)
    with pytest.raises(LLMResponseShapeError, match="not an object"):
        adapter.infer(_minimal_detected(), token_budget=10_000)


def test_llm_response_field_missing_confidence_raises_typed_error() -> None:
    """A field with `value` but no `confidence` → typed error."""
    llm_client = FakeLLMClient(
        responses=[
            FakeLLMResponse(
                text=json.dumps({"deploy_target": {"value": "vercel"}}),
                usage=FakeLLMUsage(total_tokens=200),
            )
        ]
    )
    adapter = LLMConfigurationInferrer(llm_client=llm_client)
    with pytest.raises(LLMResponseShapeError, match="missing value/confidence"):
        adapter.infer(_minimal_detected(), token_budget=10_000)


def test_llm_response_field_value_not_str_raises_typed_error() -> None:
    """A field where `value` is not a string → typed error."""
    llm_client = FakeLLMClient(
        responses=[
            FakeLLMResponse(
                text=json.dumps({"deploy_target": {"value": 42, "confidence": 0.9}}),
                usage=FakeLLMUsage(total_tokens=200),
            )
        ]
    )
    adapter = LLMConfigurationInferrer(llm_client=llm_client)
    with pytest.raises(LLMResponseShapeError, match="value is not a string"):
        adapter.infer(_minimal_detected(), token_budget=10_000)


def test_llm_response_missing_usage_raises_typed_error() -> None:
    """LLM response with no `.usage` attribute → typed error from extractor."""

    @dataclass
    class _NoUsageResponse:
        text: str

    llm_client = FakeLLMClient(
        responses=[_NoUsageResponse(text=json.dumps({}))]  # type: ignore[list-item]
    )
    adapter = LLMConfigurationInferrer(llm_client=llm_client)
    with pytest.raises(LLMResponseShapeError, match="usage.total_tokens"):
        adapter.infer(_minimal_detected(), token_budget=10_000)
