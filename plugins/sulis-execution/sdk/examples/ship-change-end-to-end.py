#!/usr/bin/env python3
"""Ship a change end-to-end.

CW-04 lifecycle in code: start → status check → finish --merge → cleanup.
Handles ExpectedError on `branch_already_exists`.

Mirrors the recipe at docs/recipes/ship-change-end-to-end.md.

Usage:
    python ship-change-end-to-end.py \\
        --slug introduce-payments \\
        --primitive create \\
        --repo-root /path/to/repo

    # Or to skip ahead to finish (assumes the change already started):
    python ship-change-end-to-end.py \\
        --slug introduce-payments \\
        --primitive create \\
        --repo-root /path/to/repo \\
        --action finish

    # Or to ship via PR instead of merge:
    python ship-change-end-to-end.py \\
        --slug introduce-payments \\
        --primitive create \\
        --action finish \\
        --via pr
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sulis_execution import (
    ExpectedError,
    InternalError,
    ProtocolError,
    SulisExecution,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ship a change end-to-end using the sulis-execution SDK.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Per the SDK v0.2.0 surface:\n"
            "  change.start  → provisions the branch + worktree\n"
            "  change.status → reports ahead/behind, worktree state, metadata\n"
            "  change.finish → squash-merges (or opens PR) + cleanup\n"
            "\n"
            "Note: the `change.adopt` path (retrofit in-flight work) is\n"
            "exposed by the SDK but not used here — see\n"
            "docs/recipes/ship-change-end-to-end.md.\n"
        ),
    )
    parser.add_argument(
        "--slug",
        required=True,
        help='Change slug, e.g. "introduce-payments"',
    )
    parser.add_argument(
        "--primitive",
        default="feat",
        help="Change primitive: feat / create / refactor / etc. (default: feat)",
    )
    parser.add_argument(
        "--base",
        default="dev",
        help="Base branch for the change (default: dev)",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root directory (default: cwd)",
    )
    parser.add_argument(
        "--project",
        # change.* is project-independent, but the client constructor
        # requires it (it's used by other resources). Provide a dummy.
        default="default",
        help="Project slug (any value; required by the SDK client but unused by change ops)",
    )
    parser.add_argument(
        "--action",
        choices=["full", "start", "status", "finish"],
        default="full",
        help="Which lifecycle step to run (default: full — start → status → finish)",
    )
    parser.add_argument(
        "--via",
        choices=["merge", "pr"],
        default="merge",
        help="When finishing, ship via squash-merge or open a PR (default: merge)",
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Skip worktree/branch cleanup on finish",
    )
    parser.add_argument(
        "--wpx-dir",
        help="Directory containing the sulis-change binary (default: WPX_DIR env / PATH)",
    )
    return parser.parse_args()


def make_client(args: argparse.Namespace) -> SulisExecution:
    return SulisExecution(
        repo_root=Path(args.repo_root).resolve(),
        project=args.project,
        wpx_dir=args.wpx_dir,
    )


def start_change(client: SulisExecution, args: argparse.Namespace) -> bool:
    """Return True if the change was newly created, False if it already exists."""
    try:
        started = client.change.start(
            slug=args.slug,
            primitive=args.primitive,
            base=args.base,
        )
    except ExpectedError as err:
        if (err.code or "") == "branch_already_exists":
            print(
                f"[start] Change {args.primitive}/{args.slug} already exists "
                f"— skipping start. Use change.adopt if you want to retrofit."
            )
            return False
        raise
    print(f"[start] Branch: {started.branch}")
    print(f"[start] Worktree: {started.worktree_path}")
    print(f"[start] Metadata: {started.metadata_path}")
    return True


def check_status(client: SulisExecution, args: argparse.Namespace) -> int:
    """Returns ahead_of_base count (so the caller can decide if there's
    anything to ship)."""
    status = client.change.status(
        slug=args.slug, primitive=args.primitive, base=args.base
    )
    ahead = status.ahead_of_base or 0
    behind = status.behind_base or 0
    print(f"[status] Branch: {status.branch}")
    print(f"[status] Worktree present: {status.worktree_present}")
    print(f"[status] Ahead of {args.base}: {ahead} commits; Behind: {behind}")
    if status.branch_sha:
        print(f"[status] Branch SHA: {status.branch_sha[:8]}")
    return ahead


def finish_change(client: SulisExecution, args: argparse.Namespace) -> None:
    via_merge = args.via == "merge"
    via_pr = args.via == "pr"
    print(f"[finish] Shipping via {args.via}; cleanup={'off' if args.no_cleanup else 'on'}")
    finished = client.change.finish(
        slug=args.slug,
        primitive=args.primitive,
        base=args.base,
        merge=via_merge,
        pr=via_pr,
        no_cleanup=args.no_cleanup,
    )
    print(f"[finish] Outcome: {finished.outcome.mode}")
    if finished.outcome.pr_url:
        print(f"[finish] PR URL: {finished.outcome.pr_url}")
    if finished.cleanup:
        print(f"[finish] Cleanup: {finished.cleanup}")


def main() -> None:
    args = parse_args()
    client = make_client(args)

    try:
        if args.action == "start":
            start_change(client, args)
        elif args.action == "status":
            check_status(client, args)
        elif args.action == "finish":
            ahead = check_status(client, args)
            if ahead == 0:
                print(
                    "[main] No commits on the change branch yet; "
                    "nothing to finish.",
                    file=sys.stderr,
                )
                sys.exit(1)
            finish_change(client, args)
        else:  # full
            newly_started = start_change(client, args)
            if newly_started:
                print(
                    "[main] Change started. Do your work in the worktree, "
                    "then re-run this script with --action finish to ship."
                )
                return
            # The change existed — assume work is done; check + finish
            ahead = check_status(client, args)
            if ahead == 0:
                print(
                    "[main] Change exists but no commits to ship. "
                    "Do the work in the worktree, then re-run with --action finish.",
                    file=sys.stderr,
                )
                sys.exit(1)
            finish_change(client, args)

    except ProtocolError as err:
        print(f"[FATAL] Transport failure: {err.message}", file=sys.stderr)
        sys.exit(2)
    except ExpectedError as err:
        print(f"[REJECTED] {err.message}", file=sys.stderr)
        print(f"  code: {err.code}", file=sys.stderr)
        print(f"  context: {err.context}", file=sys.stderr)
        sys.exit(1)
    except InternalError as err:
        print(f"[CRASH] CLI crashed: {err.message}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
