#!/usr/bin/env python3
"""Inventory the marketplace for the Find phase of `sulis:add-agent`.

Deterministic-first half of the hybrid Find pattern: this script gathers
the raw agent inventory; Claude interprets the output.

Outputs a structured BRIEF_PACK in Markdown to stdout. Stderr carries
diagnostics. Exit code is 0 on success, 1 on usage error, 2 on
filesystem error.

Usage:

    python3 inventory.py \\
        --marketplace-root . \\
        --target-plugin sulis \\
        --target-agent change-classifier \\
        --proposed-description "Classifies a change's depth mode (lite/standard/deep) based on intent + repo signals." \\
        --proposed-tools "Read" \\
        --proposed-vocabulary "depth-mode,classifier,repo-signal"
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


# ─── Data structures ────────────────────────────────────────────────


@dataclass
class AgentInfo:
    plugin: str
    name: str
    description: str
    path: Path
    user_invocable: str = ""  # "true" / "false" / "" (unspecified)
    model: str = ""  # "haiku" / "sonnet" / "opus" / "" (inherit)
    tools: str = ""  # comma-separated or "*" or "" (inherit)
    has_register_block: bool = False  # founder-facing indicator
    has_standards_block: bool = False  # v0.1.0+ standards-grounded
    body_word_count: int = 0


# ─── Parsers ────────────────────────────────────────────────────────


def parse_agent_file(agent_md_path: Path) -> AgentInfo:
    """Extract agent metadata from an agent.md file."""
    try:
        text = agent_md_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"warn: could not read {agent_md_path}: {exc}", file=sys.stderr)
        return AgentInfo(
            plugin=agent_md_path.parent.parent.name,
            name=agent_md_path.stem,
            description="",
            path=agent_md_path,
        )

    plugin = agent_md_path.parent.parent.name

    # Extract frontmatter
    if not text.startswith("---"):
        return AgentInfo(
            plugin=plugin,
            name=agent_md_path.stem,
            description="",
            path=agent_md_path,
            body_word_count=len(text.split()),
        )

    end = text.find("\n---", 4)
    if end < 0:
        return AgentInfo(
            plugin=plugin,
            name=agent_md_path.stem,
            description="",
            path=agent_md_path,
            body_word_count=len(text.split()),
        )

    fm = text[4:end]
    body = text[end + 4:]

    name = _extract_field(fm, "name")
    description = _extract_multiline_field(fm, "description")
    user_invocable = _extract_field(fm, "user_invocable")
    model = _extract_field(fm, "model")
    tools = _extract_field(fm, "tools")

    has_register_block = re.search(r"^register:", fm, re.MULTILINE) is not None
    has_standards_block = re.search(r"^standards:", fm, re.MULTILINE) is not None

    body_word_count = len(body.split())

    return AgentInfo(
        plugin=plugin,
        name=name or agent_md_path.stem,
        description=description,
        path=agent_md_path,
        user_invocable=user_invocable,
        model=model,
        tools=tools,
        has_register_block=has_register_block,
        has_standards_block=has_standards_block,
        body_word_count=body_word_count,
    )


def _extract_field(fm: str, field_name: str) -> str:
    """Extract a single-line frontmatter field."""
    pattern = rf"^{re.escape(field_name)}:\s*(.+?)$"
    match = re.search(pattern, fm, re.MULTILINE)
    if not match:
        return ""
    value = match.group(1).strip()
    # Strip quotes if any
    if value.startswith(("'", '"')) and value.endswith(("'", '"')):
        value = value[1:-1]
    return value


def _extract_multiline_field(fm: str, field_name: str) -> str:
    """Extract a frontmatter field that may be a YAML folded scalar."""
    lines = fm.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith(f"{field_name}:"):
            rest = line[len(field_name) + 1:].strip()
            if rest in (">", ">-", "|", "|-"):
                # Folded/literal scalar — gather continuation lines
                parts: list[str] = []
                i += 1
                while i < len(lines) and (lines[i].startswith("  ") or lines[i].startswith("\t")):
                    parts.append(lines[i].strip())
                    i += 1
                return " ".join(parts)
            return rest
        i += 1
    return ""


def collect_agents(marketplace_root: Path) -> list[AgentInfo]:
    """Walk every plugins/*/agents/*.md and parse."""
    agents: list[AgentInfo] = []
    plugins_dir = marketplace_root / "plugins"
    if not plugins_dir.is_dir():
        return agents

    for plugin_dir in sorted(plugins_dir.iterdir()):
        if not plugin_dir.is_dir():
            continue
        agents_dir = plugin_dir / "agents"
        if not agents_dir.is_dir():
            continue
        for agent_md in sorted(agents_dir.glob("*.md")):
            # Skip VERIFICATION_REPORT.md sibling files
            if "VERIFICATION_REPORT" in agent_md.name:
                continue
            agents.append(parse_agent_file(agent_md))

    return agents


# ─── Collision + overlap analyses ────────────────────────────────────


def check_name_collision(proposed_name: str, agents: list[AgentInfo]) -> list[str]:
    """Return list of collision warnings (empty if no collisions)."""
    warnings: list[str] = []
    for a in agents:
        if a.name == proposed_name:
            warnings.append(
                f"DIRECT COLLISION: agent named `{proposed_name}` already exists at `{a.path}` (plugin: {a.plugin})"
            )
        elif _kebab_similarity(a.name, proposed_name) >= 0.8:
            warnings.append(
                f"NEAR COLLISION: existing agent `{a.name}` (plugin: {a.plugin}) is similar to proposed `{proposed_name}`"
            )
    return warnings


def _kebab_similarity(a: str, b: str) -> float:
    """Crude similarity score: shared tokens / total tokens."""
    a_tokens = set(a.split("-"))
    b_tokens = set(b.split("-"))
    if not a_tokens or not b_tokens:
        return 0.0
    shared = a_tokens & b_tokens
    total = a_tokens | b_tokens
    return len(shared) / len(total)


def check_description_overlap(proposed_description: str, agents: list[AgentInfo]) -> list[tuple[AgentInfo, float]]:
    """Return list of (agent, overlap_score) sorted by descending overlap. Top 5."""
    if not proposed_description:
        return []

    proposed_tokens = _tokenize(proposed_description)
    if not proposed_tokens:
        return []

    scored: list[tuple[AgentInfo, float]] = []
    for a in agents:
        if not a.description:
            continue
        a_tokens = _tokenize(a.description)
        if not a_tokens:
            continue
        shared = proposed_tokens & a_tokens
        # Jaccard similarity, with a small bonus for high-information shared words
        overlap = len(shared) / len(proposed_tokens | a_tokens)
        if overlap >= 0.1:  # only surface meaningful overlaps
            scored.append((a, overlap))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:5]


def _tokenize(text: str) -> set[str]:
    """Lowercase, keep only word characters, return set of tokens."""
    return {
        token.lower()
        for token in re.findall(r"\b[a-zA-Z][a-zA-Z0-9_-]+\b", text)
        if len(token) > 2  # skip short stopwords
    }


def check_tool_overlap(proposed_tools: str, agents: list[AgentInfo]) -> list[tuple[AgentInfo, set[str]]]:
    """Return list of agents sharing tools with the proposed agent."""
    if not proposed_tools or proposed_tools == "*":
        return []

    proposed_set = _parse_tools(proposed_tools)
    matches: list[tuple[AgentInfo, set[str]]] = []
    for a in agents:
        if not a.tools or a.tools == "*":
            continue
        a_set = _parse_tools(a.tools)
        shared = proposed_set & a_set
        if len(shared) >= 2:  # meaningful overlap = 2+ shared tools
            matches.append((a, shared))
    return matches


def _parse_tools(tools_str: str) -> set[str]:
    """Parse a tools declaration into a set."""
    # Handle [Read, Edit, Bash] or "Read, Edit, Bash" or "*"
    cleaned = tools_str.strip().strip("[]")
    return {t.strip() for t in cleaned.split(",") if t.strip()}


# ─── BRIEF_PACK rendering ────────────────────────────────────────────


def render_brief_pack(
    target_plugin: str,
    target_agent: str,
    proposed_description: str,
    proposed_tools: str,
    proposed_vocabulary: str,
    agents: list[AgentInfo],
    name_warnings: list[str],
    description_overlaps: list[tuple[AgentInfo, float]],
    tool_overlaps: list[tuple[AgentInfo, set[str]]],
) -> str:
    """Render the BRIEF_PACK as Markdown."""
    out: list[str] = []
    out.append(f"# BRIEF_PACK — `add-agent` for `{target_plugin}/{target_agent}`")
    out.append("")
    out.append("Generated by `plugins/sulis/skills/add-agent/scripts/inventory.py`. Output is for Claude to interpret per BI / SI / CC at Gate 1.")
    out.append("")
    out.append(f"**Proposed agent:** `{target_plugin}/agents/{target_agent}.md`")
    out.append(f"**Proposed description:** {proposed_description or '(none provided)'}")
    out.append(f"**Proposed tools:** {proposed_tools or '(inherit)'}")
    out.append(f"**Proposed vocabulary:** {proposed_vocabulary or '(none provided)'}")
    out.append("")

    # ── Section 1: Existing agent inventory ────────────────────────
    out.append("## 1. Existing agent inventory")
    out.append("")
    if not agents:
        out.append("_No agents found in the marketplace._")
        out.append("")
    else:
        out.append(f"**{len(agents)} agents across {len({a.plugin for a in agents})} plugins.**")
        out.append("")
        out.append("| Plugin | Agent | Description (first 150 chars) | Standards | Register | Tools | Body words |")
        out.append("|---|---|---|---|---|---|---|")
        for a in agents:
            desc = (a.description[:150] + "…") if len(a.description) > 150 else a.description
            desc = desc.replace("|", "\\|").replace("\n", " ")
            standards_flag = "yes" if a.has_standards_block else "no"
            register_flag = "yes" if a.has_register_block else "no"
            tools_short = a.tools[:30] if a.tools else "(inherit)"
            out.append(
                f"| `{a.plugin}` | `{a.name}` | {desc} | {standards_flag} | {register_flag} | `{tools_short}` | {a.body_word_count} |"
            )
        out.append("")

    # ── Section 2: Name collision check ────────────────────────────
    out.append("## 2. Name collision check")
    out.append("")
    if not name_warnings:
        out.append(f"_No collisions for `{target_agent}`._")
        out.append("")
    else:
        for w in name_warnings:
            out.append(f"- ⚠️ {w}")
        out.append("")

    # ── Section 3: Description overlap analysis ────────────────────
    out.append("## 3. Description overlap analysis")
    out.append("")
    if not description_overlaps:
        out.append("_No meaningful description overlaps with existing agents._")
        out.append("")
    else:
        out.append("Top overlaps (Jaccard similarity ≥ 0.1):")
        out.append("")
        out.append("| Existing agent | Overlap | Existing description |")
        out.append("|---|---|---|")
        for a, score in description_overlaps:
            desc_short = (a.description[:120] + "…") if len(a.description) > 120 else a.description
            desc_short = desc_short.replace("|", "\\|").replace("\n", " ")
            out.append(f"| `{a.plugin}/{a.name}` | {score:.2f} | {desc_short} |")
        out.append("")
        out.append("**For Claude:** review each overlap. High overlap (≥ 0.3) likely indicates duplicate functionality — consider whether the proposed agent should be merged with the existing one, or whether the descriptions need disambiguation to avoid dispatch routing conflicts.")
        out.append("")

    # ── Section 4: Tool overlap analysis ───────────────────────────
    out.append("## 4. Tool overlap analysis")
    out.append("")
    if not tool_overlaps:
        out.append("_No agents with significant tool overlap (≥ 2 shared declared tools)._")
        out.append("")
    else:
        out.append("| Existing agent | Shared tools |")
        out.append("|---|---|")
        for a, shared in tool_overlaps:
            shared_str = ", ".join(sorted(shared))
            out.append(f"| `{a.plugin}/{a.name}` | {shared_str} |")
        out.append("")
        out.append("**For Claude:** tool overlap is a signal, not a verdict. Agents with similar tool sets may be doing similar work (duplication) OR very different work that happens to use the same primitives (legitimate). Use the description overlap (Section 3) as the deciding factor.")
        out.append("")

    # ── Section 5: Standards inventory ─────────────────────────────
    out.append("## 5. Standards inventory")
    out.append("")
    out.append("The eight cross-cutting standards to cite per audience:")
    out.append("")
    out.append("### Methodology tier (all agents)")
    out.append("")
    out.append("- `plugins/sulis/references/standards/CRITICAL_THINKING_STANDARD.md`")
    out.append("- `plugins/sulis/references/standards/DECOMPOSITION_PROCEDURE.md`")
    out.append("- `plugins/sulis/references/standards/SPIRAL_TEMPLATES.md`")
    out.append("- `plugins/sulis/references/standards/STANDARDS_RUBRIC.md`")
    out.append("- `plugins/sulis/references/standards/REFERENTIAL_INTEGRITY_STANDARD.md`")
    out.append("- `plugins/sulis/references/standards/WORK_PACKAGE_STANDARD.md` (if agent produces or consumes WPs)")
    out.append("")
    out.append("### Founder-communication tier (founder-facing or both only)")
    out.append("")
    out.append("- `plugins/sulis/references/standards/COACHING_STANDARD.md` — coaching delivery framing")
    out.append("- `plugins/sulis/references/standards/TONE_STANDARD.md` — vocabulary + voice")
    out.append("- `plugins/sulis/references/founder-facing-conventions.md` — sulis-layer apply rules + Rule 6 dual register")
    out.append("")

    # ── Section 6: Decision prompts for Claude ─────────────────────
    out.append("## 6. Decision prompts (apply BI / SI / CC at Gate 1)")
    out.append("")
    out.append("Before locking the agent at Gate 2, answer:")
    out.append("")
    out.append("1. **Could this be a skill instead?** (BI counter-search) Skills are lighter than agents — they don't carry their own conversational context or distinct role. If the work fits in a single skill invocation without needing its own persistent role, prefer `add-skill`.")
    out.append("2. **What's the dispatch trigger?** (CC) The `description:` is the load-bearing contract. Write it as a trigger condition the parent agent can match on, not a summary of internals.")
    out.append("3. **What audience?** founder-facing / operator-facing / both / agent-internal. Drives the standards citation requirement.")
    out.append("4. **What primitives does the agent own?** (PG-01..04 + PD-01..06) Decompose the agent's scope. Apply the independence test. Terminate when further splitting wouldn't change the next action.")
    out.append("5. **What tools? What model?** Per principle of least privilege + cost-and-latency profile.")
    out.append("6. **Register?** Founder-facing or both → declare both modes + technical-mode shape. Operator-facing or agent-internal → declare single register.")
    out.append("")

    return "\n".join(out)


# ─── Main ────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--marketplace-root", default=".", help="Path to marketplace root (default: cwd)")
    parser.add_argument("--target-plugin", required=True, help="Plugin home for the proposed agent (e.g., sulis)")
    parser.add_argument("--target-agent", required=True, help="Proposed agent name (kebab-case)")
    parser.add_argument("--proposed-description", default="", help="Proposed description (dispatch trigger)")
    parser.add_argument("--proposed-tools", default="", help="Proposed tools list (comma-separated or *)")
    parser.add_argument("--proposed-vocabulary", default="", help="Comma-separated terms the agent will introduce")

    args = parser.parse_args()

    marketplace_root = Path(args.marketplace_root).resolve()
    if not marketplace_root.is_dir():
        print(f"error: marketplace-root not a directory: {marketplace_root}", file=sys.stderr)
        return 2

    print(f"info: scanning {marketplace_root}/plugins/*/agents/", file=sys.stderr)
    agents = collect_agents(marketplace_root)
    print(f"info: found {len(agents)} agents across {len({a.plugin for a in agents})} plugins", file=sys.stderr)

    name_warnings = check_name_collision(args.target_agent, agents)
    description_overlaps = check_description_overlap(args.proposed_description, agents)
    tool_overlaps = check_tool_overlap(args.proposed_tools, agents)

    brief_pack = render_brief_pack(
        target_plugin=args.target_plugin,
        target_agent=args.target_agent,
        proposed_description=args.proposed_description,
        proposed_tools=args.proposed_tools,
        proposed_vocabulary=args.proposed_vocabulary,
        agents=agents,
        name_warnings=name_warnings,
        description_overlaps=description_overlaps,
        tool_overlaps=tool_overlaps,
    )

    print(brief_pack)
    return 0


if __name__ == "__main__":
    sys.exit(main())
