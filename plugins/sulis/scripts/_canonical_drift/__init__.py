"""Internal package for check-canonical-drift.py — three ports + a report dataclass.

Layout:
- reader.py — JsonLdFileReader (CanonicalReader port)
- parser.py — YamlCommentAnnotationParser (AnnotationParser port)
- matcher.py — StrictDriftMatcher (DriftMatcher port)
- report.py — DriftReport frozen dataclass + JSON envelope serialisation

Path A drift detector per ADR-001 + ADR-002 (WP-007 of release-train-as-entities).
"""
