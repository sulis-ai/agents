"""Annotation parsers — port 2: parse `canonical:...` annotations from imperative files.

Two formats are supported, dispatched by file extension:

- YAML (`.yml`, `.yaml`) — used by release-train (`release-on-merge.yml`):

      # canonical:step:<step-name>
      # canonical:failuremode:<failuremode-name>

- Markdown (`.md`) — used by discover-project's SKILL.md per ADR-001:

      <!-- canonical:step:<step-name> -->
      <!-- canonical:failuremode:<failuremode-name> -->

The matching logic downstream (`StrictDriftMatcher`) is unchanged — only
the comment syntax differs by format. Each parser surfaces the same
`YamlAnnotation` shape (kind + target + line number).

Per ADR-001 (release-train inheritance) and discover-project ADR-001:
these annotations bind an imperative line to a canonical Step or
FailureMode. They are inert in their host file (a YAML comment, an
HTML comment in Markdown) but load-bearing for the drift detector's
conformance check.

Malformed annotations are ignored cleanly. An unsupported file
extension yields an empty list — the detector treats unknown formats
as "nothing to check", not as a violation. Add a new format by
extending the `_PARSERS_BY_SUFFIX` dispatch table; the matcher need
not change.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

# YAML form: `# canonical:<kind>:<target>` — kind must be 'step' or
# 'failuremode'; target is a non-empty token (letters, digits, hyphens,
# dots, underscores).
_YAML_ANNOTATION_RE = re.compile(
    r"^\s*#\s*canonical:(?P<kind>step|failuremode):(?P<target>[A-Za-z0-9._-]+)\s*$"
)

# HTML-comment form: `<!-- canonical:<kind>:<target> -->` — tolerates
# leading/trailing whitespace inside the comment.
_HTML_ANNOTATION_RE = re.compile(
    r"<!--\s*canonical:(?P<kind>step|failuremode):(?P<target>[A-Za-z0-9._-]+)\s*-->"
)

# Back-compat alias for any external caller importing the old name.
_ANNOTATION_RE = _YAML_ANNOTATION_RE


@dataclass(frozen=True)
class YamlAnnotation:
    """One canonical annotation parsed from an imperative file.

    Historically named `YamlAnnotation` (the only format originally
    supported); the dataclass is shared across formats now. Renaming
    would ripple to release-train tests that import it — kept as-is
    for backward-compat per the WP's Don't-Touch-Existing-Behaviour
    constraint.
    """

    kind: str  # "step" or "failuremode"
    target: str  # the canonical entity's name (matches Step.name / FailureMode.name)
    line: int  # 1-based line number where the annotation appeared


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
            match = _YAML_ANNOTATION_RE.match(line)
            if match:
                annotations.append(
                    YamlAnnotation(
                        kind=match.group("kind"),
                        target=match.group("target"),
                        line=idx,
                    )
                )
        return annotations


class MarkdownHtmlAnnotationParser:
    """Scan a Markdown file for `<!-- canonical:<kind>:<target> -->` comments.

    Per ADR-001 (discover-project): imperative skill files (SKILL.md)
    bind to canonical Steps via HTML-comment annotations. The
    annotation is invisible to the rendered Markdown (HTML comments
    are not displayed) but visible to the drift detector.

    No format-level pre-parse check (Markdown has no fail-loud
    parser); a malformed Markdown file simply yields no annotations.
    """

    def parse(self, md_path: Path) -> list[YamlAnnotation]:
        if not md_path.exists():
            raise FileNotFoundError(f"Markdown file not found: {md_path}")

        text = md_path.read_text()
        annotations: list[YamlAnnotation] = []
        for idx, line in enumerate(text.splitlines(), start=1):
            # `finditer` so a single line carrying multiple HTML
            # comments still yields every annotation (the comment
            # tokens are themselves single-line in our convention,
            # but the regex is tolerant of co-located annotations).
            for match in _HTML_ANNOTATION_RE.finditer(line):
                annotations.append(
                    YamlAnnotation(
                        kind=match.group("kind"),
                        target=match.group("target"),
                        line=idx,
                    )
                )
        return annotations


# ─── Dispatcher — file extension → parser ────────────────────────────────


def _yaml_parse(path: Path) -> list[YamlAnnotation]:
    return YamlCommentAnnotationParser().parse(path)


def _markdown_parse(path: Path) -> list[YamlAnnotation]:
    return MarkdownHtmlAnnotationParser().parse(path)


# Add a new format by extending this table; the matcher need not change.
# Map extension (lower-case, including the dot) → callable Path → annotations.
_PARSERS_BY_SUFFIX: dict[str, Callable[[Path], list[YamlAnnotation]]] = {
    ".yml": _yaml_parse,
    ".yaml": _yaml_parse,
    ".md": _markdown_parse,
}


def parse_annotations(path: Path) -> list[YamlAnnotation]:
    """Dispatch on file extension; return annotations or empty list.

    `.yml` / `.yaml` → YAML comment parser.
    `.md` → Markdown HTML-comment parser.
    Anything else → empty list (no annotations expected; not an error).
    """
    parser = _PARSERS_BY_SUFFIX.get(path.suffix.lower())
    if parser is None:
        return []
    return parser(path)
