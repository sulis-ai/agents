"""
Render probe-raw JSON outputs into CODE_INTELLIGENCE.md AND .html.

Both formats are generated from the same source data (the 15 phase JSON
files + synthesis.json). Markdown is for machine/LLM/git-diff consumption;
HTML is the human-navigable review surface.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import (
    FINAL_HTML,
    FINAL_MARKDOWN,
    HIGH_CCN_THRESHOLD,
    PHASE_FILES,
    SYNTHESIS_FILE,
    SYSTEM_MANIFEST_FILE,
)
from .models import write_json
from .orchestrator import OrchestratorConfig


@dataclass(frozen=True)
class RenderResult:
    markdown_path: Path | None
    html_path: Path | None


# ─── Section labels & order ───────────────────────────────────────────────

PHASE_LABELS: dict[str, str] = {
    "1.1": "Infrastructure & Stack",
    "1.2": "Capability Inventory",
    "1.3": "Extension Points",
    "1.4": "Reusable Abstractions",
    "1.5": "Coupling & Cycles",
    "1.6": "Complexity Hotspots",
    "1.7": "Wrapper-Rot Candidates",
    "1.8": "Conventions",
    "1.9": "Test Suite Health",
    "1.10": "Lint Signal",
    "1.11": "Git History",
    "1.12": "Code Duplication",
    "1.13": "Dead Code",
    "1.14": "Architecture Rules",
    "1.15": "Coverage",
}

PHASE_TOOLS: dict[str, str] = {
    "1.1": "scc", "1.2": "ast-grep", "1.3": "ast-grep",
    "1.4": "grep", "1.5": "ast-grep+Tarjan", "1.6": "lizard",
    "1.7": "ast-grep", "1.8": "filesystem", "1.9": "test-frameworks",
    "1.10": "linters", "1.11": "git", "1.12": "jscpd",
    "1.13": "ts-prune/vulture/deadcode", "1.14": "dependency-cruiser/import-linter",
    "1.15": "coverage-reports",
}


# ─── Loaders ──────────────────────────────────────────────────────────────


def _load_repo_phase(raw_dir: Path, phase: str) -> dict[str, Any] | None:
    """Load a repo-wide phase JSON (1.16 / 1.17) from probe-raw/."""
    fname = PHASE_FILES.get(phase)
    if not fname:
        return None
    path = raw_dir / fname
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _load_phase(workspace_dir: Path, phase: str) -> dict[str, Any] | None:
    fname = PHASE_FILES.get(phase)
    if not fname:
        return None
    path = workspace_dir / fname
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _load_synthesis(raw_dir: Path) -> dict[str, Any] | None:
    path = raw_dir / SYNTHESIS_FILE
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _load_system_manifest(raw_dir: Path) -> dict[str, Any] | None:
    path = raw_dir / SYSTEM_MANIFEST_FILE
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


# ─── Public API ───────────────────────────────────────────────────────────


def render_all(cfg: OrchestratorConfig, *, render_html: bool = True) -> RenderResult:
    md_path = render_markdown(cfg)
    html_path = render_html_doc(cfg) if render_html else None
    return RenderResult(markdown_path=md_path, html_path=html_path)


def write_synthesis_draft(cfg: OrchestratorConfig) -> Path:
    """Write a draft synthesis.json with empty fields + hints for the LLM."""
    draft = {
        "summary": "",
        "summary_hint": (
            "5-sentence overview: what this codebase is, what patterns it follows, "
            "what's healthy, what's smelly. Read probe-raw/1_1_stack.json and the "
            "module inventory before writing."
        ),
        "pattern_recognition": [],
        "pattern_recognition_hint": (
            "System-level patterns. Each entry: "
            "{pattern, confidence: high|medium|low, evidence: [paths]}"
        ),
        "wrapper_rot_triage": [],
        "wrapper_rot_triage_hint": (
            "For each candidate in probe-raw/1_7_wrappers.json: classify as "
            "wrapper-rot, legitimate-adapter, in-progress-strangle, or "
            "branch-by-abstraction, with a one-line recommendation."
        ),
        "recommendations": [],
        "recommendations_hint": (
            "Prioritised list citing evidence from multiple phase JSONs. Each: "
            "{priority, primitive, target, evidence_phases: ['1.6','1.11'], "
            "rationale, confidence}"
        ),
        "reserved_vocabulary_hint": _build_reserved_vocabulary_hint(cfg.output_dir),
        "generated_at": "",
        "generated_by": "draft",
    }
    path = cfg.output_dir / SYNTHESIS_FILE
    write_json(draft, path)
    return path


# Words whose semantics are pinned by Kubernetes / Sulis-manifest convention.
# Introducing a new abstract with one of these names creates a polysemy risk:
# readers will import lifecycle expectations (persistence, reconciliation,
# `apply` semantics) that may not hold for the new concept. Downstream skills
# (blueprint) consume this list to gate on naming collisions.
_INFRASTRUCTURE_RESERVED_WORDS: tuple[str, ...] = (
    "kind", "apiVersion", "metadata", "spec", "status",
    "apply", "reconcile", "manifest", "resource",
)


def _build_reserved_vocabulary_hint(raw_dir: Path) -> dict[str, Any]:
    """Compose the vocabulary-collision hint for downstream design skills.

    Reads `1_16_deployment.json` (if present) to surface every YAML `kind:`
    value actually in use in the repo — these are the words a designer must
    not reuse as abstract type names without an explicit ADR justifying the
    shared dispatch semantics.
    """
    deployment = _load_repo_phase(raw_dir, "1.16")
    yaml_kinds: list[str] = []
    if deployment:
        payload = deployment.get("payload") or {}
        sulis_kinds = payload.get("sulis_kinds_present") or []
        # Also surface non-Sulis YAML sub-kinds (k8s Deployment, Service, etc.)
        # since they share the same dispatch shape.
        other_subkinds = {
            a.get("sub_kind")
            for a in (payload.get("artifacts") or [])
            if a.get("sub_kind") and a.get("kind") in ("k8s-manifest", "argocd", "flux")
        }
        yaml_kinds = sorted(set(sulis_kinds) | other_subkinds)
    return {
        "yaml_kinds_in_use": yaml_kinds,
        "infrastructure_reserved": list(_INFRASTRUCTURE_RESERVED_WORDS),
        "guidance": (
            "Treat these as reserved when naming abstract types, classes, or "
            "registry keys in downstream design (TDD, ADRs, GLOSSARY). "
            "A new abstract that shares a name with a YAML `kind:` value "
            "imports its dispatch shape — readers will assume shared "
            "lifecycle semantics (persistence, convergent reconciliation, "
            "`apply` verb). If the new concept differs on any of those, "
            "rename it, or write an ADR explaining the shared-dispatch "
            "intent. Blueprint's Reserved-Vocabulary Sweep enforces this."
        ),
    }


# ─── Markdown rendering ───────────────────────────────────────────────────


def render_markdown(cfg: OrchestratorConfig) -> Path | None:
    system = _load_system_manifest(cfg.output_dir)
    if not system:
        return None

    synthesis = _load_synthesis(cfg.output_dir)
    workspaces = system.get("workspaces") or []

    lines: list[str] = [
        f"# Code Intelligence — {cfg.project}",
        "",
        f"> **Project:** {cfg.project}",
        f"> **Generated:** {system.get('finished_at')}",
        f"> **Workspaces:** {len(workspaces)}",
        f"> **Toolchain:** " + ", ".join(
            f"{n}={(v.splitlines()[0] if v else 'n/a')}"
            for n, v in (system.get("tool_versions") or {}).items()
        ),
        "",
        "## Summary",
        "",
        (synthesis.get("summary") if synthesis and synthesis.get("summary") else
         "_LLM synthesis not yet written. Run `python probe.py --draft-synthesis` "
         "to write a template, then fill it._"),
        "",
    ]

    if synthesis and synthesis.get("recommendations"):
        lines.append("## Recommendations")
        lines.append("")
        for i, rec in enumerate(synthesis["recommendations"], start=1):
            lines.append(
                f"{i}. **{rec.get('primitive', 'unknown')}** — `{rec.get('target', '')}`"
            )
            if rec.get("rationale"):
                lines.append(f"   {rec['rationale']}")
            ev = rec.get("evidence_phases") or []
            if ev:
                lines.append(f"   Evidence: {', '.join(ev)}")
            lines.append(f"   Confidence: {rec.get('confidence', 'unknown')}")
            lines.append("")

    # Repo-wide phases (1.16, 1.17) — between Recommendations and per-workspace
    deployment_data = _load_repo_phase(cfg.output_dir, "1.16")
    if deployment_data:
        _md_deployment(lines, deployment_data)
    credentials_data = _load_repo_phase(cfg.output_dir, "1.17")
    if credentials_data:
        _md_credentials(lines, credentials_data)

    for ws_info in workspaces:
        ws_name = ws_info["name"]
        ws_dir = cfg.output_dir / ws_name if ws_name != "." else cfg.output_dir
        lines.append(f"## Workspace: `{ws_name}`")
        lines.append("")
        lines.append(f"> **Path:** `{ws_info['path']}`  ·  **Style:** {ws_info.get('style')}")
        lines.append("")
        _render_ws_md(lines, ws_dir)

    out_path = cfg.root / ".architecture" / cfg.project / FINAL_MARKDOWN
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def _render_ws_md(lines: list[str], ws_dir: Path) -> None:
    """Append all phase-derived sections to `lines` in Markdown."""
    for phase, label in PHASE_LABELS.items():
        data = _load_phase(ws_dir, phase)
        if not data:
            continue
        payload = data.get("payload") or {}
        lines.append(f"### {label}")
        lines.append(f"`[deterministic: {PHASE_TOOLS[phase]}]`  · phase {phase}  · duration {data.get('duration_ms', 0)}ms")
        if data.get("warnings"):
            lines.append("")
            for w in data["warnings"]:
                lines.append(f"> ⚠ {w}")
        lines.append("")
        renderer = _PHASE_MD_RENDERERS.get(phase)
        if renderer:
            renderer(lines, payload)
        else:
            lines.append("_(no detailed renderer for this phase)_")
            lines.append("")


def _md_stack(lines: list[str], p: dict) -> None:
    lines.append(f"- **Primary language:** {p.get('primary_language') or 'n/a'}")
    lines.append(f"- **Total files:** {p.get('total_files', 0)}")
    lines.append(f"- **Total LOC:** {p.get('total_loc', 0):,}")
    lines.append(f"- **Total complexity:** {p.get('total_complexity', 0):,}")
    langs = p.get("languages") or {}
    if langs:
        lines.append("")
        lines.append("| Language | Files | Code | Complexity |")
        lines.append("|---|---|---|---|")
        for n, s in sorted(langs.items(), key=lambda kv: -kv[1].get("code", 0)):
            lines.append(f"| {n} | {s.get('files', 0)} | {s.get('code', 0):,} | {s.get('complexity_total', 0)} |")
    frameworks = p.get("frameworks") or []
    if frameworks:
        lines.append("")
        lines.append("**Frameworks:** " + ", ".join(f"`{f['name']}`" for f in frameworks))
    lines.append("")


def _md_capabilities(lines: list[str], p: dict) -> None:
    by_kind = p.get("by_kind") or {}
    by_lang = p.get("by_language") or {}
    items = p.get("items") or []
    if by_kind:
        lines.append("**By kind:** " + ", ".join(f"{k}={v}" for k, v in sorted(by_kind.items())))
    if by_lang:
        lines.append("**By language:** " + ", ".join(f"{k}={v}" for k, v in sorted(by_lang.items())))
    lines.append(f"\nTotal: **{len(items)}** symbols.")
    if items:
        lines.append("\nSample (first 20):\n")
        lines.append("| Kind | Name | File | Line |")
        lines.append("|---|---|---|---|")
        for c in items[:20]:
            lines.append(f"| {c.get('kind', '')} | `{c.get('name', '')}` | `{c.get('file', '')}` | {c.get('line', 0)} |")
    lines.append("")


def _md_extensions(lines: list[str], p: dict) -> None:
    items = p.get("items") or []
    by_kind = p.get("by_kind") or {}
    lines.append("**By kind:** " + ", ".join(f"{k}={v}" for k, v in sorted(by_kind.items())) if by_kind else "_No extension points detected._")
    if items:
        lines.append("\n| Kind | Name | File | Line | Implementations |")
        lines.append("|---|---|---|---|---|")
        for e in items[:30]:
            impls = ", ".join(e.get("implementations") or []) or "—"
            lines.append(f"| {e.get('kind', '')} | `{e.get('name', '')}` | `{e.get('file', '')}` | {e.get('line', 0)} | {impls} |")
    lines.append("")


def _md_reuse(lines: list[str], p: dict) -> None:
    modules = p.get("modules") or []
    lines.append(f"Modules with consumer count ≥ threshold: **{len(modules)}**")
    if modules:
        lines.append("\n| Module | Language | Consumer count | Kitchen-sink? |")
        lines.append("|---|---|---|---|")
        for m in modules[:30]:
            lines.append(f"| `{m.get('module_path', '')}` | {m.get('language', '')} | {m.get('consumer_count', 0)} | {'⚠ yes' if m.get('is_kitchen_sink') else 'no'} |")
    lines.append("")


def _md_coupling(lines: list[str], p: dict) -> None:
    cycles = p.get("cycles") or []
    high_fanin = p.get("high_fanin") or []
    high_fanout = p.get("high_fanout") or []
    modules = p.get("modules") or []
    lines.append(f"**Modules tracked:** {len(modules)}")
    lines.append(f"**Cycles:** {len(cycles)}{(' ⚠' if cycles else '')}")
    lines.append(f"**High fan-in (>threshold):** {len(high_fanin)}")
    lines.append(f"**High fan-out (>threshold):** {len(high_fanout)}")
    if cycles:
        lines.append("\n**Detected cycles:**\n")
        for cyc in cycles[:10]:
            lines.append(f"- {' ↔ '.join(f'`{c}`' for c in cyc)}")
    if high_fanout:
        lines.append("\n**High fan-out modules (candidates for Decompose):**")
        for m in high_fanout[:10]:
            lines.append(f"- `{m}`")
    lines.append("")


def _md_complexity(lines: list[str], p: dict) -> None:
    fns = p.get("functions") or []
    fragile = p.get("fragile_files") or []
    lines.append(f"Functions over CCN {p.get('threshold_ccn', HIGH_CCN_THRESHOLD)}: **{len(fns)}**")
    lines.append(f"Files over module-fragility threshold: **{len(fragile)}**")
    if fns:
        lines.append("\n| Function | File | Line | CCN | NLOC |")
        lines.append("|---|---|---|---|---|")
        for f in fns[:20]:
            lines.append(f"| `{f.get('function', '')}` | `{f.get('file', '')}` | {f.get('line_start', 0)} | **{f.get('ccn', 0)}** | {f.get('nloc', 0)} |")
    lines.append("")


def _md_wrappers(lines: list[str], p: dict) -> None:
    candidates = p.get("candidates") or []
    internal = p.get("count_internal", 0)
    external = p.get("count_external_likely", 0)
    if not candidates:
        lines.append("_No wrapper-rot candidates detected._")
        lines.append("")
        return
    lines.append(f"**Internal candidates (review for Refactor):** {internal}")
    lines.append(f"**External-adapter candidates (likely legitimate):** {external}")
    lines.append("\n| Wrapper | Wrapped target | Suffix | Classification |")
    lines.append("|---|---|---|---|")
    for c in candidates[:20]:
        target = c.get("wrapped_target") or "(no internal target found)"
        cls = "external-likely" if c.get("is_external_adapter_candidate") else "**internal-review-needed**"
        lines.append(f"| `{c.get('wrapper_class', '')}` | `{target}` | {c.get('suffix_match', '')} | {cls} |")
    lines.append("")


def _md_conventions(lines: list[str], p: dict) -> None:
    fn = p.get("file_naming") or {}
    tn = p.get("test_naming") or {}
    layout = p.get("module_layout") or "unknown"
    eh = p.get("error_handling") or "unknown"
    roles = p.get("naming_for_roles") or {}
    lines.append(f"- **Module layout:** {layout}")
    lines.append(f"- **Error handling:** {eh}")
    if fn:
        lines.append(f"- **File naming:** {fn.get('pattern')} (confidence {fn.get('confidence', 0):.0%})")
    if tn:
        lines.append(f"- **Test naming:** {tn.get('pattern')} (confidence {tn.get('confidence', 0):.0%})")
    if roles:
        lines.append("- **Role suffixes detected:** " + ", ".join(f"`{r}={pat}`" for r, pat in roles.items()))
    lines.append("")


def _md_tests(lines: list[str], p: dict) -> None:
    fw = p.get("framework", "none-detected")
    lines.append(f"- **Framework:** `{fw}`")
    lines.append(f"- **Test files:** {p.get('test_files', 0)}")
    lines.append(f"- **Tests enumerated:** {p.get('tests_enumerated', 0)}")
    lines.append(f"- **Executed?** {'yes' if p.get('executed') else 'no (--run-tests not set)'}")
    if p.get("executed"):
        lines.append(f"- **Passed:** {p.get('passed', 0)}")
        lines.append(f"- **Failed:** {p.get('failed', 0)}")
    if p.get("coverage_tool_detected"):
        lines.append(f"- **Coverage tool detected:** {p['coverage_tool_detected']}")
    lines.append("")


def _md_lints(lines: list[str], p: dict) -> None:
    configured = p.get("linters_configured") or []
    warns = p.get("warnings_by_file") or {}
    errs = p.get("errors_by_file") or {}
    lines.append(f"- **Linters configured:** " + (", ".join(configured) if configured else "_none_"))
    lines.append(f"- **Warnings:** {sum(warns.values())}")
    lines.append(f"- **Errors:** {sum(errs.values())}")
    lines.append(f"- **Typecheck errors:** {p.get('typecheck_errors', 0)}")
    rules = p.get("rule_violations") or {}
    if rules:
        lines.append("- **Top rules:** " + ", ".join(f"`{r}`×{c}" for r, c in list(rules.items())[:5]))
    lines.append("")


def _md_history(lines: list[str], p: dict) -> None:
    churn = p.get("file_churn") or []
    high_churn = p.get("high_churn_files") or []
    bus_factor_one = p.get("bus_factor_one") or []
    co_change = p.get("co_change_pairs") or []
    lines.append(f"- **Lookback window:** {p.get('lookback_days', 0)} days")
    lines.append(f"- **Files tracked:** {len(churn)}")
    lines.append(f"- **High-churn files (>threshold):** {len(high_churn)}")
    lines.append(f"- **Bus factor = 1 files:** {len(bus_factor_one)}")
    lines.append(f"- **Co-change pairs above threshold:** {len(co_change)}")
    if high_churn:
        lines.append("\n**Top churn files:**\n")
        for f in churn[:10]:
            lines.append(f"- `{f.get('file', '')}` — {f.get('commits_in_lookback', 0)} commits, {f.get('distinct_authors', 0)} author(s)")
    lines.append("")


def _md_duplication(lines: list[str], p: dict) -> None:
    blocks = p.get("blocks") or []
    lines.append(f"- **Duplicated lines:** {p.get('duplicated_lines', 0)}")
    lines.append(f"- **Duplicated %:** {p.get('duplicated_pct', 0):.1f}%")
    lines.append(f"- **Duplicate blocks:** {len(blocks)}")
    lines.append("")


def _md_deadcode(lines: list[str], p: dict) -> None:
    syms = p.get("symbols") or []
    by_lang = p.get("by_language") or {}
    by_tool = p.get("by_tool") or {}
    lines.append(f"- **Total dead symbols:** {len(syms)}")
    if by_lang:
        lines.append(f"- **By language:** " + ", ".join(f"{k}={v}" for k, v in by_lang.items()))
    if by_tool:
        lines.append(f"- **By tool:** " + ", ".join(f"{k}={v}" for k, v in by_tool.items()))
    if syms:
        lines.append("\n| Symbol | File | Line | Kind | Confidence |")
        lines.append("|---|---|---|---|---|")
        for s in syms[:20]:
            lines.append(f"| `{s.get('name', '')}` | `{s.get('file', '')}` | {s.get('line', 0)} | {s.get('kind', '')} | {s.get('confidence', '')} |")
    lines.append("")


def _md_architecture(lines: list[str], p: dict) -> None:
    cfg_path = p.get("rules_config")
    violations = p.get("violations") or []
    lines.append(f"- **Rules config:** {'`'+cfg_path+'`' if cfg_path else '_none detected_'}")
    lines.append(f"- **Violations:** {len(violations)}")
    lines.append(f"- **Rules passed / failed:** {p.get('rules_passed', 0)} / {p.get('rules_failed', 0)}")
    if violations:
        lines.append("\n| Rule | Source → Target | Severity |")
        lines.append("|---|---|---|")
        for v in violations[:20]:
            lines.append(f"| `{v.get('rule_id', '')}` | `{v.get('source', '')}` → `{v.get('target', '')}` | {v.get('severity', '')} |")
    lines.append("")


def _md_coverage(lines: list[str], p: dict) -> None:
    overall = p.get("overall_pct")
    by_file = p.get("by_file") or {}
    low = p.get("low_coverage_files") or []
    src = p.get("source", "none")
    lines.append(f"- **Source:** {src}")
    lines.append(f"- **Overall coverage:** {overall:.1f}%" if isinstance(overall, (int, float)) else "- **Overall coverage:** _not available_")
    lines.append(f"- **Files with coverage data:** {len(by_file)}")
    lines.append(f"- **Files below threshold:** {len(low)}")
    lines.append("")


_PHASE_MD_RENDERERS: dict[str, Any] = {
    "1.1": _md_stack, "1.2": _md_capabilities, "1.3": _md_extensions,
    "1.4": _md_reuse, "1.5": _md_coupling, "1.6": _md_complexity,
    "1.7": _md_wrappers, "1.8": _md_conventions, "1.9": _md_tests,
    "1.10": _md_lints, "1.11": _md_history, "1.12": _md_duplication,
    "1.13": _md_deadcode, "1.14": _md_architecture, "1.15": _md_coverage,
}


# ─── Repo-wide section renderers (1.16 Deployment / 1.17 Credentials) ─────


def _md_deployment(lines: list[str], data: dict) -> None:
    p = data.get("payload") or {}
    artifacts = p.get("artifacts") or []
    by_kind = p.get("by_kind") or {}
    by_env = p.get("by_environment") or {}
    sulis_kinds = p.get("sulis_kinds_present") or []
    platforms = p.get("target_platforms") or []

    lines.append("## Deployment Topology")
    lines.append("")
    if data.get("warnings"):
        for w in data["warnings"]:
            lines.append(f"> ⚠ {w}")
        lines.append("")
    lines.append(f"- **Artifacts catalogued:** {len(artifacts)}")
    lines.append(f"- **Kinds detected:** {len(by_kind)}")
    lines.append(f"- **Target platforms:** {', '.join(platforms) if platforms else '_none_'}")
    if by_env:
        lines.append("- **Environments observed:** " + ", ".join(
            f"{k} ({v})" for k, v in sorted(by_env.items())
        ))
    lines.append(f"- **YAML parser:** {p.get('yaml_parser', 'unknown')}")
    lines.append("")
    if by_kind:
        lines.append("### Artifacts by kind")
        lines.append("")
        lines.append("| Kind | Count |")
        lines.append("|---|---|")
        for k, v in sorted(by_kind.items(), key=lambda kv: -kv[1]):
            lines.append(f"| `{k}` | {v} |")
        lines.append("")

    if sulis_kinds:
        sulis_artifacts = [a for a in artifacts if a.get("kind") == "sulis-manifest"]
        lines.append("### Sulis Manifests")
        lines.append("")
        lines.append(f"Kinds present: {', '.join(f'`{k}`' for k in sulis_kinds)}")
        lines.append("")
        lines.append("| Sub-kind | Name | Path | Image | Port | Replicas |")
        lines.append("|---|---|---|---|---|---|")
        for a in sulis_artifacts[:50]:
            ex = a.get("extras") or {}
            lines.append(
                f"| {a.get('sub_kind') or ''} | `{a.get('name') or ''}` | "
                f"`{a.get('path', '')}` | "
                f"{ex.get('image') or '—'} | {ex.get('port') or '—'} | "
                f"{ex.get('replicas') or '—'} |"
            )
        lines.append("")

    # Generic artifact listing (truncated)
    if artifacts:
        lines.append("### All artifacts (first 80)")
        lines.append("")
        lines.append("| Kind | Sub-kind | Name | Path | Environment | Secrets |")
        lines.append("|---|---|---|---|---|---|")
        for a in artifacts[:80]:
            secrets = ", ".join(a.get("secret_references") or []) or "—"
            lines.append(
                f"| {a.get('kind', '')} | {a.get('sub_kind') or ''} | "
                f"`{a.get('name') or ''}` | `{a.get('path', '')}` | "
                f"{a.get('environment') or '—'} | {secrets} |"
            )
        lines.append("")


def _md_credentials(lines: list[str], data: dict) -> None:
    p = data.get("payload") or {}
    lines.append("## Credential Scanning")
    lines.append("")
    if p.get("skipped"):
        lines.append(f"> _Phase skipped: {p.get('skip_reason') or 'unknown reason'}_")
        lines.append("")
        lines.append("To enable credential scanning, install detect-secrets:")
        lines.append("")
        lines.append("```")
        lines.append("pipx install detect-secrets")
        lines.append("```")
        lines.append("")
        return
    findings = p.get("findings") or []
    new_findings = p.get("new_findings") or []
    known_findings = p.get("known_findings") or []
    by_type = p.get("by_type") or {}

    lines.append(f"- **Total findings:** {len(findings)}")
    lines.append(f"- **New (not in baseline):** **{len(new_findings)}**")
    lines.append(f"- **Known (acknowledged in baseline):** {len(known_findings)}")
    lines.append(
        f"- **Baseline present:** "
        f"{'yes (' + p.get('baseline_path', '') + ')' if p.get('baseline_present') else 'no'}"
    )
    lines.append("")
    lines.append("> Privacy contract: only SHA-1 hashes are stored; secret values never appear in this report.")
    lines.append("")

    if by_type:
        lines.append("### Findings by type")
        lines.append("")
        lines.append("| Type | Count |")
        lines.append("|---|---|")
        for k, v in sorted(by_type.items(), key=lambda kv: -kv[1]):
            lines.append(f"| `{k}` | {v} |")
        lines.append("")

    if new_findings:
        lines.append("### New findings")
        lines.append("")
        lines.append("| Type | File | Line | Hash (SHA-1) |")
        lines.append("|---|---|---|---|")
        for f in new_findings[:80]:
            lines.append(
                f"| `{f.get('secret_type', '')}` | `{f.get('file', '')}` | "
                f"{f.get('line', 0)} | `{f.get('hashed_secret', '')[:16]}…` |"
            )
        lines.append("")


# ─── HTML rendering ───────────────────────────────────────────────────────


def render_html_doc(cfg: OrchestratorConfig) -> Path | None:
    system = _load_system_manifest(cfg.output_dir)
    if not system:
        return None

    synthesis = _load_synthesis(cfg.output_dir)
    workspaces = system.get("workspaces") or []
    templates_dir = Path(__file__).parent / "render_templates"
    css = (templates_dir / "styles.css").read_text(encoding="utf-8")
    js = (templates_dir / "interactivity.js").read_text(encoding="utf-8")

    # Compute dashboard metrics across all workspaces
    total_loc = 0
    total_hotspots = 0
    total_wrappers_internal = 0
    total_recommendations = len((synthesis or {}).get("recommendations") or [])

    for ws_info in workspaces:
        ws_name = ws_info["name"]
        ws_dir = cfg.output_dir / ws_name if ws_name != "." else cfg.output_dir
        stack = _load_phase(ws_dir, "1.1") or {}
        total_loc += (stack.get("payload") or {}).get("total_loc", 0)
        cx = _load_phase(ws_dir, "1.6") or {}
        total_hotspots += len((cx.get("payload") or {}).get("functions") or [])
        wr = _load_phase(ws_dir, "1.7") or {}
        total_wrappers_internal += (wr.get("payload") or {}).get("count_internal", 0)

    # Repo-wide phases — load once before dashboard so we can count
    deployment_data = _load_repo_phase(cfg.output_dir, "1.16")
    credentials_data = _load_repo_phase(cfg.output_dir, "1.17")
    deployment_count = (
        len((deployment_data.get("payload") or {}).get("artifacts") or [])
        if deployment_data else 0
    )
    credential_new_count = (
        len((credentials_data.get("payload") or {}).get("new_findings") or [])
        if credentials_data else 0
    )

    # Build HTML
    body_parts: list[str] = []
    body_parts.append(_html_header(cfg.project, system))
    body_parts.append(_html_dashboard(
        total_loc, total_hotspots, total_wrappers_internal,
        total_recommendations,
        deployment_count=deployment_count if deployment_data else None,
        credential_new_count=credential_new_count if credentials_data else None,
    ))
    body_parts.append('<div class="layout">')
    body_parts.append(_html_sidebar(
        workspaces,
        has_deployment=deployment_data is not None,
        has_credentials=credentials_data is not None,
    ))
    body_parts.append('<main class="content">')

    if synthesis and synthesis.get("summary"):
        body_parts.append(_html_section("summary", "Summary", f"<p>{_md_to_html(synthesis['summary'])}</p>"))
    else:
        body_parts.append(_html_section("summary", "Summary",
            "<p><em>LLM synthesis not yet written. Run "
            "<code>python probe.py --draft-synthesis</code> to write a "
            "template, then fill it.</em></p>"))

    if synthesis and synthesis.get("recommendations"):
        body_parts.append(_html_recommendations(synthesis["recommendations"]))

    # Repo-wide sections between Recommendations and workspaces
    if deployment_data:
        body_parts.append(_html_deployment(deployment_data))
    if credentials_data:
        body_parts.append(_html_credentials(credentials_data))

    for ws_info in workspaces:
        body_parts.append(_html_workspace(ws_info, cfg.output_dir))

    body_parts.append('</main></div>')
    body_parts.append(_html_footer(system))

    full = (
        "<!DOCTYPE html>\n"
        f"<html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        f"<title>Code Intelligence — {html.escape(cfg.project)}</title>"
        f"<style>{css}</style></head>"
        f"<body>"
        + "".join(body_parts)
        + f"<script>{js}</script></body></html>"
    )

    out_path = cfg.root / ".architecture" / cfg.project / FINAL_HTML
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(full, encoding="utf-8")
    return out_path


# ─── HTML section helpers ─────────────────────────────────────────────────


def _html_header(project: str, system: dict) -> str:
    tools = system.get("tool_versions") or {}
    tool_str = " · ".join(
        f"{html.escape(n)}={html.escape((v.splitlines()[0] if v else 'n/a'))}"
        for n, v in tools.items()
    )
    return (
        f'<header class="top">'
        f'<h1>{html.escape(project)}</h1>'
        f'<div class="meta">Generated {html.escape(system.get("finished_at", ""))} · '
        f'<span class="mono">{tool_str}</span></div>'
        f'</header>'
    )


def _html_dashboard(
    loc: int, hotspots: int, wrappers: int, recs: int,
    *,
    deployment_count: int | None = None,
    credential_new_count: int | None = None,
) -> str:
    def card(metric: str, label: str, klass: str = "") -> str:
        cls = "card" + (f" {klass}" if klass else "")
        return (
            f'<div class="{cls}">'
            f'<div class="metric">{html.escape(metric)}</div>'
            f'<div class="label">{html.escape(label)}</div>'
            f'</div>'
        )
    cards_html = [
        card(f"{loc:,}", "LOC"),
        card(str(hotspots), "Complexity hotspots"),
        card(str(wrappers), "Internal wrappers (review)"),
        card(str(recs), "Recommendations"),
    ]
    if deployment_count is not None:
        cards_html.append(card(str(deployment_count), "Deployment artifacts"))
    if credential_new_count is not None:
        klass = "alert" if credential_new_count > 0 else ""
        cards_html.append(card(
            str(credential_new_count), "Credential findings (new)", klass=klass,
        ))
    return '<div class="dashboard">' + "".join(cards_html) + '</div>'


def _html_sidebar(
    workspaces: list[dict],
    *,
    has_deployment: bool = False,
    has_credentials: bool = False,
) -> str:
    items: list[str] = ['<li><a href="#summary">Summary</a></li>',
                        '<li><a href="#recommendations">Recommendations</a></li>']
    if has_deployment:
        items.append('<li><a href="#deployment">Deployment Topology</a></li>')
    if has_credentials:
        items.append('<li><a href="#credentials">Credential Scanning</a></li>')
    for ws in workspaces:
        ws_name = ws["name"]
        slug = _slug(ws_name)
        items.append(f'<li><a href="#ws-{slug}"><strong>Workspace: {html.escape(ws_name)}</strong></a></li>')
        for phase, label in PHASE_LABELS.items():
            items.append(
                f'<li><a href="#ws-{slug}-{phase.replace(".", "_")}">'
                f'<span class="mono">{phase}</span> {html.escape(label)}</a></li>'
            )
    return (
        '<nav class="sidebar">'
        '<h3>Navigation</h3>'
        f'<ul>{"".join(items)}</ul>'
        '</nav>'
    )


def _html_deployment(data: dict) -> str:
    p = data.get("payload") or {}
    artifacts = p.get("artifacts") or []
    by_kind = p.get("by_kind") or {}
    by_env = p.get("by_environment") or {}
    sulis_kinds = p.get("sulis_kinds_present") or []
    platforms = p.get("target_platforms") or []
    warnings = data.get("warnings") or []

    parts: list[str] = []
    parts.append(f'<p><strong>Artifacts catalogued:</strong> {len(artifacts)}</p>')
    parts.append(f'<p><strong>Kinds:</strong> {len(by_kind)}</p>')
    if platforms:
        parts.append('<p><strong>Target platforms:</strong> ' +
                     ", ".join(f'<code>{html.escape(s)}</code>' for s in platforms) + '</p>')
    if by_env:
        env_str = ", ".join(f'{html.escape(k)} ({v})' for k, v in sorted(by_env.items()))
        parts.append(f'<p><strong>Environments observed:</strong> {env_str}</p>')
    parts.append(f'<p><strong>YAML parser:</strong> <code>{html.escape(p.get("yaml_parser", "unknown"))}</code></p>')
    for w in warnings:
        parts.append(f'<div class="warning">⚠ {html.escape(str(w))}</div>')

    if by_kind:
        rows = [[html.escape(k), str(v)] for k, v in sorted(by_kind.items(), key=lambda kv: -kv[1])]
        parts.append('<h3>Artifacts by kind</h3>')
        parts.append(_table(["Kind", "Count"], rows))

    if sulis_kinds:
        sulis_artifacts = [a for a in artifacts if a.get("kind") == "sulis-manifest"]
        parts.append('<h3>Sulis Manifests</h3>')
        parts.append(
            '<p>Kinds present: '
            + ", ".join(f'<code>{html.escape(k)}</code>' for k in sulis_kinds)
            + '</p>'
        )
        rows = []
        for a in sulis_artifacts[:200]:
            ex = a.get("extras") or {}
            rows.append([
                html.escape(a.get("sub_kind") or ""),
                html.escape(a.get("name") or ""),
                html.escape(a.get("path", "")),
                html.escape(str(ex.get("image") or "—")),
                html.escape(str(ex.get("port") or "—")),
                html.escape(str(ex.get("replicas") or "—")),
            ])
        parts.append(_table(
            ["Sub-kind", "Name", "Path", "Image", "Port", "Replicas"],
            rows,
        ))

    # Full artifact table.
    parts.append('<h3>All artifacts</h3>')
    rows = []
    for a in artifacts[:500]:
        secrets = ", ".join(a.get("secret_references") or [])
        rows.append([
            html.escape(a.get("kind", "")),
            html.escape(a.get("sub_kind") or ""),
            html.escape(a.get("name") or ""),
            html.escape(a.get("path", "")),
            html.escape(a.get("environment") or ""),
            html.escape(secrets),
        ])
    parts.append(_table(
        ["Kind", "Sub-kind", "Name", "Path", "Environment", "Secrets-referenced"],
        rows,
    ))
    return _html_section("deployment", "Deployment Topology", "".join(parts))


def _html_credentials(data: dict) -> str:
    p = data.get("payload") or {}
    parts: list[str] = []
    if p.get("skipped"):
        parts.append(
            '<div class="info-card">'
            f'<p><strong>Phase skipped:</strong> {html.escape(p.get("skip_reason") or "")}</p>'
            '<p>To enable credential scanning, install detect-secrets:</p>'
            '<pre><code>pipx install detect-secrets</code></pre>'
            '</div>'
        )
        return _html_section("credentials", "Credential Scanning", "".join(parts))

    findings = p.get("findings") or []
    new_findings = p.get("new_findings") or []
    known_findings = p.get("known_findings") or []
    by_type = p.get("by_type") or {}

    new_class = "alert" if new_findings else "ok"
    parts.append(
        f'<div class="credential-banner {new_class}">'
        f'<strong>NEW: {len(new_findings)}</strong> · '
        f'KNOWN (baselined): {len(known_findings)} · '
        f'Total: {len(findings)} · '
        f'Baseline: {"yes (" + html.escape(p.get("baseline_path", "")) + ")" if p.get("baseline_present") else "no"}'
        f'</div>'
    )
    parts.append(
        '<p><em>Privacy contract: only SHA-1 hashes are stored; secret values '
        'never appear in this report.</em></p>'
    )

    if by_type:
        rows = [[k, str(v)] for k, v in sorted(by_type.items(), key=lambda kv: -kv[1])]
        parts.append('<h3>Findings by type</h3>')
        parts.append(_table(["Type", "Count"], rows))

    if findings:
        parts.append('<h3>All findings</h3>')
        rows = []
        for f in findings[:500]:
            rows.append([
                html.escape(f.get("secret_type", "")),
                html.escape(f.get("file", "")),
                str(f.get("line", 0)),
                html.escape((f.get("hashed_secret") or "")[:16]) + "…",
                "yes" if f.get("is_known") else "<strong>NEW</strong>",
            ])
        parts.append(_table(
            ["Type", "File", "Line", "Hash (SHA-1)", "Known?"],
            rows,
        ))
    return _html_section("credentials", "Credential Scanning", "".join(parts))


def _html_section(section_id: str, title: str, inner: str) -> str:
    return (
        f'<section class="card" id="{html.escape(section_id)}">'
        f'<h2>{html.escape(title)}</h2>'
        f'<div class="body">{inner}</div>'
        f'</section>'
    )


def _html_recommendations(recs: list[dict]) -> str:
    if not recs:
        return _html_section("recommendations", "Recommendations",
                             "<p><em>No recommendations yet.</em></p>")
    cards: list[str] = []
    for r in recs:
        cards.append(
            '<div class="recommendation">'
            f'<div><span class="primitive">{html.escape(r.get("primitive", ""))}</span> '
            f'<span class="target">{html.escape(r.get("target", ""))}</span> '
            f'<span class="badge {_confidence_badge(r.get("confidence"))}">{html.escape(r.get("confidence", ""))}</span></div>'
            f'<div class="rationale">{_md_to_html(r.get("rationale", ""))}</div>'
            f'<div>{"".join(f"<span class=\"evidence-chip\">{html.escape(e)}</span>" for e in (r.get("evidence_phases") or []))}</div>'
            '</div>'
        )
    filter_input = (
        '<input class="filter-input" placeholder="Filter recommendations…" '
        'data-target="#recommendations">'
    )
    return _html_section("recommendations", "Recommendations",
                         filter_input + "".join(cards))


def _html_workspace(ws_info: dict, raw_dir: Path) -> str:
    ws_name = ws_info["name"]
    slug = _slug(ws_name)
    ws_dir = raw_dir / ws_name if ws_name != "." else raw_dir

    inner_parts: list[str] = [
        f'<p><span class="mono">{html.escape(ws_info["path"])}</span> · '
        f'<span class="badge gray">{html.escape(ws_info.get("style", ""))}</span></p>'
    ]
    for phase, label in PHASE_LABELS.items():
        data = _load_phase(ws_dir, phase)
        if not data:
            continue
        payload = data.get("payload") or {}
        section_id = f"ws-{slug}-{phase.replace('.', '_')}"
        renderer = _PHASE_HTML_RENDERERS.get(phase)
        body_html = renderer(payload) if renderer else '<em>(no detailed renderer)</em>'
        warnings_html = ""
        if data.get("warnings"):
            warnings_html = '<div>' + "".join(
                f'<div class="badge amber">⚠ {html.escape(w)}</div>' for w in data["warnings"]
            ) + '</div>'
        inner_parts.append(
            f'<section class="card" id="{section_id}">'
            f'<h2>{html.escape(label)} '
            f'<span class="badge green">deterministic: {html.escape(PHASE_TOOLS[phase])}</span>'
            f'<span class="badge gray">phase {phase}</span>'
            f'<span class="badge gray">{data.get("duration_ms", 0)}ms</span></h2>'
            f'<div class="body">{warnings_html}{body_html}</div>'
            f'</section>'
        )

    return (
        f'<section class="card" id="ws-{slug}">'
        f'<h2>Workspace: {html.escape(ws_name)}</h2>'
        f'<div class="body">{"".join(inner_parts)}</div>'
        f'</section>'
    )


def _html_footer(system: dict) -> str:
    return (
        '<footer class="bottom">'
        f'Generated by /sulis:analyse-codebase · '
        f'<span class="mono">{html.escape(system.get("project", ""))}</span> · '
        f'Refresh: <code>python probe.py --root . --project &lt;name&gt;</code>'
        '</footer>'
    )


# ─── Per-phase HTML renderers ─────────────────────────────────────────────


def _table(headers: list[str], rows: list[list[str]], sortable: bool = True,
           filter_target: str | None = None, numeric_cols: list[int] | None = None) -> str:
    numeric = set(numeric_cols or [])
    th_html = "".join(
        f'<th{"" if i not in numeric else " data-type=\"number\""}>{html.escape(h)}</th>'
        for i, h in enumerate(headers)
    )
    rows_html = ""
    for row in rows:
        rows_html += "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
    cls = ' class="sortable"' if sortable else ''
    filter_html = ""
    if filter_target:
        filter_html = (
            f'<input class="filter-input" placeholder="Filter…" '
            f'data-target="{filter_target}">'
        )
    return f'{filter_html}<table{cls}><thead><tr>{th_html}</tr></thead><tbody>{rows_html}</tbody></table>'


def _html_stack(p: dict) -> str:
    summary = (
        f'<p><strong>Primary:</strong> {html.escape(p.get("primary_language") or "n/a")} · '
        f'<strong>Files:</strong> {p.get("total_files", 0):,} · '
        f'<strong>LOC:</strong> {p.get("total_loc", 0):,} · '
        f'<strong>Complexity:</strong> {p.get("total_complexity", 0):,}</p>'
    )
    langs = p.get("languages") or {}
    rows = [
        [html.escape(n), f"{s.get('files', 0):,}", f"{s.get('code', 0):,}",
         f"{s.get('blanks', 0):,}", f"{s.get('complexity_total', 0):,}"]
        for n, s in sorted(langs.items(), key=lambda kv: -kv[1].get("code", 0))
    ]
    return summary + _table(["Language", "Files", "Code", "Blanks", "Complexity"], rows,
                            numeric_cols=[1, 2, 3, 4])


def _html_capabilities(p: dict) -> str:
    items = p.get("items") or []
    by_kind = p.get("by_kind") or {}
    summary = (
        f'<p><strong>Total:</strong> {len(items):,} symbols · '
        + " · ".join(f"<span class=\"badge gray\">{html.escape(k)}: {v}</span>" for k, v in sorted(by_kind.items()))
        + "</p>"
    )
    rows = [
        [html.escape(c.get("kind", "")), f'<code>{html.escape(c.get("name", ""))}</code>',
         f'<code>{html.escape(c.get("file", ""))}</code>', str(c.get("line", 0)),
         html.escape(c.get("language", ""))]
        for c in items[:300]
    ]
    return summary + _table(
        ["Kind", "Name", "File", "Line", "Language"],
        rows, filter_target="section.card",
        numeric_cols=[3],
    )


def _html_extensions(p: dict) -> str:
    items = p.get("items") or []
    if not items:
        return '<p><em>No extension points detected.</em></p>'
    rows = [
        [html.escape(e.get("kind", "")), f'<code>{html.escape(e.get("name", ""))}</code>',
         f'<code>{html.escape(e.get("file", ""))}</code>', str(e.get("line", 0)),
         html.escape(", ".join(e.get("implementations") or []) or "—")]
        for e in items[:100]
    ]
    return _table(["Kind", "Name", "File", "Line", "Implementations"], rows, numeric_cols=[3])


def _html_reuse(p: dict) -> str:
    modules = p.get("modules") or []
    summary = f'<p><strong>{len(modules)}</strong> modules with ≥ threshold consumers.</p>'
    rows = [
        [f'<code>{html.escape(m.get("module_path", ""))}</code>',
         html.escape(m.get("language", "")), str(m.get("consumer_count", 0)),
         '<span class="badge amber">⚠</span>' if m.get("is_kitchen_sink") else "—"]
        for m in modules[:100]
    ]
    return summary + _table(["Module", "Language", "Consumer count", "Kitchen-sink"],
                            rows, numeric_cols=[2])


def _html_coupling(p: dict) -> str:
    cycles = p.get("cycles") or []
    high_fanin = p.get("high_fanin") or []
    high_fanout = p.get("high_fanout") or []
    summary = (
        f'<p><strong>Cycles:</strong> {len(cycles)} '
        f'<span class="badge {"red" if cycles else "green"}">'
        f'{"⚠ structural smell" if cycles else "clean"}</span> · '
        f'<strong>High fan-in:</strong> {len(high_fanin)} · '
        f'<strong>High fan-out:</strong> {len(high_fanout)}</p>'
    )
    body = summary
    if cycles:
        body += '<h4>Detected cycles</h4><ul>'
        for cyc in cycles[:20]:
            body += '<li>' + " ↔ ".join(f"<code>{html.escape(c)}</code>" for c in cyc) + '</li>'
        body += '</ul>'
    if high_fanout:
        body += '<h4>High fan-out (Decompose candidates)</h4><ul>'
        for m in high_fanout[:20]:
            body += f'<li><code>{html.escape(m)}</code></li>'
        body += '</ul>'
    return body


def _html_complexity(p: dict) -> str:
    fns = p.get("functions") or []
    fragile = p.get("fragile_files") or []
    summary = (
        f'<p><strong>{len(fns)}</strong> functions over CCN threshold · '
        f'<strong>{len(fragile)}</strong> fragile files</p>'
    )
    if not fns:
        return summary + '<p><em>No hotspots detected.</em></p>'
    rows = [
        [f'<code>{html.escape(f.get("function", ""))}</code>',
         f'<code>{html.escape(f.get("file", ""))}</code>',
         str(f.get("line_start", 0)),
         f'<strong>{f.get("ccn", 0)}</strong>',
         str(f.get("nloc", 0)),
         str(f.get("params", 0))]
        for f in fns[:200]
    ]
    return summary + _table(
        ["Function", "File", "Line", "CCN", "NLOC", "Params"],
        rows, filter_target="section.card",
        numeric_cols=[2, 3, 4, 5],
    )


def _html_wrappers(p: dict) -> str:
    candidates = p.get("candidates") or []
    if not candidates:
        return '<p><em>No wrapper-rot candidates detected.</em></p>'
    rows = []
    for c in candidates[:100]:
        target = c.get("wrapped_target") or "(no internal target found)"
        is_ext = c.get("is_external_adapter_candidate")
        badge = ('<span class="badge green">external-likely</span>' if is_ext
                 else '<span class="badge amber">internal — review</span>')
        rows.append([
            f'<code>{html.escape(c.get("wrapper_class", ""))}</code>',
            f'<code>{html.escape(target)}</code>',
            html.escape(c.get("suffix_match", "")),
            badge,
            f'<code>{html.escape(c.get("wrapper_file", ""))}</code>',
        ])
    return _table(["Wrapper", "Wrapped target", "Suffix", "Classification", "File"], rows,
                  sortable=True)


def _html_conventions(p: dict) -> str:
    items = []
    if p.get("file_naming"):
        fn = p["file_naming"]
        items.append(f'<li><strong>File naming:</strong> {html.escape(fn["pattern"])} ({fn["confidence"]:.0%})</li>')
    if p.get("test_naming"):
        tn = p["test_naming"]
        items.append(f'<li><strong>Test naming:</strong> {html.escape(tn["pattern"])} ({tn["confidence"]:.0%})</li>')
    items.append(f'<li><strong>Module layout:</strong> {html.escape(p.get("module_layout", ""))}</li>')
    items.append(f'<li><strong>Error handling:</strong> {html.escape(p.get("error_handling", ""))}</li>')
    roles = p.get("naming_for_roles") or {}
    if roles:
        role_str = ", ".join(f'<code>{html.escape(r)}={html.escape(pat)}</code>' for r, pat in roles.items())
        items.append(f'<li><strong>Roles:</strong> {role_str}</li>')
    return '<ul>' + "".join(items) + '</ul>'


def _html_tests(p: dict) -> str:
    fw = p.get("framework", "none-detected")
    items = [
        f'<li><strong>Framework:</strong> <code>{html.escape(fw)}</code></li>',
        f'<li><strong>Test files:</strong> {p.get("test_files", 0)}</li>',
        f'<li><strong>Tests enumerated:</strong> {p.get("tests_enumerated", 0)}</li>',
        f'<li><strong>Executed:</strong> {"yes" if p.get("executed") else "no (--run-tests not set)"}</li>',
    ]
    if p.get("executed"):
        items.append(f'<li><strong>Passed:</strong> {p.get("passed", 0)}</li>')
        items.append(f'<li><strong>Failed:</strong> {p.get("failed", 0)}</li>')
    if p.get("coverage_tool_detected"):
        items.append(f'<li><strong>Coverage tool:</strong> {html.escape(p["coverage_tool_detected"])}</li>')
    return '<ul>' + "".join(items) + '</ul>'


def _html_lints(p: dict) -> str:
    configured = p.get("linters_configured") or []
    items = [
        f'<li><strong>Linters configured:</strong> ' + (", ".join(f'<code>{html.escape(l)}</code>' for l in configured) if configured else "<em>none</em>") + '</li>',
        f'<li><strong>Warnings:</strong> {sum((p.get("warnings_by_file") or {}).values())}</li>',
        f'<li><strong>Errors:</strong> {sum((p.get("errors_by_file") or {}).values())}</li>',
        f'<li><strong>Typecheck errors:</strong> {p.get("typecheck_errors", 0)}</li>',
    ]
    return '<ul>' + "".join(items) + '</ul>'


def _html_history(p: dict) -> str:
    churn = p.get("file_churn") or []
    high = p.get("high_churn_files") or []
    bus = p.get("bus_factor_one") or []
    co = p.get("co_change_pairs") or []
    summary = (
        f'<p><strong>Lookback:</strong> {p.get("lookback_days", 0)}d · '
        f'<strong>Files:</strong> {len(churn)} · '
        f'<strong>High-churn:</strong> {len(high)} · '
        f'<strong>Bus-factor=1:</strong> {len(bus)} · '
        f'<strong>Co-change pairs:</strong> {len(co)}</p>'
    )
    rows = [
        [f'<code>{html.escape(f.get("file", ""))}</code>',
         str(f.get("commits_in_lookback", 0)),
         str(f.get("distinct_authors", 0)),
         str(f.get("age_days", 0)),
         html.escape(f.get("last_commit_iso", ""))]
        for f in churn[:50]
    ]
    return summary + _table(
        ["File", "Commits", "Authors", "Age (days)", "Last commit"],
        rows, numeric_cols=[1, 2, 3],
    )


def _html_duplication(p: dict) -> str:
    return (
        f'<p><strong>Duplicated lines:</strong> {p.get("duplicated_lines", 0):,} · '
        f'<strong>Duplicated %:</strong> {p.get("duplicated_pct", 0):.1f}% · '
        f'<strong>Blocks:</strong> {len(p.get("blocks") or [])}</p>'
    )


def _html_deadcode(p: dict) -> str:
    syms = p.get("symbols") or []
    if not syms:
        return '<p><em>No dead symbols detected (or detector unavailable).</em></p>'
    rows = [
        [f'<code>{html.escape(s.get("name", ""))}</code>',
         f'<code>{html.escape(s.get("file", ""))}</code>',
         str(s.get("line", 0)),
         html.escape(s.get("kind", "")),
         f'<span class="badge {_confidence_badge(s.get("confidence"))}">{html.escape(s.get("confidence", ""))}</span>',
         html.escape(s.get("tool", ""))]
        for s in syms[:200]
    ]
    return f'<p><strong>{len(syms)}</strong> dead symbols.</p>' + _table(
        ["Symbol", "File", "Line", "Kind", "Confidence", "Tool"],
        rows, numeric_cols=[2],
    )


def _html_architecture(p: dict) -> str:
    cfg_path = p.get("rules_config")
    violations = p.get("violations") or []
    summary = (
        f'<p><strong>Rules config:</strong> '
        + (f'<code>{html.escape(cfg_path)}</code>' if cfg_path else "<em>none detected</em>")
        + f' · <strong>Violations:</strong> {len(violations)}</p>'
    )
    if not violations:
        return summary
    rows = [
        [html.escape(v.get("rule_id", "")),
         f'<code>{html.escape(v.get("source", ""))}</code>',
         f'<code>{html.escape(v.get("target", ""))}</code>',
         html.escape(v.get("severity", ""))]
        for v in violations[:100]
    ]
    return summary + _table(["Rule", "Source", "Target", "Severity"], rows)


def _html_coverage(p: dict) -> str:
    overall = p.get("overall_pct")
    low = p.get("low_coverage_files") or []
    by_file = p.get("by_file") or {}
    overall_str = f"{overall:.1f}%" if isinstance(overall, (int, float)) else "n/a"
    return (
        f'<p><strong>Overall:</strong> {overall_str} · '
        f'<strong>Files with data:</strong> {len(by_file)} · '
        f'<strong>Below threshold:</strong> {len(low)} · '
        f'<strong>Source:</strong> <code>{html.escape(p.get("source", "none"))}</code></p>'
    )


_PHASE_HTML_RENDERERS: dict[str, Any] = {
    "1.1": _html_stack, "1.2": _html_capabilities, "1.3": _html_extensions,
    "1.4": _html_reuse, "1.5": _html_coupling, "1.6": _html_complexity,
    "1.7": _html_wrappers, "1.8": _html_conventions, "1.9": _html_tests,
    "1.10": _html_lints, "1.11": _html_history, "1.12": _html_duplication,
    "1.13": _html_deadcode, "1.14": _html_architecture, "1.15": _html_coverage,
}


# ─── Utilities ────────────────────────────────────────────────────────────


def _slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_-]+", "-", text).strip("-")
    return s or "root"


def _confidence_badge(confidence: str | None) -> str:
    return {
        "high": "blue",
        "medium": "amber",
        "low": "red",
    }.get((confidence or "").lower(), "gray")


def _md_to_html(text: str) -> str:
    """Minimal Markdown → HTML for the synthesis sections (plain text + a few inlines)."""
    if not text:
        return ""
    # Escape first, then unescape our markup
    s = html.escape(text)
    # Inline code
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    # Bold
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    # Newlines → <br>
    s = s.replace("\n", "<br>")
    return s


# ─── Re-render entry (called from probe.py --render) ──────────────────────


def render_markdown_only(cfg: OrchestratorConfig) -> Path | None:
    """Backwards-compat alias."""
    return render_markdown(cfg)
