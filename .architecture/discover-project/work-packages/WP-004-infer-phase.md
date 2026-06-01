---
id: WP-004
title: Implement Infer phase — ConfigurationInferrer port + LLM and Null adapters + token budget
status: pending
kind: backend
primitive: create
group: GENERATE
change_id: CH-01KT1W
sequence_id: WP-004
dependsOn: [WP-001]
blocks: [WP-008]
estimated_token_cost:
  input: 4k
  output: 4k
tdd_section: Form §Ports & Adapters — Port 2 (ConfigurationInferrer); Armor §LLM provider; ADR-006
adrs: [ADR-006]
---

## Context

Implements the Infer phase per TDD §Form §Ports & Adapters. The
`ConfigurationInferrer` port abstracts the probabilistic-inference
seam. Two adapters satisfy it:

- `LLMConfigurationInferrer` — the production adapter. Calls the LLM
  with a strict prompt template; enforces the 10k token budget per
  ADR-006; raises `TokenBudgetExceeded` on exceedance.
- `NullConfigurationInferrer` — the graceful-degradation adapter
  (TDD §Armor §LLM provider, NFR-006). Returns an empty
  `InferenceResult` immediately. Selected when the LLM is unavailable
  OR when `TokenBudgetExceeded` is caught at the composition root.

Per the Ports-vs-Wrappers discriminator: both adapters are **Create**,
not Wrap — the port is domain-owned (the discovery domain defines what
"propose configuration values" means).

The Step `propose-configuration-values` (Step ULID
`01KT1WDSST05PROPOSECONFG`, per TDD §Canonical Identifiers) binds to
the `infer-configuration-values` Tool (Tool ULID
`01KT1WTL06INFERCONFIG0`, the only `kind: side-effect` Tool in this
change).

## Contract

### Files created

```
plugins/sulis/scripts/_discovery/
└── inferrer.py                     # ConfigurationInferrer port + LLMConfigurationInferrer + NullConfigurationInferrer + TokenBudgetExceeded
plugins/sulis/scripts/tests/unit/
└── test_discovery_inferrer.py      # contract + adapter tests (LLM mocked)
```

2 files.

### Port + adapters

```python
# plugins/sulis/scripts/_discovery/inferrer.py
from dataclasses import dataclass, field
from typing import Protocol

from _discovery.inspector import RepoRoot, Manifest, CiWorkflow, RepoContract


@dataclass(frozen=True)
class DetectionResult:
    repo_root: RepoRoot
    manifests: list[Manifest]
    ci_workflows: list[CiWorkflow]
    repo_contract: RepoContract | None


@dataclass(frozen=True)
class InferredValue:
    value: str
    confidence: float        # 0..1


@dataclass(frozen=True)
class InferenceResult:
    inferences: dict[str, InferredValue]  # keys are Configuration Vocabulary field names
    tokens_consumed: int                  # input + output combined


class TokenBudgetExceeded(Exception):
    """Raised when the LLM call exceeds the configured token budget.

    Carries the over-budget count so the composition root can log it
    (TDD §Armor §Observability) and the caller can decide whether to
    fall back to NullConfigurationInferrer.
    """
    def __init__(self, consumed: int, budget: int):
        self.consumed = consumed
        self.budget = budget
        super().__init__(f"Token budget exceeded: {consumed} > {budget}")


# canonical-source: TDD.md §Form §Ports & Adapters — Port 2 (ConfigurationInferrer)
class ConfigurationInferrer(Protocol):
    def infer(self, detected: DetectionResult, token_budget: int) -> InferenceResult: ...


class LLMConfigurationInferrer:
    """Production adapter. Calls the LLM with the prompt template at
    `plugins/sulis/scripts/_discovery/_prompts/infer.txt` (authored
    by this WP). Token-counted via the LLM provider's usage response;
    raises TokenBudgetExceeded on >= budget.
    """

    LLM_TIMEOUT_S = 90        # NFR-001 wall-time bound

    def __init__(self, llm_client):
        self._llm = llm_client

    def infer(self, detected: DetectionResult, token_budget: int) -> InferenceResult: ...


class NullConfigurationInferrer:
    """Graceful-degradation adapter (NFR-006). Used when the LLM is
    unavailable. Returns an empty InferenceResult; the Ask phase will
    fall back to all-human-ask.
    """
    def infer(self, detected: DetectionResult, token_budget: int) -> InferenceResult:
        return InferenceResult(inferences={}, tokens_consumed=0)
```

### Prompt template

A small text file at `plugins/sulis/scripts/_discovery/_prompts/infer.txt`
holds the LLM prompt template. Strict JSON-output instruction; placeholders
for the manifests + CI summary. Token count of the populated prompt
sets the input-side budget consumption.

## Definition of Done

### Red — Failing tests written

**Contract tests (any `ConfigurationInferrer` adapter must pass these):**

- [ ] `test_discovery_inferrer.py::test_contract_returns_InferenceResult` — given a `DetectionResult`, returns an `InferenceResult` (type signature stable)
- [ ] `test_discovery_inferrer.py::test_contract_inferences_keys_are_strings` — every key in `inferences` is a `str`
- [ ] `test_discovery_inferrer.py::test_contract_tokens_consumed_is_nonneg_int`

**Adapter-specific (`LLMConfigurationInferrer`):**

- [ ] `test_discovery_inferrer.py::test_llm_returns_inferences_with_confidence` — mock LLM returns valid JSON; adapter parses into `InferredValue(value=..., confidence=...)` per field
- [ ] `test_discovery_inferrer.py::test_llm_raises_TokenBudgetExceeded_at_boundary` — mock LLM reports `usage.total_tokens = 10001`, budget = 10000 → raises `TokenBudgetExceeded(consumed=10001, budget=10000)`
- [ ] `test_discovery_inferrer.py::test_llm_does_not_raise_at_exact_budget` — `usage.total_tokens = 10000`, budget = 10000 → returns normally (boundary is `>` not `>=`, or the boundary direction is documented in the test)
- [ ] `test_discovery_inferrer.py::test_llm_timeout_at_90s` — using a chaos shim that holds the LLM call open >90s, the adapter cancels or raises a timeout after 90s
- [ ] `test_discovery_inferrer.py::test_llm_malformed_json_response_raises_typed_error` — LLM returns non-JSON → typed `LLMResponseShapeError` (NOT a raw JSONDecodeError leaking up)
- [ ] `test_discovery_inferrer.py::test_llm_records_actual_tokens_consumed` — `InferenceResult.tokens_consumed` equals the mocked `usage.total_tokens`

**Adapter-specific (`NullConfigurationInferrer`):**

- [ ] `test_discovery_inferrer.py::test_null_returns_empty_inferences` — `InferenceResult.inferences == {}` and `tokens_consumed == 0`
- [ ] `test_discovery_inferrer.py::test_null_makes_no_llm_call` — pass a mock LLM client whose `.call` raises if invoked; `NullConfigurationInferrer.infer(...)` does not raise

**Protocol conformance:**

- [ ] `test_discovery_inferrer.py::test_both_adapters_satisfy_protocol` — `isinstance(LLMConfigurationInferrer(mock), ConfigurationInferrer)` and `isinstance(NullConfigurationInferrer(), ConfigurationInferrer)` via `runtime_checkable`

### Green — Implementation makes tests pass

- [ ] `plugins/sulis/scripts/_discovery/inferrer.py` authored per Contract
- [ ] `plugins/sulis/scripts/_discovery/_prompts/infer.txt` authored — JSON-output instruction + manifest/CI placeholders
- [ ] All 12 Red tests pass
- [ ] Coverage on `inferrer.py` ≥ 90%

### Blue — Refactor complete

- [ ] Token-counting logic is one helper (`_extract_tokens_consumed(response)`), not duplicated between input-side estimation and output-side enforcement
- [ ] Prompt-template loading is one helper that reads `_prompts/infer.txt` once at construction time (no re-read per call)
- [ ] `LLMResponseShapeError` extends a common `InferenceError` base so callers can catch the family
- [ ] Adapter docstrings cross-reference the canonical Step (`# canonical:step:propose-configuration-values`) for WP-009's parser

## Sequence

- **dependsOn:** WP-001 (the Tool ULID + schema for `infer-configuration-values` are authored there)
- **blocks:** WP-008 (skill prose imports `LLMConfigurationInferrer` + `NullConfigurationInferrer` for the Infer phase composition)
- **Parallelisable with:** WP-002, WP-003, WP-005, WP-006, WP-007, WP-009

## Estimated Token Cost

- **Input:** ~4k (TDD §Form §Ports + §Armor §LLM provider + ADR-006 + WP-001's `infer-configuration-values-*.schema.json`)
- **Output:** ~4k (`inferrer.py` ≈ 200 LOC + test file ≈ 200 LOC + prompt template ≈ 30 lines)
- **Total:** ~8k

## Performance

- LLM call MUST complete in ≤90 seconds (NFR-001 — Infer phase alone).
- Token budget enforced at 10,000 input+output per call (NFR-002 / ADR-006). Streaming token counts ARE permitted to fail-fast before the full response lands — the boundary check applies to the running total, not only the final `usage` value.
- Per ADR-006, the actual `tokens_consumed` is observable for v1.1 calibration — emitted on the structured stderr log per TDD §Armor §Observability.

## Notes

- The `NullConfigurationInferrer` is exercised in TWO scenarios: (a) LLM unreachable at boot (network/auth/rate-limit error); (b) `TokenBudgetExceeded` caught at the composition root mid-run. Both transition to all-human-ask. Test `test_null_makes_no_llm_call` covers (a); the swap-mid-run case is covered by WP-010's E2E `token-budget/` fixture.
- The 10k boundary is pinned in ADR-006 + NFR-002. v1.1 calibration may tighten or loosen; instrumentation in this WP makes the data observable.
- Prompt template lives next to the adapter (not in `_prompts/` at the package root) so the adapter+prompt are colocated for diff visibility.
