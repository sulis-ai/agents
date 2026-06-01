"""YamlCommentAnnotationParser — port 2: parse `# canonical:...` annotations from YAML.

Implements the AnnotationParser port from the TDD's Form section. Scans
release-on-merge.yml line-by-line for two annotation shapes:

    # canonical:step:<step-name>
    # canonical:failuremode:<failuremode-name>

Per ADR-002: these are inert YAML comments that bind a YAML step block to a
canonical entity. The parser does NOT interpret YAML structure beyond running
a parse-check first (Armor: pyyaml safe-load before scan, so a YAML-broken
file raises clearly).

Malformed annotations (e.g. `# canonical: step <name>` with whitespace instead
of colons) are ignored cleanly per TDD Proof section.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


# `# canonical:<kind>:<target>` — kind must be 'step' or 'failuremode'; target
# is a non-empty token (allow letters, digits, hyphens, dots, underscores).
_ANNOTATION_RE = re.compile(
    r"^\s*#\s*canonical:(?P<kind>step|failuremode):(?P<target>[A-Za-z0-9._-]+)\s*$"
)


@dataclass(frozen=True)
class YamlAnnotation:
    """One canonical annotation parsed from the YAML."""

    kind: str  # "step" or "failuremode"
    target: str  # the canonical entity's name (matches Step.name / FailureMode.name)
    line: int  # 1-based line number where the comment appeared


class YamlCommentAnnotationParser:
    """Scan a YAML file for `# canonical:<kind>:<target>` comments."""

    def parse(self, yaml_path: Path) -> list[YamlAnnotation]:
        if not yaml_path.exists():
            raise FileNotFoundError(f"YAML file not found: {yaml_path}")

        # First: confirm the file is parseable YAML. Per Armor section, a YAML
        # parse failure is itself a release-train FailureMode (workflow-yaml-fails-
        # to-parse, MUC-002). Surface it loudly.
        try:
            import yaml  # local import keeps the package optional at module-load time
        except ImportError as e:  # pragma: no cover — pyyaml is in pyproject
            raise RuntimeError("PyYAML required for annotation parsing") from e

        text = yaml_path.read_text()
        try:
            yaml.safe_load(text)
        except yaml.YAMLError as e:
            raise ValueError(f"{yaml_path}: YAML parse failed — {e}") from e

        # Scan line-by-line for annotation comments.
        annotations: list[YamlAnnotation] = []
        for idx, line in enumerate(text.splitlines(), start=1):
            match = _ANNOTATION_RE.match(line)
            if match:
                annotations.append(
                    YamlAnnotation(
                        kind=match.group("kind"),
                        target=match.group("target"),
                        line=idx,
                    )
                )
        return annotations
