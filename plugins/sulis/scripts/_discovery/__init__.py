"""``_discovery`` — internal package for the ``/sulis:discover-project``
skill's deterministic Python helpers.

First arrival: WP-002 (``tenant.py`` — consumer-tenant ULID derivation).
Downstream WPs (WP-003 Detect, WP-004 Infer, WP-006 Mint, WP-007 Verify)
extend the package without re-creating this marker file.

The leading underscore signals "internal to the skill" — not a public
plugin module; not imported from outside ``plugins/sulis/scripts/``.
"""
