#!/usr/bin/env python3
"""Aggregate attention-items for the founder's inbox.

Walks the project's state sources (train-runs, BLOCKERs, findings) and
returns a structured envelope. Founder-vocab translation is the SKILL.md's
job — this script returns raw data only.

Sources (see references/sources-of-truth.md):
- .architecture/{project}/train-runs/*.state.json  → paused work
- .architecture/{project}/work-packages/BLOCKER-*.md  → blocked tasks
- .security/{project}/findings/*.md  → review needed
- .security/{project}/findings-register.md  → review needed (fallback)

Usage:

    python3 aggregator.py --project NAME [--repo-root .] [--format markdown|json]
    python3 aggregator.py --project NAME --doctor    # source-existence check

Exit codes:
- 0 = success (regardless of inbox count)
- 1 = usage error
- 2 = filesystem error (project dir missing, etc.)
- 3 = doctor found missing sources outside may-be-empty allow-list
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


# ─── Data structures ────────────────────────────────────────────────


@dataclass
class AttentionItem:
    """One thing waiting for the founder."""

    category: str  # paused_work | review_needed | blocked_tasks | decisions_waiting
    operator_ref: str  # WP-AUTO-018, train_id, S-024, etc.
    source_path: str  # relative path to the source file
    summary: str  # one-line summary in whatever vocab the source uses
    severity: str = "normal"  # high | normal | low (drives ordering within category)
    extras: dict[str, Any] = field(default_factory=dict)  # category-specific data


@dataclass
class InboxEnvelope:
    project: str
    repo_root: str
    total_count: int
    categories: dict[str, list[AttentionItem]]
    errors: list[str]
    sources_unavailable: list[str]


# ─── Path resolution (mirrors sulis-execution conventions) ───────────


@dataclass
class Paths:
    repo_root: Path
    project: str

    @property
    def arch_root(self) -> Path:
        return self.repo_root / ".architecture" / self.project

    @property
    def wp_dir(self) -> Path:
        return self.arch_root / "work-packages"

    @property
    def train_runs_dir(self) -> Path:
        return self.arch_root / "train-runs"

    @property
    def security_dir(self) -> Path:
        return self.repo_root / ".security" / self.project

    @property
    def findings_dir(self) -> Path:
        return self.security_dir / "findings"

    @property
    def findings_register(self) -> Path:
        return self.security_dir / "findings-register.md"


# ─── Source readers ──────────────────────────────────────────────────


def read_paused_trains(paths: Paths, errors: list[str]) -> list[AttentionItem]:
    """Walk train-runs/*.state.json; emit AttentionItem for any in phase=paused
    or phase=verifying_gates."""
    items: list[AttentionItem] = []
    if not paths.train_runs_dir.is_dir():
        return items

    for state_file in sorted(paths.train_runs_dir.glob("*.state.json")):
        try:
            with state_file.open("r", encoding="utf-8") as fh:
                state = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{state_file.name}: {exc}")
            continue

        phase = state.get("phase", "")
        if phase not in ("paused", "verifying_gates"):
            continue

        train_id = state.get("train_id") or state_file.stem.replace(".state", "")
        pause_reason = state.get("pause_reason") or "no reason recorded"
        recovery_hint = state.get("recovery_hint") or ""

        items.append(
            AttentionItem(
                category="paused_work",
                operator_ref=train_id,
                source_path=str(state_file.relative_to(paths.repo_root)),
                summary=pause_reason,
                severity="normal",
                extras={
                    "phase": phase,
                    "recovery_hint": recovery_hint,
                    "wps": state.get("wps", []),
                    "started_at": state.get("started_at", ""),
                },
            )
        )

    return items


def read_blockers(paths: Paths, errors: list[str]) -> list[AttentionItem]:
    """Walk work-packages/BLOCKER-WP-*.md; emit AttentionItem for each."""
    items: list[AttentionItem] = []
    if not paths.wp_dir.is_dir():
        return items

    for blocker_file in sorted(paths.wp_dir.glob("BLOCKER-WP-*.md")):
        # WP ID from filename: BLOCKER-WP-AUTO-018.md → WP-AUTO-018
        match = re.match(r"^BLOCKER-(WP-[A-Z0-9-]+?)\.md$", blocker_file.name)
        if not match:
            errors.append(f"{blocker_file.name}: cannot parse WP ID")
            continue
        wp = match.group(1)

        # Reason: first non-heading paragraph
        try:
            text = blocker_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"{blocker_file.name}: {exc}")
            continue

        reason = _first_paragraph(text) or "no reason recorded"

        # WP slug for founder name (best-effort)
        wp_slug = _find_wp_slug(paths.wp_dir, wp)

        items.append(
            AttentionItem(
                category="blocked_tasks",
                operator_ref=wp,
                source_path=str(blocker_file.relative_to(paths.repo_root)),
                summary=reason,
                severity="normal",
                extras={"wp_slug": wp_slug},
            )
        )

    return items


def read_review_needed(paths: Paths, errors: list[str]) -> list[AttentionItem]:
    """Walk security/findings/*.md; emit AttentionItem for each not-yet-triaged."""
    items: list[AttentionItem] = []
    if not paths.findings_dir.is_dir():
        return items

    for finding_file in sorted(paths.findings_dir.glob("*.md")):
        try:
            text = finding_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"{finding_file.name}: {exc}")
            continue

        triage = _parse_field(text, "triage") or "pending"
        if triage.lower() not in ("pending", "needs-decision", ""):
            continue

        finding_id = _parse_field(text, "id") or finding_file.stem
        severity = _parse_field(text, "severity") or "normal"
        summary = _parse_field(text, "summary") or _first_paragraph(text) or "no summary"

        items.append(
            AttentionItem(
                category="review_needed",
                operator_ref=finding_id,
                source_path=str(finding_file.relative_to(paths.repo_root)),
                summary=summary,
                severity=severity.lower(),
            )
        )

    return items


# ─── Parsing helpers ─────────────────────────────────────────────────


def _first_paragraph(text: str) -> str:
    """Return the first non-heading, non-frontmatter paragraph (up to 240 chars)."""
    in_frontmatter = False
    paragraphs: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "---":
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter:
            continue
        if stripped.startswith("#"):
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        if not stripped:
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        current.append(stripped)
    if current:
        paragraphs.append(" ".join(current))

    for p in paragraphs:
        if p:
            return p[:240] + ("…" if len(p) > 240 else "")
    return ""


def _parse_field(text: str, field: str) -> str:
    """Parse a YAML-frontmatter scalar field. Returns empty string if not found."""
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 4)
    if end < 0:
        return ""
    fm = text[4:end]
    for line in fm.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            if key.strip().lower() == field.lower():
                return value.strip().strip('"').strip("'")
    return ""


def _find_wp_slug(wp_dir: Path, wp: str) -> str:
    """Find the slug from WP-AUTO-018-some-slug.md → 'some-slug'."""
    for candidate in wp_dir.glob(f"{wp}-*.md"):
        if candidate.name.startswith("BLOCKER-") or candidate.name.startswith("."):
            continue
        slug_part = candidate.stem[len(wp) + 1:]  # strip "WP-AUTO-018-"
        return slug_part
    return ""


# ─── Doctor ──────────────────────────────────────────────────────────


MAY_BE_EMPTY = {
    "train_runs_dir": "no train has run yet",
    "wp_dir": "no work packages drafted yet",
    "findings_dir": "no security review has run yet",
    "findings_register": "no findings register yet",
}


def doctor(paths: Paths) -> tuple[list[str], list[str]]:
    """Check source-path existence. Returns (problems, info)."""
    problems: list[str] = []
    info: list[str] = []

    if not paths.arch_root.is_dir():
        problems.append(
            f".architecture/{paths.project}/ does not exist — "
            f"project may be mis-named or not yet initialised"
        )
        return problems, info

    checks = [
        ("train_runs_dir", paths.train_runs_dir),
        ("wp_dir", paths.wp_dir),
        ("findings_dir", paths.findings_dir),
        ("findings_register", paths.findings_register),
    ]

    for key, path in checks:
        if path.exists():
            info.append(f"✓ {key}: {path.relative_to(paths.repo_root)}")
        elif key in MAY_BE_EMPTY:
            info.append(f"○ {key}: not present ({MAY_BE_EMPTY[key]})")
        else:
            problems.append(f"missing source: {key} at {path}")

    return problems, info


# ─── Output renderers ────────────────────────────────────────────────


def render_envelope_json(env: InboxEnvelope) -> str:
    payload = {
        "project": env.project,
        "repo_root": env.repo_root,
        "total_count": env.total_count,
        "categories": {
            k: [asdict(item) for item in v] for k, v in env.categories.items()
        },
        "errors": env.errors,
        "sources_unavailable": env.sources_unavailable,
    }
    return json.dumps(payload, indent=2)


def render_envelope_markdown(env: InboxEnvelope) -> str:
    out: list[str] = []
    out.append(f"# Inbox — {env.project}")
    out.append("")
    if env.total_count == 0:
        out.append("_Nothing waiting._")
        if env.sources_unavailable:
            out.append("")
            out.append("**Note:** some sources were not available:")
            for s in env.sources_unavailable:
                out.append(f"- {s}")
        return "\n".join(out)

    out.append(f"**Total:** {env.total_count} attention-item(s).")
    out.append("")
    out.append(
        "_This is the raw aggregator output. SKILL.md translates each item "
        "into founder English before presenting._"
    )
    out.append("")

    category_labels = {
        "paused_work": "Paused work",
        "review_needed": "Things to review",
        "blocked_tasks": "Blocked tasks",
        "decisions_waiting": "Decisions waiting on you",
    }

    for cat_key, cat_label in category_labels.items():
        items = env.categories.get(cat_key, [])
        if not items:
            continue
        out.append(f"## {cat_label} ({len(items)})")
        out.append("")
        for item in items:
            out.append(f"- **{item.operator_ref}** ({item.severity})")
            out.append(f"  - Summary: {item.summary}")
            out.append(f"  - Source: `{item.source_path}`")
            if item.extras:
                extras_str = ", ".join(
                    f"{k}={v}" for k, v in item.extras.items() if v
                )
                if extras_str:
                    out.append(f"  - Extras: {extras_str}")
        out.append("")

    if env.errors:
        out.append("## Errors during aggregation")
        out.append("")
        for e in env.errors:
            out.append(f"- {e}")
        out.append("")

    return "\n".join(out)


# ─── Main ────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate attention-items for the founder's inbox."
    )
    parser.add_argument(
        "--project",
        required=True,
        help="Project slug (resolves .architecture/<project>/ paths).",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repo root (defaults to cwd).",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="json",
        help="Output format. Default: json (intended for SKILL.md consumption).",
    )
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="Run source-existence check; do not aggregate.",
    )
    args = parser.parse_args()

    paths = Paths(repo_root=Path(args.repo_root).resolve(), project=args.project)

    if args.doctor:
        problems, info = doctor(paths)
        for line in info:
            print(line)
        if problems:
            print("\nPROBLEMS:")
            for p in problems:
                print(f"  - {p}")
            return 3
        print("\nAll sources OK (or may-be-empty per allow-list).")
        return 0

    if not paths.arch_root.is_dir():
        print(
            f"error: .architecture/{paths.project}/ does not exist. "
            f"Is the project name correct? Is .architecture/ initialised?",
            file=sys.stderr,
        )
        return 2

    errors: list[str] = []
    sources_unavailable: list[str] = []

    # Check each source-dir; track unavailable so the renderer can mention them
    if not paths.train_runs_dir.is_dir():
        sources_unavailable.append("train-runs/ (no trains have run yet)")
    if not paths.wp_dir.is_dir():
        sources_unavailable.append("work-packages/ (no WPs drafted yet)")
    if not paths.findings_dir.is_dir():
        sources_unavailable.append("findings/ (no security review yet)")

    categories: dict[str, list[AttentionItem]] = {
        "paused_work": read_paused_trains(paths, errors),
        "review_needed": read_review_needed(paths, errors),
        "blocked_tasks": read_blockers(paths, errors),
        "decisions_waiting": [],  # v1: not implemented
    }

    total = sum(len(items) for items in categories.values())

    env = InboxEnvelope(
        project=args.project,
        repo_root=str(paths.repo_root),
        total_count=total,
        categories=categories,
        errors=errors,
        sources_unavailable=sources_unavailable,
    )

    if args.format == "json":
        print(render_envelope_json(env))
    else:
        print(render_envelope_markdown(env))

    return 0


if __name__ == "__main__":
    sys.exit(main())
