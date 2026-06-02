# Code Review: train-2026-06-01T184341Z — the skill prose

Single WP shipped: the `/sulis:discover-project` skill (the user-facing
prose that walks someone through the 5 phases of detecting + minting
their project's settings).

Mechanical baseline green. Per-WP code review on the skill PASSed with
zero findings. Composition check: the skill correctly references all 5
backend pieces by name, all 5 phase identifiers from the canonical spec,
and the three Ask-phase prose fragments by path. Verdict: ready.

A small fix landed earlier in this train cycle — the drift detector was
crashing on the "tool reused from elsewhere" rows that the canonical
specs use. One-line filter added. Refs CH-01KT1W.
