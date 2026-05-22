# sulis-execution SDK examples

**Applies to:** sulis-execution SDK v0.2.0+

Runnable Python scripts that drive the sulis-execution surface
end-to-end. Use these when you want to orchestrate executors / trains
/ changes from outside Claude Code — e.g., from a CI pipeline, a
notebook, or a cron job.

## Prerequisites

1. Python 3.10+
2. The Python SDK installed:

   ```bash
   pip install -e /path/to/agents/plugins/sulis-execution/sdk/python/
   ```

3. The underlying wpx-* CLI binaries available — either on `PATH` or
   pointed at via `WPX_DIR`:

   ```bash
   export WPX_DIR=/path/to/agents/plugins/sulis-execution/scripts
   ```

4. A real project with `.architecture/<project>/` populated.

Verify setup:

```bash
python -c "import sulis_execution; print(sulis_execution.__version__)"  # 0.2.0
```

## Examples

| Script | What it demonstrates |
|---|---|
| [`run-train-after-executors.py`](run-train-after-executors.py) | Discover ready WPs → poll eligibility → fire the train → flip merged WPs to done. Handles all three outcome paths (success / not_triggered / blocker). Mirrors the recipe at [`docs/recipes/run-train-after-executors.md`](../docs/recipes/run-train-after-executors.md). |
| [`ship-change-end-to-end.py`](ship-change-end-to-end.py) | Start a change → status check → finish --merge → cleanup. Handles `ExpectedError` on `branch_already_exists`. Mirrors the recipe at [`docs/recipes/ship-change-end-to-end.md`](../docs/recipes/ship-change-end-to-end.md). |

## Running

Each script has `--help`:

```bash
python sdk/examples/run-train-after-executors.py --help
python sdk/examples/ship-change-end-to-end.py --help
```

Sample invocations:

```bash
# Poll for ready WPs in `my-project`, fire the train when ≥3 are ready
python sdk/examples/run-train-after-executors.py \
  --project my-project \
  --repo my-org/my-repo \
  --deploy-workflow "Deploy to Dev" \
  --staging-url https://staging.example.com \
  --smoke-cmd "curl -sf https://staging.example.com/health" \
  --poll-interval 30 \
  --max-wait 600

# Start + ship a change end-to-end
python sdk/examples/ship-change-end-to-end.py \
  --slug introduce-payments \
  --primitive create \
  --repo-root .
```

## Conventions in these scripts

- Argparse for inputs (every script is self-documenting via `--help`)
- Typed Pydantic v2 results from the SDK
- Outcome handling per the v0.2.0 contract:
  - `outcome: success` → continue
  - `outcome: blocker` (pipeline / train) → log + escalate; NOT an
    exception
  - `outcome: not_triggered` (train) → benign; sleep + retry
  - `ExpectedError` / `InternalError` / `ProtocolError` → caught
    explicitly with the right recovery
- No retry loops baked into the SDK — these scripts implement their
  own polling where appropriate (per v0.2.0 Part 4.3 — retries are
  caller-level for subprocess transport)

## See also

- [Mental model](../docs/explanation/mental-model.md) — how the SDK
  is organised
- [Error categories](../docs/explanation/error-categories.md) — when
  to catch which class
- [Blocker is not an exception](../docs/explanation/blocker-not-exception.md)
- [Operations catalogue](../docs/reference/operations.md) — full 38-op
  surface
