#!/usr/bin/env python3
"""Run a train after a batch of executors.

End-to-end orchestration: discover ready WPs → poll for eligibility
growth → fire the train → flip merged WPs to done. Handles every
outcome path (success / not_triggered / blocker / error / etc.).

Mirrors the recipe at docs/recipes/run-train-after-executors.md.

Usage:
    python run-train-after-executors.py \\
        --project my-project \\
        --repo my-org/my-repo \\
        --deploy-workflow "Deploy to Dev" \\
        --staging-url https://staging.example.com \\
        --smoke-cmd "curl -sf https://staging.example.com/health"
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Optional

from sulis_execution import (
    ExpectedError,
    InternalError,
    ProtocolError,
    SulisExecution,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Orchestrate a train run after a batch of executors.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Outcome handling per the SDK v0.2.0 contract:\n"
            "  success       → log + flip merged WPs to done\n"
            "  not_triggered → benign; trigger not met yet\n"
            "  nothing_to_pack → no eligible WPs; nothing to do\n"
            "  blocker       → train ran but reported deterministic failure;\n"
            "                  see train_blocker_path for the BLOCKER record\n"
            "  error         → internal logic error (rare bug)\n"
        ),
    )
    parser.add_argument("--project", required=True, help="Project slug")
    parser.add_argument(
        "--repo",
        help="GitHub repo as org/name (defaults to $GITHUB_REPOSITORY env)",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root directory (default: cwd)",
    )
    parser.add_argument(
        "--deploy-workflow",
        required=True,
        help='Deploy workflow name (e.g., "Deploy to Dev Environment")',
    )
    parser.add_argument("--staging-url", help="Staging URL for health checks")
    parser.add_argument(
        "--smoke-cmd", help="Smoke test command (e.g., curl -sf ...)"
    )
    parser.add_argument(
        "--health-path", help="Health check path (auto-detected from smoke-cmd if not set)"
    )
    parser.add_argument(
        "--min-batch-size",
        type=int,
        default=3,
        help="Minimum eligible WPs before firing the train (default: 3)",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=30,
        help="Seconds between eligibility polls (default: 30)",
    )
    parser.add_argument(
        "--max-wait",
        type=int,
        default=600,
        help="Maximum seconds to wait for the batch to grow (default: 600)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Bypass min-batch-size + trigger check; fire the train now",
    )
    parser.add_argument(
        "--base-branch",
        help="Base ref (default: dev; pass change/{primitive}-{slug} when inside a change worktree)",
    )
    parser.add_argument(
        "--wpx-dir",
        help="Directory containing wpx-* binaries (default: WPX_DIR env / PATH)",
    )
    return parser.parse_args()


def make_client(args: argparse.Namespace) -> SulisExecution:
    return SulisExecution(
        repo_root=Path(args.repo_root).resolve(),
        project=args.project,
        wpx_dir=args.wpx_dir,
    )


def discover_ready(client: SulisExecution) -> list[str]:
    """Step 1 — discover WPs ready for execution."""
    result = client.index.list_ready()
    print(f"[discover] Ready WPs: {result.ready} (max parallel: {result.max_parallel})")
    return result.ready


def wait_for_eligibility(
    client: SulisExecution,
    min_count: int,
    poll_interval: int,
    max_wait: int,
    repo: Optional[str],
) -> int:
    """Step 2 — poll until at least `min_count` WPs are eligible OR max_wait elapses."""
    elapsed = 0
    while elapsed <= max_wait:
        eligibility = client.train.queue_list(repo=repo)
        print(
            f"[wait t+{elapsed:>4d}s] Eligible: {eligibility.eligible_count}; "
            f"Ineligible: {eligibility.ineligible_count}"
        )
        if eligibility.eligible_count >= min_count:
            return eligibility.eligible_count
        time.sleep(poll_interval)
        elapsed += poll_interval
    print(
        f"[wait] Timed out after {max_wait}s; eligible={eligibility.eligible_count} "
        f"(below min {min_count}). Will attempt train.run with --force."
    )
    return eligibility.eligible_count


def fire_train(
    client: SulisExecution, args: argparse.Namespace, force: bool
) -> None:
    """Step 3 — fire the train; handle every outcome."""
    print(f"[train] Firing train (force={force})")
    try:
        result = client.train.run(
            deploy_workflow=args.deploy_workflow,
            staging_url=args.staging_url,
            smoke_cmd=args.smoke_cmd,
            health_path=args.health_path,
            base_branch=args.base_branch,
            force=force,
            repo=args.repo,
        )
    except ProtocolError as err:
        print(f"[FATAL] Transport failure: {err.message}", file=sys.stderr)
        sys.exit(2)
    except ExpectedError as err:
        print(
            f"[REJECTED] CLI rejected the train.run call: {err.message}",
            file=sys.stderr,
        )
        print(f"  context: {err.context}", file=sys.stderr)
        sys.exit(1)
    except InternalError as err:
        print(f"[CRASH] CLI crashed: {err.message}", file=sys.stderr)
        sys.exit(2)

    # Successful operation; outcome may be success, blocker, not_triggered, etc.
    print(f"[train] Outcome: {result.outcome}")
    print(f"[train] train_id: {result.train_id}")

    if result.outcome == "success":
        print(f"[train] Shipped: {result.wps_shipped}")
        if result.deploy_url:
            print(f"[train] Deploy URL: {result.deploy_url}")
        flip_merged_wps_to_done(client, result.wps_shipped)
    elif result.outcome == "not_triggered":
        print(
            f"[train] Trigger not met; {result.eligible_count} eligible. "
            f"Retry later or re-run with --force."
        )
    elif result.outcome == "nothing_to_pack":
        print("[train] No eligible WPs to pack into a batch.")
    elif result.outcome == "blocker":
        print(
            f"[train] BLOCKER: investigate {result.train_blocker_path}",
            file=sys.stderr,
        )
        print(
            f"[train] Bundle attempted: {[b.wp for b in result.bundle]}",
            file=sys.stderr,
        )
        sys.exit(1)
    elif result.outcome == "error":
        print("[train] Internal error in the train logic — file an issue.", file=sys.stderr)
        sys.exit(2)


def flip_merged_wps_to_done(client: SulisExecution, wps: list[str]) -> None:
    """Step 4 — for each merged WP, flip INDEX status to done."""
    for wp_id in wps:
        try:
            client.index.flip_status(wp=wp_id, to="done", expected="step-7-complete")
            print(f"[flip] {wp_id} → done")
        except ExpectedError as err:
            # E.g., status was already done, or wasn't step-7-complete
            print(
                f"[flip] WARN: could not flip {wp_id}: {err.message}",
                file=sys.stderr,
            )


def main() -> None:
    args = parse_args()
    client = make_client(args)

    discover_ready(client)

    if not args.force:
        wait_for_eligibility(
            client,
            min_count=args.min_batch_size,
            poll_interval=args.poll_interval,
            max_wait=args.max_wait,
            repo=args.repo,
        )

    fire_train(client, args, force=args.force)


if __name__ == "__main__":
    main()
