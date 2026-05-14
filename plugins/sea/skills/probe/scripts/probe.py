#!/usr/bin/env python3
"""
/sea:probe — Python orchestrator for deterministic code intelligence.

Entry point. Parses CLI args, hands off to the orchestrator, prints a
one-line JSON status object to stdout.

Usage:
    python probe.py --root . --project myproject
    python probe.py --check-tools
    python probe.py --root . --render        # re-render from existing JSON
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure the `probe` package is importable when running this file directly.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from probe import config as probe_config  # noqa: E402
from probe.detection import detect_tools, format_report  # noqa: E402
from probe.orchestrator import OrchestratorConfig, run as run_orchestrator  # noqa: E402


def _python_version_check() -> None:
    """Probe requires Python 3.11+ for stdlib tomllib + modern type syntax."""
    if sys.version_info < (3, 11):
        sys.stderr.write(
            f"probe requires Python 3.11+ — current: {sys.version.split()[0]}\n"
            "Install a newer Python (e.g. via Homebrew, pyenv, or the official installer).\n"
        )
        sys.exit(3)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="probe",
        description="Deterministic code intelligence for /sea:probe.",
    )
    p.add_argument("--root", default=".", help="Project root directory (default: cwd)")
    p.add_argument("--project", default=None, help="Project name slug (default: root basename)")
    p.add_argument("--output-dir", default=None, help="Where to write probe-raw/ (default: {root}/.architecture/{project}/probe-raw)")
    p.add_argument("--workspace", default=None, help="Restrict to one workspace by name")
    p.add_argument("--max-depth", type=int, default=probe_config.DEFAULT_MAX_DEPTH, help=f"Walk depth ceiling (default {probe_config.DEFAULT_MAX_DEPTH})")
    p.add_argument("--include-pattern", action="append", default=[], help="File glob to include (repeatable)")
    p.add_argument("--exclude-pattern", action="append", default=[], help="File glob to exclude (repeatable)")
    p.add_argument("--languages", default="", help="Comma-separated language codes (ts,python,go,...)")
    p.add_argument("--skip-phase", action="append", default=[], help="Phase ID to skip (e.g. 1.7); repeatable")
    p.add_argument("--run-tests", action="store_true", help="Execute test suite in Phase 1.9 (opt-in)")
    p.add_argument("--test-timeout", type=int, default=300, help="Test execution timeout in seconds (default 300)")
    p.add_argument("--git-lookback-days", type=int, default=probe_config.GIT_HISTORY_LOOKBACK_DAYS_DEFAULT, help="Phase 1.11 lookback window (default 365)")
    for opt_phase in ("tests", "lints", "history", "duplication", "deadcode", "architecture"):
        p.add_argument(f"--skip-{opt_phase}", action="store_true", help=f"Skip Phase relating to {opt_phase}")
    p.add_argument("--continue-on-error", action="store_true", help="Don't fail-fast on runner errors")
    p.add_argument("--json-only", action="store_true", help="Skip rendering Markdown + HTML")
    p.add_argument("--md-only", action="store_true", help="Render Markdown but skip HTML")
    p.add_argument("--quiet", action="store_true", help="Suppress progress output")
    p.add_argument("--verbose", action="store_true", help="Verbose progress output")
    p.add_argument("--check-tools", action="store_true", help="Verify toolchain; exit 0/2")
    p.add_argument("--draft-synthesis", action="store_true", help="Write a synthesis.json template only")
    p.add_argument("--render", action="store_true", help="Re-render Markdown + HTML from existing JSONs (no scan)")
    return p


def _resolve_paths(args: argparse.Namespace) -> tuple[Path, str, Path]:
    root = Path(args.root).resolve()
    if not root.exists() or not root.is_dir():
        sys.stderr.write(f"--root does not exist or is not a directory: {root}\n")
        sys.exit(3)

    project = args.project or root.name

    if args.output_dir:
        output_dir = Path(args.output_dir).resolve()
    else:
        output_dir = root / ".architecture" / project / probe_config.RAW_SUBDIR

    return root, project, output_dir


def _skip_phases(args: argparse.Namespace) -> frozenset[str]:
    skip: set[str] = set(args.skip_phase or [])
    if args.skip_tests:
        skip.add("1.9")
        skip.add("1.15")        # coverage depends on tests
    if args.skip_lints:
        skip.add("1.10")
    if args.skip_history:
        skip.add("1.11")
    if args.skip_duplication:
        skip.add("1.12")
    if args.skip_deadcode:
        skip.add("1.13")
    if args.skip_architecture:
        skip.add("1.14")
    return frozenset(skip)


def main(argv: list[str] | None = None) -> int:
    _python_version_check()

    parser = _build_parser()
    args = parser.parse_args(argv)

    # --check-tools short-circuit
    if args.check_tools:
        report = detect_tools()
        print(format_report(report))
        return 0 if report.all_required_present and not report.failed_sanity else 2

    root, project, output_dir = _resolve_paths(args)
    languages = tuple(s.strip() for s in args.languages.split(",") if s.strip())

    cfg = OrchestratorConfig(
        root=root,
        project=project,
        output_dir=output_dir,
        languages=languages,
        run_tests=args.run_tests,
        test_timeout_sec=args.test_timeout,
        git_lookback_days=args.git_lookback_days,
        workspace_filter=args.workspace,
        skip_phases=_skip_phases(args),
        continue_on_error=args.continue_on_error,
    )

    # --draft-synthesis and --render are short-circuit modes
    if args.draft_synthesis:
        try:
            from probe.render import write_synthesis_draft
        except ImportError:
            sys.stderr.write("render.py not yet implemented; cannot produce synthesis draft.\n")
            return 1
        path = write_synthesis_draft(cfg)
        status = {
            "status": "ok",
            "project": project,
            "synthesis_draft": str(path),
        }
        print(json.dumps(status))
        return 0

    if args.render:
        try:
            from probe.render import render_all
        except ImportError:
            sys.stderr.write("render.py not yet implemented; cannot render.\n")
            return 1
        out = render_all(cfg, render_html=not args.md_only and not args.json_only)
        status = {
            "status": "ok",
            "project": project,
            "raw_dir": str(output_dir),
            "md": str(out.markdown_path) if out.markdown_path else None,
            "html": str(out.html_path) if out.html_path else None,
        }
        print(json.dumps(status))
        return 0

    # Full run
    try:
        result = run_orchestrator(cfg)
    except SystemExit:
        raise
    except Exception as exc:
        sys.stderr.write(f"probe failed: {exc!r}\n")
        return 1

    # Optionally render
    md_path = None
    html_path = None
    if not args.json_only:
        try:
            from probe.render import render_all
            out = render_all(cfg, render_html=not args.md_only)
            md_path = out.markdown_path
            html_path = out.html_path
        except ImportError:
            if not args.quiet:
                sys.stderr.write("render.py not available; only JSON outputs were written.\n")

    status = {
        "status": "ok" if not result.errors else "ok_with_warnings",
        "project": project,
        "workspaces": [w.name for w in result.workspaces],
        "raw_dir": str(result.raw_dir),
        "md": str(md_path) if md_path else None,
        "html": str(html_path) if html_path else None,
        "errors": result.errors if result.errors else None,
    }
    print(json.dumps(status))
    return 0


if __name__ == "__main__":
    sys.exit(main())
