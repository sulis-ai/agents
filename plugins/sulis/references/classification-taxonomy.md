# Classification Taxonomy

> **Status:** Active — v0.1.0

Each source surfaced by discovery is classified by the user into one of four
buckets. Downstream plugins (SRD, SEA, sulis-security) read these
classifications and behave differently per bucket.

---

## The Four Classifications

### `authoritative`

**Meaning:** This source is load-bearing. Decisions, definitions, or
specifications recorded here are in force. Downstream artifacts MUST
respect them.

**Examples:**
- A current ADR library where decisions have been formally adopted
- An `ARCHITECTURE.md` that the team treats as the source of truth
- A `DOMAIN_MODEL.md` that defines the entity vocabulary
- A `STANDARDS.md` that the team enforces in code review

**Downstream behaviour:**
- **SRD** grounds facilitation questions in this source ("you already define
  entity `Order` here — should the new feature follow that definition?")
- **SEA** references this source rather than restating its content
  (Respect-Don't-Restate). New SEA artifacts must not contradict authoritative
  sources; if they need to, the contradiction is recorded as an ADR
  ("supersedes external:ADR-007").
- **sulis-security** uses this source to constrain findings — if an
  authoritative standard already mandates TLS 1.3, the auditor doesn't flag
  it as a missing requirement, only as missing implementation.

---

### `informational`

**Meaning:** Useful context, but not binding. The team may have moved past
it, or it may describe ideal-state rather than enforced-state, or it may
simply be background reading.

**Examples:**
- An older design proposal that wasn't fully implemented
- A research note exploring options
- Conference talk notes captured in the repo
- A `TECH_RADAR.md` describing things under evaluation but not adopted

**Downstream behaviour:**
- **SRD** may reference this source when surfacing options to the user
  but does not constrain facilitation by it.
- **SEA** may cite this in ADRs as context for a decision but does not
  treat it as a constraint.
- **sulis-security** ignores informational sources.

Default classification when the user is unsure or declines to classify.

---

### `superseded`

**Meaning:** This source describes a state that is no longer current. It was
true once. It is not now. Keep it for historical reference but exclude from
downstream consumption.

**Examples:**
- ADRs marked `status: superseded` in their frontmatter
- A pre-rewrite architecture document
- Old design notes for a removed feature
- Conventions that the team has explicitly retired

**Downstream behaviour:**
- All downstream plugins **ignore** superseded sources for new artifact
  production.
- Refresh continues to track them in case they are referenced by other
  documents.
- A superseded source can be promoted back to `authoritative` if the user
  classifies it that way in a future discovery run.

---

### `out-of-scope`

**Meaning:** Exclude entirely from downstream consumption. Do not read, do
not reference, do not classify in future runs.

**Examples:**
- Legacy documents that belong to a different project
- Vendor documentation accidentally checked into the repo
- Personal notes, scratch files
- Documents covering a different bounded context that the current
  workstream is not touching

**Downstream behaviour:**
- All downstream plugins **never read** out-of-scope sources.
- The index records them so they can be re-classified later without
  re-discovering.

---

## Classification Rules

1. **The user classifies. The agent does not.** The Context Cartographer
   presents candidates with previews. The user picks the bucket. The agent
   never assumes.

2. **Default to `informational` if the user declines.** When the user is
   unsure or wants to skip a candidate, classify as `informational` and
   move on. This is conservative — informational sources are visible to
   downstream plugins but not binding.

3. **Classifications are sticky across refreshes.** A subsequent
   `/sulis:refresh-context` re-validates existence but does not re-ask the
   user about already-classified sources unless the file has been modified
   since `Last validated`.

4. **Classifications can be overridden manually.** Users can edit
   `.context/{project}/INDEX.md` directly. Refresh respects manual edits.

5. **Promotion and demotion are explicit.** Moving a source between buckets
   (e.g. `informational` → `authoritative`) happens in a refresh session,
   not as a side effect of any other action.

---

## How Downstream Plugins Read the Classification

Each downstream plugin runs a first-step check:

```
1. Read .context/{project}/INDEX.md
2. For each entry in the "Authoritative Sources" section:
   - Load the file
   - Apply Respect-Don't-Restate to anything it covers
3. For each entry in the "Informational" section:
   - Path-only awareness; load only if a specific need arises
4. Ignore "Superseded" and "Out of Scope" sections entirely
```

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 0.1.0 | 2026-05-14 | Initial taxonomy. Four classifications: authoritative, informational, superseded, out-of-scope. |
