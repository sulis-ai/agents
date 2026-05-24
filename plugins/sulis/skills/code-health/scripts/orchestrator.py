#!/usr/bin/env python3
"""Code-health orchestrator.

Walks the 7-tier registry; invokes wired tier skills; collects findings;
renders a tiered CHECKUP report (markdown for founder mode; JSON for
--raw).

v1 wires tier 5 only (invokes check-readability/scripts/audit.py).
Other tiers render as "not yet checked (planned)".

Tier-gating from .architecture/sulis-checkup/TDD.md ADR-002 is implemented
but is a no-op in v1 since tiers 1+2 aren't wired (no findings → no gate
can fire).

Usage:

    python3 orchestrator.py [--scope auto|pr|codebase] [--pr-number N] [--raw]
                            [--tier N] [--check-everything]

Exit codes:
- 0 = success
- 1 = usage error
- 2 = filesystem / git error
- 3 = a wired tier's underlying script failed (orchestrator continues but reports)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path


# ─── Tier registry ──────────────────────────────────────────────────


@dataclass
class TierSpec:
    number: int
    name: str
    founder_question: str
    wired: bool
    wired_in: str
    founder_skill: str | None
    invoke_script: str | None  # path relative to repo root
    covers: list[str] = field(default_factory=list)
    # Extra args passed to the underlying script — per-tier needs (e.g.,
    # check-tests needs --run to actually execute, with a shorter timeout
    # than its default so code-health doesn't block on slow test suites).
    extra_args: list[str] = field(default_factory=list)


TIER_REGISTRY: list[TierSpec] = [
    TierSpec(
        number=1, name="Exists",
        founder_question="Does it build? Do the basics work?",
        wired=True, wired_in="0.7.0",
        founder_skill="/sulis:check-build",
        invoke_script="plugins/sulis/skills/check-build/scripts/builder.py",
        covers=["Build artefact produces", "Manifest hygiene (plugin.json / marketplace.json / package.json semantics)", "Multi-system detection (pip / npm / go / cargo / docker / make)"],
        # Hygiene-only by default (cheap, no side effects); --run is opt-in
        # because actual builds can have side effects (npm install, docker pull)
        extra_args=[],
    ),
    TierSpec(
        number=2, name="Safe",
        founder_question="Could anyone be harmed? (security, leaked credentials, dangerous patterns)",
        wired=True, wired_in="0.8.0",
        founder_skill="/sulis:check-security",
        invoke_script="plugins/sulis/skills/check-security/scripts/scanner.py",
        covers=["Credential leaks (AWS / GitHub / Stripe / OpenAI / Anthropic / Slack patterns)", "Dangerous code patterns (eval / exec / SQL injection / XSS)", "For deeper analysis: sulis-security:codebase-assess (25 primitives)"],
        extra_args=[],  # scanner runs always (cheap, read-only)
    ),
    TierSpec(
        number=3, name="Works",
        founder_question="Do the tests pass? Does it do what it should?",
        wired=True, wired_in="0.6.0",
        founder_skill="/sulis:check-tests",
        invoke_script="plugins/sulis/skills/check-tests/scripts/regression.py",
        covers=["Tests pass when run", "Regressions (newly-failing tests)", "Functional spec parity (future)", "Smoke / deploy (future)"],
        # check-tests defaults to detection-only; pass --run so code-health
        # actually exercises the suite. Tighter timeout than check-tests'
        # default 120s so a slow suite doesn't block the whole checkup.
        extra_args=["--run", "--timeout", "60"],
    ),
    TierSpec(
        number=4, name="Survives",
        founder_question="Does it handle failure gracefully?",
        wired=True, wired_in="0.10.0",
        founder_skill="/sulis:check-reliability",
        invoke_script="plugins/sulis/skills/check-reliability/scripts/scanner.py",
        covers=["Missing timeouts on HTTP / subprocess calls", "Silent-except (try/except/pass)", "Broad-except without re-raise", "For deeper analysis: sulis-security:codebase-assess (Armor pillar)"],
        extra_args=[],
    ),
    TierSpec(
        number=5, name="Understandable",
        founder_question="Can a new person read it?",
        wired=True, wired_in="0.5.0",
        founder_skill="/sulis:check-readability",
        invoke_script="plugins/sulis/skills/check-readability/scripts/audit.py",
        covers=["Naming clarity", "Module cohesion", "Jargon density"],
    ),
    TierSpec(
        number=6, name="Evolves",
        founder_question="Can we change it without breaking things?",
        wired=True, wired_in="0.11.0",
        founder_skill="/sulis:check-maintainability",
        invoke_script="plugins/sulis/skills/check-maintainability/scripts/scanner.py",
        covers=["Dead code (unused functions / classes / imports)", "Migration completion (deferred to v1.1)", "Surface contract drift (deferred to v1.1)", "Test quality (deferred to v1.1)"],
        extra_args=[],
    ),
    TierSpec(
        number=7, name="Polished",
        founder_question="Does the project feel professional?",
        wired=True, wired_in="0.11.0",
        founder_skill="/sulis:check-polish",
        invoke_script="plugins/sulis/skills/check-polish/scripts/scanner.py",
        covers=["Documentation completeness (README, CHANGELOG, LICENSE)", "Tech-debt density (TODO/FIXME/HACK)", "File hygiene (trailing whitespace, mixed line endings)", "Performance / a11y / UX deferred — need upstream design choice"],
        extra_args=[],
    ),
]


# ─── Data structures ────────────────────────────────────────────────


@dataclass
class TierResult:
    tier: int
    name: str
    status: str  # "passed" | "needs_attention" | "failed" | "not_yet_checked" | "skipped_by_gating" | "error"
    finding_count: int
    findings: list[dict]  # raw findings from the tier skill (JSON envelope)
    wired_in: str | None  # for not_yet_checked
    error_message: str | None  # for error
    severity_summary: dict[str, int] = field(default_factory=dict)  # {high: 0, concern: 1, advisory: 12}


@dataclass
class CheckupReport:
    scope: str
    base_branch: str | None
    pr_number: int | None
    tiers: list[TierResult]
    gating_applied: bool
    gating_reason: str | None
    errors: list[str]


# ─── Tier invocation ────────────────────────────────────────────────


def _marketplace_root() -> Path:
    """The sulis marketplace root, derived from this script's location.

    orchestrator.py lives at
      plugins/sulis/skills/code-health/scripts/orchestrator.py
    so the marketplace root is 5 levels up.
    """
    return Path(__file__).resolve().parents[5]


def invoke_tier(
    tier: TierSpec,
    repo_root: Path,
    scope: str,
    base_branch: str | None,
    pr_number: int | None,
) -> TierResult:
    """Invoke a wired tier's underlying script; collect its JSON findings.

    The tier script LIVES in the sulis marketplace (where the orchestrator
    lives). The tier script OPERATES on the target repo (where --repo-root
    points). These can be the same or different — e.g., when checking a
    founder's project, marketplace = /Users/iain/.claude/.../sulis/ and
    target = /path/to/founder/project/.
    """
    if not tier.wired or not tier.invoke_script:
        return TierResult(
            tier=tier.number, name=tier.name,
            status="not_yet_checked", finding_count=0,
            findings=[], wired_in=tier.wired_in,
            error_message=None,
        )

    script_path = _marketplace_root() / tier.invoke_script
    if not script_path.is_file():
        return TierResult(
            tier=tier.number, name=tier.name,
            status="error", finding_count=0,
            findings=[], wired_in=tier.wired_in,
            error_message=f"underlying script missing: {script_path}",
        )

    cmd = [
        "python3", str(script_path),
        "--raw",
        "--scope", scope,
        "--repo-root", str(repo_root),
    ]
    if base_branch:
        cmd.extend(["--base-branch", base_branch])
    if pr_number:
        cmd.extend(["--pr-number", str(pr_number)])
    cmd.extend(tier.extra_args)

    try:
        proc = subprocess.run(
            cmd, cwd=str(repo_root), capture_output=True, text=True, timeout=300,
        )
    except subprocess.TimeoutExpired:
        return TierResult(
            tier=tier.number, name=tier.name,
            status="error", finding_count=0,
            findings=[], wired_in=tier.wired_in,
            error_message=f"tier-{tier.number} script timed out",
        )
    except FileNotFoundError as exc:
        return TierResult(
            tier=tier.number, name=tier.name,
            status="error", finding_count=0,
            findings=[], wired_in=tier.wired_in,
            error_message=f"python3 not found: {exc}",
        )

    if proc.returncode != 0:
        return TierResult(
            tier=tier.number, name=tier.name,
            status="error", finding_count=0,
            findings=[], wired_in=tier.wired_in,
            error_message=f"tier-{tier.number} exited rc={proc.returncode}: {proc.stderr[:200]}",
        )

    try:
        envelope = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return TierResult(
            tier=tier.number, name=tier.name,
            status="error", finding_count=0,
            findings=[], wired_in=tier.wired_in,
            error_message=f"tier-{tier.number} produced unparseable JSON: {exc}",
        )

    findings = envelope.get("findings", [])
    sev_summary: dict[str, int] = {}
    for f in findings:
        sev = f.get("severity", "advisory")
        sev_summary[sev] = sev_summary.get(sev, 0) + 1

    # Status from severity profile
    if not findings:
        status = "passed"
    elif sev_summary.get("high", 0) > 0:
        status = "failed"
    elif sev_summary.get("concern", 0) > 0:
        status = "needs_attention"
    else:
        status = "needs_attention"  # advisories — needs attention but lighter

    return TierResult(
        tier=tier.number, name=tier.name,
        status=status, finding_count=len(findings),
        findings=findings, wired_in=tier.wired_in,
        error_message=None, severity_summary=sev_summary,
    )


# ─── Gating ─────────────────────────────────────────────────────────


def apply_gating(
    results: list[TierResult],
    check_everything: bool,
) -> tuple[list[TierResult], bool, str | None]:
    """Apply tier 1/2 critical hard-stop rule. v1: no-op since tiers 1+2 are unwired.

    Returns (results, gating_applied, gating_reason).
    """
    if check_everything:
        return results, False, "--check-everything override active"

    for r in results[:2]:  # tiers 1 + 2
        if r.severity_summary.get("critical", 0) > 0:
            # Hard-stop: mark higher tiers as skipped_by_gating
            for higher in results[2:]:
                if higher.status not in ("not_yet_checked", "error"):
                    higher.status = "skipped_by_gating"
                    higher.findings = []
            return (
                results, True,
                f"hard-stop at tier {r.tier} ({r.name}) due to critical finding",
            )

    return results, False, None


# ─── Rendering ──────────────────────────────────────────────────────


STATUS_BADGE_FOUNDER = {
    "passed": "✅ Clear",
    "needs_attention": "🟡 needs attention",
    "failed": "❌ failed",
    "not_yet_checked": "⏳ not yet checked (planned)",
    "skipped_by_gating": "⏭  skipped (fix higher-priority first)",
    "error": "⚠️  couldn't check",
}


def render_markdown(report: CheckupReport) -> str:
    out: list[str] = []
    scope_label = (
        f"PR #{report.pr_number}" if report.pr_number
        else f"current branch vs {report.base_branch}" if report.scope == "pr"
        else "whole codebase"
    )
    out.append(f"# Code Health — {scope_label}")
    out.append("")

    # ── At a glance ──
    out.append("## At a glance")
    out.append("")
    for r in report.tiers:
        badge = STATUS_BADGE_FOUNDER.get(r.status, r.status)
        count_suffix = f" ({r.finding_count} item{'s' if r.finding_count != 1 else ''})" if r.finding_count else ""
        if r.status == "not_yet_checked" and r.wired_in:
            out.append(f"- Tier {r.tier} — **{r.name}**: {badge}")
        else:
            out.append(f"- Tier {r.tier} — **{r.name}**: {badge}{count_suffix}")
    out.append("")

    if report.gating_applied:
        out.append(f"> _Note: {report.gating_reason}. Lower-priority tiers were skipped — fix the higher-priority finding first and re-run._")
        out.append("")

    # ── What needs your attention (failed + needs_attention only) ──
    attention_tiers = [r for r in report.tiers if r.status in ("failed", "needs_attention")]
    if attention_tiers:
        out.append("## What needs your attention")
        out.append("")
        for r in attention_tiers:
            badge = STATUS_BADGE_FOUNDER.get(r.status, r.status)
            out.append(f"### {badge} — Tier {r.tier} ({r.name})")
            out.append("")
            out.append(f"_The tier asks: \"{_tier_question(r.tier)}\"_")
            out.append("")
            for f in r.findings[:5]:  # top 5 per tier in the founder view
                out.append(f"- **{f.get('file', 'unknown')}**" + (f":{f['line']}" if f.get('line') else ""))
                out.append(f"  - {f.get('message', '')}")
                if f.get('suggestion'):
                    out.append(f"  - Suggestion: {f['suggestion']}")
            if len(r.findings) > 5:
                out.append(f"- _…and {len(r.findings) - 5} more — see `--raw` for full list._")
            out.append("")

    # ── What's not yet checked ──
    stubbed = [r for r in report.tiers if r.status == "not_yet_checked"]
    if stubbed:
        out.append("## What's not yet checked")
        out.append("")
        out.append("These tiers aren't silently passing — they aren't running yet:")
        out.append("")
        for r in stubbed:
            out.append(f"- Tier {r.tier} — **{r.name}** ({r.wired_in})")
        out.append("")
        out.append("When their underlying skills ship, they'll wire in automatically. The framework here is forward-compatible.")
        out.append("")

    # ── Errors ──
    if report.errors:
        out.append("## Errors")
        out.append("")
        for e in report.errors:
            out.append(f"- {e}")
        out.append("")

    out.append("---")
    out.append("")
    out.append("_This skill is read-only. It identifies what to consider; it never modifies code._")
    return "\n".join(out)


def _tier_question(tier_num: int) -> str:
    for t in TIER_REGISTRY:
        if t.number == tier_num:
            return t.founder_question
    return ""


def render_json(report: CheckupReport) -> str:
    return json.dumps({
        "scope": report.scope,
        "base_branch": report.base_branch,
        "pr_number": report.pr_number,
        "gating_applied": report.gating_applied,
        "gating_reason": report.gating_reason,
        "tiers": [asdict(r) for r in report.tiers],
        "errors": report.errors,
    }, indent=2)


# ─── Main ────────────────────────────────────────────────────────────


def _print_dispatch_instructions(mode: str, repo_root: str, scope: str) -> None:
    """Print Agent-dispatch instructions for Claude to execute.

    Called when --mode=deep or --mode=audited. The orchestrator itself
    cannot invoke Agents (no Agent tool available to a Python subprocess);
    only Claude in the calling session has the Agent tool. So we print
    the dispatch plan; Claude reads it and acts.

    This mirrors the pattern in sulis-execution's run-all skill.
    """
    project = Path(repo_root).resolve().name
    prompt_dir = Path(__file__).resolve().parent.parent / "agent_prompts"

    print(f"# code-health {mode} mode — dispatch plan")
    print()
    print("The orchestrator cannot dispatch Agents (pure Python). Claude must")
    print("execute the following dispatches in the calling session.")
    print()
    print("## Inputs (substitute into each prompt template):")
    print(f"  repo_root = {repo_root}")
    print(f"  project   = {project}")
    print(f"  scope     = {scope}")
    print(f"  mode      = {mode}")
    print()
    print("## Dispatches (issue ALL in a single message for parallelism):")
    print()
    tier_to_skill = {
        1: ("check-build", "Explore"),
        2: ("check-security", "general-purpose"),
        3: ("check-tests", "general-purpose"),
        4: ("check-reliability", "Explore"),
        5: ("check-readability", "Explore"),
        6: ("check-maintainability", "Explore"),
        7: ("check-polish", "Explore"),
    }
    for n in range(1, 8):
        skill, subagent_type = tier_to_skill[n]
        prompt_path = prompt_dir / f"{skill}.md"
        print(f"  Agent(subagent_type={subagent_type!r}, description={skill!r},")
        print(f"        prompt=<read+substitute {prompt_path}>)")
    print()
    if mode == "audited":
        print("## After deep-mode dispatches return:")
        print()
        print("Pick the highest-stakes tier (typically check-security), then re-dispatch:")
        ind_path = prompt_dir / "independence-check.md"
        print(f"  Agent(subagent_type='Explore', description='independence-check',")
        print(f"        prompt=<read+substitute {ind_path} with prior tier-2 response>)")
        print()
    print("## Aggregate (after all dispatches return):")
    print()
    print("Write each agent's response to a temp file, then invoke:")
    print()
    print("  python3 plugins/sulis/skills/code-health/scripts/aggregator.py \\")
    for n in range(1, 8):
        skill, _ = tier_to_skill[n]
        print(f"      --tier-response {n}:<path/to/{skill}-response.md> \\")
    if mode == "audited":
        print("      --independence-check <path/to/independence-response.md> \\")
    print("      --scope", scope, "--project", project)
    print()
    print("The aggregator emits the CHECKUP.md (founder mode) or JSON envelope (--raw).")


def main() -> int:
    parser = argparse.ArgumentParser(description="Code-health orchestrator (7-tier wrapper).")
    parser.add_argument("--scope", choices=("auto", "pr", "codebase"), default="auto")
    parser.add_argument("--base-branch", default=None)
    parser.add_argument("--pr-number", type=int, default=None)
    parser.add_argument("--raw", action="store_true", help="Output JSON instead of markdown")
    parser.add_argument("--tier", type=int, default=None, help="Run only tier N")
    parser.add_argument("--check-everything", action="store_true", help="Disable hard-stop gating")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--mode", choices=("fast", "deep", "audited"), default="deep",
        help="Invocation mode. deep (default; founder-interactive) = Agent dispatch from the "
             "calling Claude session; orchestrator prints dispatch instructions and exits. "
             "fast = subprocess-only (zero tokens; use for CI / cron / ambient monitoring). "
             "audited = deep + Independence Check second pass (SPIRAL_TEMPLATES HEAVY compliant; "
             "use for production-readiness reviews).")
    args = parser.parse_args()

    if args.mode in ("deep", "audited"):
        # The orchestrator (pure Python) can't dispatch Agents; only Claude in
        # the calling session can invoke the Agent tool. Print the dispatch
        # instructions for Claude to act on, then exit cleanly. See
        # plugins/sulis/skills/code-health/SKILL.md "When invoked — DEEP mode"
        # and "AUDITED mode" sections for the full workflow.
        _print_dispatch_instructions(args.mode, args.repo_root, args.scope)
        return 0

    repo_root = Path(args.repo_root).resolve()
    if not (repo_root / ".git").exists():
        print(f"error: {repo_root} is not a git repo", file=sys.stderr)
        return 2

    # Filter tier list if --tier provided
    tiers_to_walk = TIER_REGISTRY
    if args.tier is not None:
        tiers_to_walk = [t for t in TIER_REGISTRY if t.number == args.tier]
        if not tiers_to_walk:
            print(f"error: tier {args.tier} not in registry", file=sys.stderr)
            return 1

    errors: list[str] = []
    results: list[TierResult] = []
    for tier in tiers_to_walk:
        result = invoke_tier(
            tier, repo_root, args.scope, args.base_branch, args.pr_number,
        )
        if result.error_message:
            errors.append(f"tier-{tier.number} ({tier.name}): {result.error_message}")
        results.append(result)

    # If --tier filtered us, still pad with the unwired tiers so the report
    # shows the full registry — unless --raw, where the caller probably wants
    # just the filtered set.
    if args.tier is not None and not args.raw:
        full = []
        for t in TIER_REGISTRY:
            existing = next((r for r in results if r.tier == t.number), None)
            if existing:
                full.append(existing)
            else:
                full.append(TierResult(
                    tier=t.number, name=t.name,
                    status="not_yet_checked", finding_count=0,
                    findings=[], wired_in=t.wired_in,
                    error_message=None,
                ))
        results = full

    # Apply gating
    results, gating_applied, gating_reason = apply_gating(results, args.check_everything)

    # Resolve scope label for the report (read from first wired tier's result if possible)
    scope_resolved = args.scope
    base_resolved = args.base_branch
    for r in results:
        if r.findings:
            # The underlying script reported what scope/base it used; not currently
            # surfaced through TierResult — left as args-level info for now.
            break

    report = CheckupReport(
        scope=scope_resolved,
        base_branch=base_resolved,
        pr_number=args.pr_number,
        tiers=results,
        gating_applied=gating_applied,
        gating_reason=gating_reason,
        errors=errors,
    )

    if args.raw:
        print(render_json(report))
    else:
        print(render_markdown(report))

    total_findings = sum(r.finding_count for r in results)
    wired_count = sum(1 for r in results if r.status not in ("not_yet_checked",))
    print(
        f"code-health: tiers_walked={len(results)}, wired_tiers={wired_count}, "
        f"total_findings={total_findings}, gating={gating_applied}",
        file=sys.stderr,
    )

    return 3 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
