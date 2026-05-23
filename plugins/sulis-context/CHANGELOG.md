# sulis-context — Changelog

## v0.3.1 — 2026-05-XX

Minor refinements to discovery protocol.

## v0.3.0 — 2026-05-XX

Refresh skill ships. Re-validates an existing `.context/{project}/INDEX.md`
with sticky classifications — only asks about deltas, not re-classifying
already-classified sources.

## v0.2.0 — 2026-04-XX

Show skill ships. Read-only display of the current
`.context/{project}/INDEX.md` so users can see what SRD/SEA will read
on their next invocation.

## v0.1.0 — 2026-03-XX

Initial release. Context Cartographer — folder-structure-agnostic
discovery protocol that scans for architecture documentation, ADRs,
conventions, standards, patterns, domain models, and existing specs.

Discover skill: first-time context discovery for a project. Presents
findings grouped by purpose; user classifies each as authoritative /
informational / superseded / out-of-scope. Writes
`.context/{project}/INDEX.md` for downstream plugins (SRD, SEA,
sulis-security) to consume.

---

_Approximate dates — sulis-context's version history was not formally
tracked before this CHANGELOG was created (2026-05-23). The shape of
each version is reconstructed from the current skill set + plugin.json
metadata._
