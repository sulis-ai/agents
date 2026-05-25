#!/usr/bin/env python3
"""Find every reference to plugins/{source}/ outside the source plugin itself.

Repo-wide grep for paths citing the source plugin + a separate sweep for
`subagent_type` references to the source plugin's agents. Emits a Markdown
report to stdout, grouped by file.

Usage:
  python3 plugins/sulis/skills/consolidate-into-sulis/scripts/find_external_refs.py \\
    --marketplace-root . \\
    --source-plugin sulis-context \\
    --agent-names context-cartographer
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


def run_git_grep(marketplace_root: Path, pattern: str, exclude: str | None = None) -> list[str]:
    """Run git grep -n; return list of lines. Falls back to plain grep if git missing."""
    args = ["git", "grep", "-nE", pattern]
    if exclude:
        args.extend(["--", ".", f":!{exclude}"])
    try:
        proc = subprocess.run(
            args,
            cwd=marketplace_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode in (0, 1):
            return proc.stdout.splitlines()
    except FileNotFoundError:
        pass

    # Fallback to plain grep -rnE
    args_fallback = ["grep", "-rnE", pattern, "."]
    if exclude:
        args_fallback = ["grep", "-rnE", "--exclude-dir", exclude.lstrip("/"), pattern, "."]
    proc = subprocess.run(
        args_fallback,
        cwd=marketplace_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode in (0, 1):
        return proc.stdout.splitlines()
    return []


def parse_grep_line(line: str) -> tuple[str, int, str] | None:
    """Parse a single grep -n line: file:lineno:content."""
    m = re.match(r"^([^:]+):(\d+):(.*)$", line)
    if not m:
        return None
    file_path, lineno, content = m.groups()
    return file_path, int(lineno), content.strip()


def find_path_refs(marketplace_root: Path, source_plugin: str) -> list[tuple[str, int, str]]:
    """Find every external reference to the source plugin.

    Catches THREE patterns (v0.1.1 — added slash-command pattern after the
    sulis-context → sulis consolidation surfaced 13 missed refs):

    - Absolute: plugins/{source}/  (cited from CLAUDE.md, root README, etc.)
    - Relative: (../)+{source}/    (cited from related_skills: blocks in other
      plugins' SKILL.md / agent.md, README cross-links, etc.)
    - Slash command: /{source}:{name}  (cited from agent bodies, skill
      bodies, references, .architecture/ TDDs — wherever the founder-visible
      slash-command form is invoked or documented)

    Excludes the source plugin's own directory so we don't surface its internal
    self-references.
    """
    exclude = f"plugins/{source_plugin}/"
    src_escaped = re.escape(source_plugin)

    # Absolute marketplace-rooted paths
    abs_pattern = f"plugins/{src_escaped}/"
    abs_lines = run_git_grep(marketplace_root, abs_pattern, exclude)

    # Relative paths: one-or-more "../" followed by the source plugin name + slash
    # ERE word boundary not portable across git-grep/grep variants; use the
    # slash-suffix as the right boundary and the "../" prefix as the left.
    rel_pattern = f"(\\.\\./)+{src_escaped}/"
    rel_lines = run_git_grep(marketplace_root, rel_pattern, exclude)

    # Slash-command pattern: /{source}:{name}
    # ERE doesn't have lookahead; we use [a-zA-Z] as the right boundary
    # (slash-command names are kebab-case identifiers).
    slash_pattern = f"/{src_escaped}:[a-zA-Z]"
    slash_lines = run_git_grep(marketplace_root, slash_pattern, exclude)

    # Merge + de-dup by (file, lineno) so a line matching multiple patterns
    # isn't reported more than once.
    seen: set[tuple[str, int]] = set()
    results: list[tuple[str, int, str]] = []
    for line in abs_lines + rel_lines + slash_lines:
        parsed = parse_grep_line(line)
        if parsed is None:
            continue
        file_path, lineno, content = parsed
        key = (file_path, lineno)
        if key in seen:
            continue
        seen.add(key)
        results.append(parsed)
    return results


def find_subagent_type_refs(
    marketplace_root: Path, agent_names: list[str]
) -> list[tuple[str, int, str, str]]:
    """grep for subagent_type: "{name}" for each agent name."""
    results: list[tuple[str, int, str, str]] = []
    for agent in agent_names:
        agent = agent.strip().replace(".md", "")
        if not agent:
            continue
        # Match: subagent_type: "name" or subagent_type=name or subagent_type='name'
        pattern = rf"subagent_type[=:][[:space:]]*[\"']?{re.escape(agent)}[\"']?\\b"
        lines = run_git_grep(marketplace_root, pattern)
        for line in lines:
            parsed = parse_grep_line(line)
            if parsed:
                file_path, lineno, content = parsed
                results.append((file_path, lineno, content, agent))
    return results


def emit_markdown(
    source_plugin: str,
    path_refs: list[tuple[str, int, str]],
    subagent_refs: list[tuple[str, int, str, str]],
) -> str:
    out: list[str] = []
    out.append(f"# External references to `{source_plugin}`")
    out.append("")
    out.append(
        f"All file paths and agent dispatch points that mention "
        f"`plugins/{source_plugin}/` or the source plugin's agents."
    )
    out.append("Every line below needs updating during Commits 2–4 of the consolidation.")
    out.append("")

    # Path refs grouped by file
    out.append("## 1. Files citing source-plugin paths")
    out.append("")
    if not path_refs:
        out.append("None.")
        out.append("")
    else:
        by_file: dict[str, list[tuple[int, str]]] = {}
        for file_path, lineno, content in path_refs:
            by_file.setdefault(file_path, []).append((lineno, content))
        for fp in sorted(by_file):
            out.append(f"### `{fp}`")
            out.append("")
            for lineno, content in sorted(by_file[fp]):
                snippet = content[:120] + ("…" if len(content) > 120 else "")
                out.append(f"- L{lineno}: `{snippet}`")
            out.append("")

    # Subagent_type refs
    out.append("## 2. Subagent_type dispatch references")
    out.append("")
    if not subagent_refs:
        out.append("None.")
        out.append("")
    else:
        by_file: dict[str, list[tuple[int, str, str]]] = {}
        for file_path, lineno, content, agent in subagent_refs:
            by_file.setdefault(file_path, []).append((lineno, content, agent))
        for fp in sorted(by_file):
            out.append(f"### `{fp}`")
            out.append("")
            for lineno, content, agent in sorted(by_file[fp]):
                snippet = content[:120] + ("…" if len(content) > 120 else "")
                out.append(f"- L{lineno}: dispatches `{agent}` — `{snippet}`")
            out.append("")

    # Sweep checklist
    out.append("## 3. Sweep checklist (apply during Commits 2–4)")
    out.append("")
    out.append("For each line above:")
    out.append("- Replace `plugins/{source}/` with `plugins/sulis/`")
    out.append("- Apply any skill / agent / reference renames from CONSOLIDATION_PLAN.md")
    out.append("- For subagent_type references: update to the new agent location after Commit 3 lands")
    out.append("")
    out.append("After Commit 4:")
    out.append("```bash")
    out.append(f"git grep \"plugins/{source_plugin}/\" .")
    out.append("# Expected: zero hits outside the source plugin's own DEPRECATED shell")
    out.append("```")
    out.append("")

    # Summary
    out.append("## Summary")
    out.append("")
    files_with_path_refs = len({fp for fp, _, _ in path_refs})
    files_with_subagent_refs = len({fp for fp, _, _, _ in subagent_refs})
    out.append(f"- Path references: **{len(path_refs)}** across **{files_with_path_refs}** files")
    out.append(f"- Subagent_type references: **{len(subagent_refs)}** across **{files_with_subagent_refs}** files")
    out.append("")

    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--marketplace-root", default=".", type=Path)
    parser.add_argument("--source-plugin", required=True)
    parser.add_argument(
        "--agent-names",
        default="",
        help="comma-separated agent names to search for subagent_type refs",
    )
    args = parser.parse_args()

    marketplace_root = args.marketplace_root.resolve()
    path_refs = find_path_refs(marketplace_root, args.source_plugin)

    agent_names = [a.strip() for a in args.agent_names.split(",") if a.strip()]
    subagent_refs = find_subagent_type_refs(marketplace_root, agent_names) if agent_names else []

    sys.stdout.write(emit_markdown(args.source_plugin, path_refs, subagent_refs))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
