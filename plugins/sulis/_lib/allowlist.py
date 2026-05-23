"""Per-project + per-skill allowlist loading.

Allowlists let a project mark a finding as known-and-accepted so it
stops appearing as a regression. Each tier-skill loads its own
allowlist; shared format:

  # comment lines start with #
  signature-or-pattern: reason
  signature-or-pattern   (no reason)

Per-project allowlists live at:
  .checkup/{project}/{skill-name}-allowlist.md      # per skill
  .checkup/{project}/known-flaky.md                 # check-tests
  .checkup/{project}/security-allowlist.md          # check-security

Marketplace-shared allowlists live at:
  plugins/sulis/skills/{skill-name}/references/{skill-name}-known-{X}.md
"""

from __future__ import annotations

from pathlib import Path


def load_allowlist(*paths: Path) -> set[str]:
    """Read each path (if it exists); return the union of all entries.

    Each line is either `signature` or `signature: reason`. Signatures
    themselves may contain `:` characters — we split on the LAST `: `
    (colon-space) to find the reason boundary.
    """
    entries: set[str] = set()
    for path in paths:
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # signature: reason — split on last ": " (colon-space)
            sep_idx = line.rfind(": ")
            sig = line[:sep_idx].strip() if sep_idx > 0 else line
            entries.add(sig)
    return entries


def project_allowlist_path(
    repo_root: Path, project: str, skill_slug: str
) -> Path:
    """Conventional per-project allowlist location for a skill."""
    return repo_root / ".checkup" / project / f"{skill_slug}-allowlist.md"


def marketplace_allowlist_path(skill_root: Path, skill_slug: str, kind: str) -> Path:
    """Conventional marketplace-shared allowlist location.

    `kind` is the allowlist's domain noun (e.g., "flaky" → known-flaky.md;
    "vocabulary" → check-readability-vocabulary.md).
    """
    return skill_root / "references" / f"{skill_slug}-known-{kind}.md"
