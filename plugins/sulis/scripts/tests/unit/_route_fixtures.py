"""Shared fixture-tree builder for the routing-spine test suite.

Extracted from test_route_inventory.py in the WP-002 Blue (REFACTOR) phase
(EP-02; TDD §10.3 names the fixture-tree builder as an extraction candidate).
WP-005 (lookup), WP-006 (match), and WP-007 (gate + CLI) all need a real
skills/agents tree under a tmp_path to exercise the discover/build seam against
real files (MEA-09 / TDD §10.2 — real adapters, not mocks). Centralising the
builder here means those WPs reuse one source of truth rather than each
re-deriving a tree.

Not a pytest test module (the leading underscore keeps it out of collection);
it is a plain helper imported by the test modules.
"""

from __future__ import annotations

from pathlib import Path


def write_file(path: Path, text: str) -> None:
    """Create parent dirs and write `text` to `path` (UTF-8)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def skill_md(name: str, *, description: str = "A fixture skill.") -> str:
    """A SKILL.md body with a folded `description` scalar (the real shape)."""
    return f"""---
name: {name}
description: >
  {description}
user_invocable: true
---
# {name}

Body.
"""


def agent_md(name: str, *, description: str = "A fixture agent.") -> str:
    """A plain specialist agent .md body (no routes_to)."""
    return f"""---
name: {name}
description: >
  {description}
---
{name} body.
"""


def orchestrator_md() -> str:
    """An agents/sulis.md fixture carrying a routes_to list-of-mappings block.

    Mirrors the live orchestrator's shape: the only entry whose `routes_to`
    is read (TDD §3.1).
    """
    return """---
name: sulis
description: >
  The orchestrator. Routes founder intent to specialists.
routes_to:
  - slug: context-cartographer
    description: "Discover existing context, conventions, ADRs, prior art"
    triggers: ["what already exists", "scan the codebase", "discover"]
  - slug: requirements-analyst
    description: "Long-form requirements interview producing SRD + NFR"
    triggers: ["interview me", "capture requirements"]
---
Orchestrator body.
"""


def build_fixture_tree(root: Path) -> Path:
    """Create a plugins/sulis/{skills,agents} tree under `root`. Returns `root`.

    Auto-discovery means the inventory is never hand-listed in code — real
    files are laid down and `discover`/`build_inventory` derive everything
    (WP-002 Notes; ADR-001). The tree includes:

      * three skills (specify, design, and one whose DIRECTORY name `wp-status`
        differs from its frontmatter `name: status` — proving invocation keys
        off `name`, not the dir, TDD §7.5#2),
      * one plain specialist agent (requirements-analyst, no routes),
      * the orchestrator agent (sulis.md) carrying the routes_to block.
    """
    skills_dir = root / "plugins" / "sulis" / "skills"
    agents_dir = root / "plugins" / "sulis" / "agents"

    write_file(skills_dir / "specify" / "SKILL.md", skill_md("specify"))
    write_file(skills_dir / "design" / "SKILL.md", skill_md("design"))
    # Directory name != frontmatter name (TDD §7.5#2).
    write_file(skills_dir / "wp-status" / "SKILL.md", skill_md("status"))

    write_file(agents_dir / "requirements-analyst.md", agent_md("requirements-analyst"))
    write_file(agents_dir / "sulis.md", orchestrator_md())

    return root
