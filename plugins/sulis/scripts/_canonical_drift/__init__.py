"""Internal package for check-canonical-drift.py — three ports + a report dataclass.

Layout:
- reader.py — JsonLdFileReader (CanonicalReader port)
- parser.py — YamlCommentAnnotationParser + MarkdownHtmlAnnotationParser
  (AnnotationParser port). File-extension dispatcher `parse_annotations`
  routes by suffix: `.yml`/`.yaml` → YAML; `.md` → Markdown.
- matcher.py — StrictDriftMatcher (DriftMatcher port) + the
  `cross_tenant_ref_is_allowed` helper used by the Verify phase to
  recognise the consumer Project → marketplace Workflow boundary
  (ADR-002 of discover-project).
- report.py — DriftReport frozen dataclass + JSON envelope serialisation

Path A drift detector per release-train ADR-001 + ADR-002 (WP-007 of
release-train-as-entities); extended for discover-project per ADR-001
(HTML-comment annotations) + ADR-002 (cross-tenant Project → Workflow
boundary) via WP-009.
"""
