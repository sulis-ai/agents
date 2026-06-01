---
id: WP-FIX008
title: Synthetic WP with mismatched adapter
kind: backend
primitive: create
verification:
  adapter: documentation
  artifact: docs/some-link-check.md
---

# WP-FIX008

This WP declares `verification.adapter: documentation` while the
change's `kind:` is `backend`. P-VER 9.08 fires on the mismatch.
