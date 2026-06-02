# Final wave: the end-to-end test

Single piece shipped: the integration test suite that runs the whole
discovery flow against 4 fixture projects + the dogfood check against
this marketplace itself.

15 new tests; full suite at 1585 passing. The dogfood test confirms
running discovery on this repo produces a Project entity consistent
with the one we hand-authored in the release-train work — proving the
methodology actually generates what we previously wrote by hand.

Verdict: ready. Change is feature-complete.
