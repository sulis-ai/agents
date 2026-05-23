#!/usr/bin/env python3
"""Inventory the marketplace for the Find phase of `sulis:add-skill`.

Deterministic-first half of the hybrid Find pattern: this script gathers
the raw inventory; Claude interprets the output.

Outputs a structured BRIEF_PACK in Markdown to stdout. Stderr carries
diagnostics. Exit code is 0 on success, 1 on usage error, 2 on
filesystem error.

Usage:

    python3 inventory.py \\
        --marketplace-root . \\
        --target-plugin sea \\
        --target-skill code-hygiene \\
        --proposed-description "Use when the user wants a stranger-reader audit of naming, module cohesion, and legibility across a module or directory." \\
        --proposed-vocabulary "stranger-reader,legibility,module-cohesion"
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


# ─── Data structures ────────────────────────────────────────────────


@dataclass
class SkillInfo:
    plugin: str
    name: str
    description: str
    path: Path
    gotchas: list[str] = field(default_factory=list)
    vocabulary: list[str] = field(default_factory=list)


@dataclass
class ReferenceInfo:
    plugin: str
    relative_path: str
    title: str
    size_bytes: int


# ─── Parsers ────────────────────────────────────────────────────────


def parse_frontmatter(skill_md_path: Path) -> tuple[str, str]:
    """Extract `name:` and `description:` from SKILL.md frontmatter.

    Returns (name, description). Falls back to empty strings if absent.
    Handles multi-line descriptions via YAML `>` folded scalar.
    """
    try:
        text = skill_md_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"warn: could not read {skill_md_path}: {exc}", file=sys.stderr)
        return ("", "")

    if not text.startswith("---"):
        return ("", "")

    end = text.find("\n---", 4)
    if end < 0:
        return ("", "")
    fm = text[4:end]

    name = ""
    description = ""
    lines = fm.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("name:"):
            name = line[5:].strip()
        elif line.startswith("description:"):
            rest = line[12:].strip()
            if rest in (">", ">-", "|", "|-"):
                # Folded/literal scalar — gather continuation lines
                parts: list[str] = []
                i += 1
                while i < len(lines) and lines[i].startswith(("  ", "\t")):
                    parts.append(lines[i].strip())
                    i += 1
                description = " ".join(parts)
                continue
            description = rest
        i += 1

    return (name, description)


def extract_gotchas(skill_md_path: Path) -> list[str]:
    """Pull bullet items from a `## Gotchas` section, if present."""
    try:
        text = skill_md_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    # Find the Gotchas heading (## Gotchas or # Gotchas)
    match = re.search(r"^#{1,3}\s+Gotchas\s*$", text, re.MULTILINE | re.IGNORECASE)
    if not match:
        return []

    # Slice from end of heading to next heading at same-or-higher level
    start = match.end()
    rest = text[start:]
    next_heading = re.search(r"^#{1,3}\s+", rest, re.MULTILINE)
    section = rest[: next_heading.start()] if next_heading else rest

    gotchas: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith(("- ", "* ")):
            item = stripped[2:].strip()
            # Strip leading bold/italic markers (e.g., "**Title**")
            item = re.sub(r"^\*+", "", item).strip()
            # Truncate at 220 chars with ellipsis if longer
            if len(item) > 220:
                item = item[:220].rstrip() + "…"
            gotchas.append(item)

    return gotchas


def extract_vocabulary(skill_md_path: Path) -> list[str]:
    """Pull term names from a `## Vocabulary` section, if present."""
    try:
        text = skill_md_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    match = re.search(r"^#{1,3}\s+Vocabulary\s*$", text, re.MULTILINE | re.IGNORECASE)
    if not match:
        return []

    start = match.end()
    rest = text[start:]
    next_heading = re.search(r"^#{1,3}\s+", rest, re.MULTILINE)
    section = rest[: next_heading.start()] if next_heading else rest

    terms: list[str] = []
    # Match `- **term**` or `- *term*` or `- term —` patterns
    for match in re.finditer(
        r"^[-*]\s+(?:\*\*([^*]+)\*\*|\*([^*]+)\*|([^\s—-]+(?:\s[^\s—-]+){0,2}))",
        section,
        re.MULTILINE,
    ):
        term = next(g for g in match.groups() if g)
        terms.append(term.strip().lower())

    return terms


# ─── Inventory walkers ──────────────────────────────────────────────


def walk_skills(marketplace_root: Path) -> list[SkillInfo]:
    """Find every SKILL.md in plugins/*/skills/*/."""
    skills: list[SkillInfo] = []
    plugins_dir = marketplace_root / "plugins"
    if not plugins_dir.is_dir():
        print(f"error: {plugins_dir} not a directory", file=sys.stderr)
        return skills

    for plugin_dir in sorted(plugins_dir.iterdir()):
        if not plugin_dir.is_dir():
            continue
        skills_dir = plugin_dir / "skills"
        if not skills_dir.is_dir():
            continue
        for skill_dir in sorted(skills_dir.iterdir()):
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.is_file():
                continue
            name, description = parse_frontmatter(skill_md)
            skills.append(
                SkillInfo(
                    plugin=plugin_dir.name,
                    name=name or skill_dir.name,
                    description=description,
                    path=skill_md,
                    gotchas=extract_gotchas(skill_md),
                    vocabulary=extract_vocabulary(skill_md),
                )
            )

    return skills


def walk_references(marketplace_root: Path) -> list[ReferenceInfo]:
    """Find every references/*.md across plugins (skill-level + plugin-level)."""
    refs: list[ReferenceInfo] = []
    plugins_dir = marketplace_root / "plugins"
    if not plugins_dir.is_dir():
        return refs

    for plugin_dir in sorted(plugins_dir.iterdir()):
        if not plugin_dir.is_dir():
            continue
        for ref_md in sorted(plugin_dir.rglob("references/*.md")):
            try:
                rel = ref_md.relative_to(plugin_dir)
                size = ref_md.stat().st_size
                title = ""
                with ref_md.open("r", encoding="utf-8") as fh:
                    for line in fh:
                        if line.startswith("# "):
                            title = line[2:].strip()
                            break
                refs.append(
                    ReferenceInfo(
                        plugin=plugin_dir.name,
                        relative_path=str(rel),
                        title=title or rel.stem.replace("-", " ").title(),
                        size_bytes=size,
                    )
                )
            except OSError as exc:
                print(f"warn: could not stat {ref_md}: {exc}", file=sys.stderr)

    return refs


# ─── Collision detection ────────────────────────────────────────────


def detect_vocabulary_collisions(
    proposed_vocab: list[str], existing: list[SkillInfo]
) -> list[tuple[str, list[str]]]:
    """For each proposed term, list skills that use the same term."""
    proposed_set = {t.strip().lower() for t in proposed_vocab if t.strip()}
    collisions: list[tuple[str, list[str]]] = []

    for term in sorted(proposed_set):
        matchers: list[str] = []
        for skill in existing:
            # Match against vocabulary section
            if term in skill.vocabulary:
                matchers.append(f"{skill.plugin}:{skill.name} (vocabulary)")
            # Match against description (case-insensitive whole word)
            elif re.search(rf"\b{re.escape(term)}\b", skill.description, re.IGNORECASE):
                matchers.append(f"{skill.plugin}:{skill.name} (description)")
        if matchers:
            collisions.append((term, matchers))

    return collisions


def detect_description_overlap(
    proposed_desc: str, existing: list[SkillInfo], top_n: int = 5
) -> list[tuple[str, int]]:
    """Heuristic overlap: shared non-stopword tokens between proposed
    description and each existing skill description.

    Returns top-N skills by overlap count.
    """
    stop = {
        "the", "a", "an", "use", "when", "user", "wants", "to", "for",
        "of", "and", "or", "with", "in", "on", "at", "by", "from", "is",
        "are", "be", "this", "that", "it", "as", "if", "then", "but",
        "into", "out", "up", "down", "via", "through", "across", "skill",
    }

    def tokens(text: str) -> set[str]:
        return {
            t.lower()
            for t in re.findall(r"[a-zA-Z]{4,}", text.lower())
            if t.lower() not in stop
        }

    proposed_tokens = tokens(proposed_desc)
    if not proposed_tokens:
        return []

    scored: list[tuple[str, int]] = []
    for skill in existing:
        existing_tokens = tokens(skill.description)
        overlap = len(proposed_tokens & existing_tokens)
        if overlap > 0:
            scored.append((f"{skill.plugin}:{skill.name}", overlap))

    scored.sort(key=lambda x: -x[1])
    return scored[:top_n]


# ─── Output renderer ────────────────────────────────────────────────


def render_brief_pack(
    args: argparse.Namespace,
    skills: list[SkillInfo],
    references: list[ReferenceInfo],
    vocab_collisions: list[tuple[str, list[str]]],
    desc_overlap: list[tuple[str, int]],
) -> str:
    out: list[str] = []
    out.append(f"# BRIEF_PACK — {args.target_plugin}:{args.target_skill}")
    out.append("")
    out.append(f"Generated by `sulis:add-skill/scripts/inventory.py`")
    out.append(f"Marketplace root: `{args.marketplace_root}`")
    out.append("")
    out.append(f"**Proposed trigger condition:** {args.proposed_description or '(none provided)'}")
    out.append("")
    out.append(
        f"**Proposed vocabulary:** "
        f"{', '.join(args.proposed_vocabulary or []) or '(none provided)'}"
    )
    out.append("")

    # 1. Existing skills
    out.append("## 1. Existing skills (jargon + scope collision check)")
    out.append("")
    out.append(f"Total: {len(skills)} skills across {len({s.plugin for s in skills})} plugins.")
    out.append("")
    by_plugin: dict[str, list[SkillInfo]] = {}
    for s in skills:
        by_plugin.setdefault(s.plugin, []).append(s)
    for plugin in sorted(by_plugin):
        out.append(f"### {plugin}")
        out.append("")
        for s in by_plugin[plugin]:
            desc = s.description[:140] + ("…" if len(s.description) > 140 else "")
            out.append(f"- **{s.name}** — {desc}")
        out.append("")

    # 2. Description overlap
    out.append("## 2. Description overlap (potential scope collision)")
    out.append("")
    out.append("Top skills with shared non-stopword tokens in description.")
    out.append("Review each: is this a real overlap (same scope, different skills)")
    out.append("or coincidental (shared domain vocabulary)?")
    out.append("")
    if not desc_overlap:
        out.append("_No description provided, or no overlap detected._")
    else:
        out.append("| Skill | Overlap tokens |")
        out.append("|---|---|")
        for name, n in desc_overlap:
            out.append(f"| {name} | {n} |")
    out.append("")

    # 3. Vocabulary collisions
    out.append("## 3. Vocabulary collisions")
    out.append("")
    out.append("Proposed terms that appear in another skill's vocabulary section")
    out.append("or description. Resolve each: rename, scope-disambiguate, or waive.")
    out.append("")
    if not vocab_collisions:
        out.append("_No proposed vocabulary, or no collisions detected._")
    else:
        for term, matchers in vocab_collisions:
            out.append(f"### `{term}`")
            for m in matchers:
                out.append(f"- {m}")
            out.append("")

    # 4. References (knowledge-source check)
    out.append("## 4. Existing references (knowledge sources to wrap, not restate)")
    out.append("")
    out.append(f"Total: {len(references)} reference files across the marketplace.")
    out.append("")
    refs_by_plugin: dict[str, list[ReferenceInfo]] = {}
    for r in references:
        refs_by_plugin.setdefault(r.plugin, []).append(r)
    for plugin in sorted(refs_by_plugin):
        out.append(f"### {plugin}")
        out.append("")
        for r in refs_by_plugin[plugin]:
            kb = r.size_bytes // 1024
            out.append(f"- `{r.relative_path}` — {r.title} ({kb}K)")
        out.append("")

    # 5. Prior-art gotchas (target plugin domain)
    out.append("## 5. Prior-art gotchas in target plugin")
    out.append("")
    out.append(
        f"Gotchas from existing skills in `{args.target_plugin}` plugin. Use these"
    )
    out.append("as source material for the new skill's gotchas section (Gate 2).")
    out.append("")
    target_skills = [s for s in skills if s.plugin == args.target_plugin]
    if not target_skills:
        out.append(
            f"_Plugin `{args.target_plugin}` does not exist yet, "
            f"or has no skills with gotchas. No prior art available._"
        )
    else:
        any_gotchas = False
        for s in target_skills:
            if s.gotchas:
                any_gotchas = True
                out.append(f"### {s.name}")
                out.append("")
                for g in s.gotchas[:15]:
                    out.append(f"- {g}")
                out.append("")
        if not any_gotchas:
            out.append(f"_No gotchas found in `{args.target_plugin}` skills._")

    # 6. Target plugin layout
    out.append("## 6. Target plugin layout")
    out.append("")
    target_plugin_dir = Path(args.marketplace_root) / "plugins" / args.target_plugin
    if target_plugin_dir.is_dir():
        out.append(f"Plugin `{args.target_plugin}` exists at `{target_plugin_dir}`.")
        out.append("")
        out.append("New skill goes at:")
        out.append("")
        out.append(f"    plugins/{args.target_plugin}/skills/{args.target_skill}/")
        out.append("        SKILL.md")
        out.append("        references/   (optional)")
        out.append("        scripts/      (optional)")
        out.append("        templates/    (optional)")
    else:
        out.append(
            f"Plugin `{args.target_plugin}` does NOT exist yet. Decide before Gate 2:"
        )
        out.append("")
        out.append(f"- Create new plugin `{args.target_plugin}` (requires plugin.json + marketplace.json entry), OR")
        out.append("- Pick an existing plugin from section 1 as the home.")

    out.append("")
    out.append("---")
    out.append("")
    out.append("**Next step:** Claude interprets this BRIEF_PACK. Are flagged")
    out.append("collisions real or coincidental? Does an existing skill already")
    out.append("cover this? Is a reference doc better wrapped than restated?")
    out.append("Resolve before moving to Gate 2 (Scope Lock).")

    return "\n".join(out)


# ─── Main ───────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inventory the marketplace for sulis:add-skill Gate 1 (Find)."
    )
    parser.add_argument(
        "--marketplace-root",
        required=True,
        help="Path to the marketplace repo root (contains plugins/ directory).",
    )
    parser.add_argument(
        "--target-plugin",
        required=True,
        help="Plugin name where the new skill will live (existing or new).",
    )
    parser.add_argument(
        "--target-skill",
        required=True,
        help="Proposed skill name (kebab-case).",
    )
    parser.add_argument(
        "--proposed-description",
        default="",
        help="The proposed `description:` field (one-line trigger condition).",
    )
    parser.add_argument(
        "--proposed-vocabulary",
        type=lambda s: [t.strip() for t in s.split(",") if t.strip()],
        default=[],
        help="Comma-separated proposed vocabulary terms.",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format. Default: markdown (BRIEF_PACK).",
    )
    args = parser.parse_args()

    marketplace_root = Path(args.marketplace_root).resolve()
    if not marketplace_root.is_dir():
        print(f"error: marketplace root not a directory: {marketplace_root}", file=sys.stderr)
        return 2

    skills = walk_skills(marketplace_root)
    references = walk_references(marketplace_root)
    vocab_collisions = detect_vocabulary_collisions(args.proposed_vocabulary, skills)
    desc_overlap = detect_description_overlap(args.proposed_description, skills)

    if args.format == "json":
        payload = {
            "target_plugin": args.target_plugin,
            "target_skill": args.target_skill,
            "proposed_description": args.proposed_description,
            "proposed_vocabulary": args.proposed_vocabulary,
            "skills": [
                {
                    "plugin": s.plugin,
                    "name": s.name,
                    "description": s.description,
                    "gotchas_count": len(s.gotchas),
                    "vocabulary": s.vocabulary,
                }
                for s in skills
            ],
            "references_count": len(references),
            "vocabulary_collisions": [
                {"term": term, "matchers": matchers}
                for term, matchers in vocab_collisions
            ],
            "description_overlap": [
                {"skill": name, "overlap_tokens": n} for name, n in desc_overlap
            ],
        }
        print(json.dumps(payload, indent=2))
    else:
        print(
            render_brief_pack(args, skills, references, vocab_collisions, desc_overlap)
        )

    print(
        f"inventory: scanned {len(skills)} skills, {len(references)} references; "
        f"{len(vocab_collisions)} vocab collision(s), "
        f"{len(desc_overlap)} description overlap(s)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
