# Why `outcome: blocker` is NOT an exception

**Applies to:** sulis-execution v0.1.0

## The contract

When `client.pipeline.run(...)` or `client.train.run(...)` reports
`outcome: blocker`, the SDK returns a typed result — it does NOT raise
an exception.

This is one of the load-bearing design decisions in the SDK. It looks
like a small thing; it has real consequences for how calling code is
structured.

## Why

Consider two failures with very different shapes:

**Failure A:** the SDK tried to spawn `wpx-pipeline`, but the binary
isn't on PATH. The SDK can't run your pipeline; can't return a
meaningful result; can't tell you anything about what would have
happened. **This is an exception** — `BinaryNotFoundError`. There's
no useful return value.

**Failure B:** the SDK spawned `wpx-pipeline` successfully. The
pipeline ran through CI polling, deploy, health checks, smoke tests.
At some step, something failed (CI was red, or the deploy timed out,
or the smoke command returned non-zero). The pipeline finished cleanly
and emits a structured JSON envelope describing exactly what happened.
**This is a successful operation that produced a "bad news" result.**

If we treat both as exceptions, calling code can't distinguish
"infrastructure broke" from "the work I asked you to do reported a
deterministic problem." The recovery is different:

- A → fix setup; retry once the binary is found
- B → write a BLOCKER record; investigate the cause; possibly resolve
  manually; don't retry blindly with the same inputs

Treating B as an exception loses the structured information about what
the pipeline *did* — the CI verdict, the deploy URL (if any), the
specific blocker reason — by collapsing it into a string message.

## The shape in code

```python
result = client.pipeline.run(...)

# A normal result with rich detail
assert result.outcome in {"success", "blocker", "error", "pending"}

if result.outcome == "blocker":
    # All the pipeline's per-step verdicts are still accessible
    print(f"CI poll skipped: {result.ci_poll_skipped}")
    print(f"Merge already complete: {result.merge_already_complete}")
    print(f"Health: {result.health_status}")
    print(f"Smoke: {result.smoke_verdict}")
    print(f"Blocker reason: {result.blocker_reason}")
    # Decide what to do based on the full context
```

Compare what we'd lose if blocker were raised:

```python
# DON'T do this
try:
    result = client.pipeline.run(...)
except BlockerError as e:
    print(e.message)  # ONE STRING. No structured detail.
```

## What about `train.run` outcomes?

Same pattern. `train.run` can return:

- `outcome: success` — train shipped the batch
- `outcome: not_triggered` — eligibility check decided no train
  should fire yet (e.g., only 1 WP eligible, no --force)
- `outcome: nothing_to_pack` — no eligible WPs
- `outcome: blocker` — train started but a deterministic step failed
  (CI red, deploy timed out)
- `outcome: error` — internal logic error (rare; bug)

All five are returned as normal results. The caller inspects `outcome`
to decide what to do.

## Exceptions are reserved for…

| Exception | When |
|---|---|
| `ProtocolError` (and subclasses) | The SDK couldn't spawn the CLI at all |
| `ExpectedError` (and subclasses) | The CLI rejected your inputs before doing the work |
| `InternalError` (and subclasses) | The CLI crashed during the work; emitted a traceback on stderr |

If you can imagine the operation returning a meaningful result with the
information you got back, it's a result. If the operation couldn't
return anything, it's an exception.

## See also

- [Error categories](error-categories.md)
- [Mental model](mental-model.md)
- [How to handle errors](../how-to/handle-errors.md)
