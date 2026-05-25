# sulis-context — Changelog

## v0.4.0 — 2026-05-25 — [DEPRECATED]

**This plugin is consolidated into `sulis` at v0.35.0 as the first Phase 3
consolidation of the change-as-primitive build.**

Authored via `consolidate-into-sulis` v0.1.0 (the methodology meta-skill
introduced in the v1.77.0 marketplace release). Commit chain:

- `0e5c9ea` — step 2/5 — 3 sulis-context skills moved into sulis with
  tin-test renames: `discover` → `discover-context`, `refresh` →
  `refresh-context`, `show` → `show-context`
- `584d438` — step 2/5 (continuation) — founder-friendly description
  rewrites + `/sulis-context:*` → `/sulis:*-context` slash-command sweep
- `2348bc5` — step 3/5 — context-cartographer agent moved into sulis;
  Sulis agent's `related_skills:` block updated to point at the new
  co-located path
- `c4f6358` — step 4/5 — 3 references (classification-taxonomy,
  context-index-template, discovery-protocol) moved into sulis;
  external ref sweep across 9 marketplace files (paths + slash-commands)
- (this commit) — step 5/5 — wrap-up: this plugin marked DEPRECATED;
  sulis bumped to v0.35.0; marketplace.json updated; consolidation run's
  VERIFICATION_REPORT.md captured under
  `plugins/sulis/skills/consolidate-into-sulis/runs/sulis-context-2026-05-25/`

No shim skills written (mirrors the sulis-concierge → sulis precedent at
v0.2.0 and the sulis-execution → sulis precedent at v0.30.0). The plugin
shell stays in-place for marketplace compatibility.

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
