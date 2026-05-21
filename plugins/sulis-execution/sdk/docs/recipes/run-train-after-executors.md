# Recipe: Run a train after a batch of executors

**Applies to:** sulis-execution v0.1.0

A common end-to-end task: an orchestrator dispatches N parallel
executors; each completes Steps 1-7 and flips its WP to
`step-7-complete`; then a single train shipment fires for the batch.

This recipe combines the SDK methods that orchestrator code typically
needs.

## The flow

```
1. Discover ready WPs
2. (Outside the SDK: dispatch executors per WP)
3. Wait for executors to complete Steps 1-7
4. Check eligibility (was Step 7 reached? CI green?)
5. Fire wpx-train run for the eligible batch
6. Inspect the result; on success, flip step-7-complete → done per WP
```

## Python implementation

```python
import time
from sulis_execution import (
    SulisExecution,
    ExpectedError,
    ProtocolError,
)

client = SulisExecution(
    repo_root='/path/to/repo',
    project='my-project',
)

# 1. Discover ready WPs
ready = client.index.list_ready()
print(f"Ready: {ready.ready} (max parallel: {ready.max_parallel})")

# 2. (Dispatch executors externally — outside this script)
# This recipe assumes executors run separately and flip WPs to
# step-7-complete when done.

# 3. Wait for the eligible set to grow (poll every 30s, cap at 10 min)
for _ in range(20):
    eligibility = client.train.queue_list()
    if eligibility.eligible_count >= 3:
        print(f"Eligible: {eligibility.eligible_count}; firing train")
        break
    time.sleep(30)

# 4. Run the train (fires only if trigger conditions met; force to bypass)
result = client.train.run(
    deploy_workflow='Deploy to Dev Environment',
    staging_url='https://staging.example.com',
    smoke_cmd='curl -sf https://staging.example.com/health',
)

# 5. Inspect outcome
if result.outcome == 'not_triggered':
    print(f"Trigger not met yet: {result.eligible_count} eligible")
elif result.outcome == 'success':
    print(f"Shipped: {result.wps_shipped}")
    print(f"Deploy: {result.deploy_url}")
    # 6. Flip each merged WP to done
    for wp_id in result.wps_shipped:
        try:
            client.index.flip_status(
                wp=wp_id, to='done', expected='step-7-complete'
            )
        except ExpectedError as e:
            print(f"WARN: couldn't flip {wp_id}: {e.message}")
elif result.outcome == 'blocker':
    # See result.train_blocker_path for the BLOCKER record
    print(f"Train blocked; investigate {result.train_blocker_path}")
    print(f"Bundle attempted: {[b.wp for b in result.bundle]}")
```

## What this recipe demonstrates

- `index.list_ready` for discovery
- `train.queue_list` for polling eligibility growth
- `train.run` returning outcome=not_triggered as a normal result (not exception)
- `train.run` returning outcome=success vs outcome=blocker
- `index.flip_status` with CAS guard (`expected`) to avoid races

## What's missing (real orchestrator concerns)

- Executor dispatch (separate concern; the SDK doesn't dispatch agents)
- Retry on train outcome=blocker (caller-level decision)
- Notification (post to Slack, email, etc. — caller wiring)
- Concurrent runs against multiple projects (separate clients per project)

## See also

- [Mental model](../explanation/mental-model.md)
- [Operations catalogue](../reference/operations.md)
