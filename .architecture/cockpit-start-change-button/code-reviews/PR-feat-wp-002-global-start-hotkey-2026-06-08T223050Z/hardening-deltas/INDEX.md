# Hardening Deltas — code review of feat/wp-002-global-start-hotkey

No draft hardening deltas produced by this review.

The single finding (F-01, low/awareness — case-sensitive `e.key` comparison)
matches the WP-002 Contract verbatim and the established `ProductSwitcher`
keydown idiom; it is recorded for awareness only, not as a fix to apply.
Per CR-04, awareness items with no failing characterisation test belong on
the Watch List, not in the delta queue.
