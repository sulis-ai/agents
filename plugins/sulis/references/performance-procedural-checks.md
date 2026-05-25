# Performance Procedural Checks

<!-- summary -->
This document lists the ten mechanical performance anti-pattern
detections that CR-10 (in the Code Review Standard) requires every
`/code-review` invocation to scan for. Each entry has a detection
signature (regex + file-type filter), severity default per CR-05, an
evidence template citing CR-04, and false-positive guidance. The list
is intentionally narrow and mechanically detectable; broader
performance review (algorithmic complexity, system-wide bottlenecks)
is the reviewer's judgement work, scoped by the Quality lens (CR-07).
<!-- /summary -->

> **Version:** 0.1.0
> **Status:** Active — Calibration Period (90 days from 2026-05-22)
> **Applies to:** CR-10 in `plugins/sulis/references/code-review-standard.md`
> **Audience:** `/code-review` skill author + reviewing agent + future skill authors

---

## Why this exists

LLM-driven quality review catches what an LLM happens to notice. The
same diff reviewed twice by different sessions produces different
findings. For the cheapest class of performance defects — N+1
queries, O(N²) loops, synchronous waterfalls — that variability is
unacceptable: these defects are mechanical, ship to production
regularly, and would be caught deterministically by a 30-line
regex scan.

This document is that scan. Ten signatures. CR-10 makes the scan
mandatory; this document defines what "the scan" means.

The signatures intentionally over-match (favour false-positive over
false-negative) — the reviewer agent's job is to read each finding's
context (per CR-03) and downgrade or omit with justification when
the match is benign.

---

## Severity defaults

Per CR-05 (Severity Rubric With Objective Conditions). Defaults are
starting points; the reviewer adjusts per the context after reading
file:line + surrounding lines.

| Severity | When |
|---|---|
| **CRITICAL** | Pattern in a request handler / hot path with unbounded input |
| **HIGH** | Pattern in a code path that runs on each request, even if input is bounded; OR pattern that would obviously degrade as data grows |
| **CONCERN** | Pattern in cold path, init code, batch job; OR bounded input ≤ small N |
| **ADVISORY** | Style/maintainability impact only (e.g., string concat in loop) |

A reviewer that downgrades from a default severity records the
justification in the finding body (per CR-05's existing rules).

---

## Pattern 1 — N+1 DB query

**Signature (regex + filetype):**

```
Files: *.py *.js *.ts *.tsx *.go *.java *.rb
Outer match: (^\s*(for|while|forEach|map)\b)|(^\s*\.(map|forEach)\()
Inner match (within the loop body's next 20 lines): \b(\.get\(|\.first\(|\.objects\.filter|\.objects\.get|db\.query|session\.execute|prisma\.\w+\.findUnique|prisma\.\w+\.findFirst|\.findOne\(|repository\.findBy)\b
```

**Severity default:** HIGH; upgrade to CRITICAL if the loop is in a
request handler (presence of `async def view_`, `@app.route`,
`@router.get`, etc. above) and input has no bound annotation.

**Evidence template:**

```markdown
**N+1 DB query** (HIGH) — `apps/api/services/notifications.py:42`
> for user_id in recipient_ids:
>     user = User.objects.get(id=user_id)  # ← one query per iteration

The loop fetches `User` once per `recipient_ids` entry. For 1000
recipients this issues 1001 queries (the list plus the loop).

**Fix:** batch with `User.objects.filter(id__in=recipient_ids)` plus
a dict lookup; or use `select_related` / `prefetch_related` upstream.
```

**False-positive guidance:** the loop is bounded to small N (≤5)
established at compile time, OR the loop body comment explicitly
states "batch impossible because <reason>". Downgrade to ADVISORY
or omit with justification.

---

## Pattern 2 — N+1 RPC / HTTP

**Signature:**

```
Files: *.py *.js *.ts *.tsx *.go *.java
Outer match: (^\s*(for|while|forEach|map)\b)|(^\s*\.(map|forEach)\()
Inner match: \b(requests\.|httpx\.|fetch\(|aiohttp\.|axios\.|grpc(Client|_client)\.|stub\.\w+\(|http\.get\(|http\.post\(|client\.\w+\.invoke\()\b
```

**Severity default:** HIGH; CRITICAL on hot path with unbounded input.

**Evidence template:**

```markdown
**N+1 RPC** (HIGH) — `apps/api/services/dispatch.ts:67`
> for (const orderId of orderIds) {
>   const order = await this.orderClient.get(orderId);  // ← one RPC per iteration
> }

Each iteration issues a separate RPC; latency is O(N × per-call-RTT).

**Fix:** use the client's batch method (`getMany(orderIds)`) or
`Promise.all(orderIds.map(id => this.orderClient.get(id)))` if the
upstream service can handle concurrency.
```

**False-positive guidance:** loop is bounded; or the upstream service
genuinely has no batch endpoint. Document and downgrade.

---

## Pattern 3 — N+1 filesystem

**Signature:**

```
Files: *.py *.js *.ts
Outer match: (^\s*(for|while|forEach|map)\b)|(^\s*\.(map|forEach)\()
Inner match: \b(open\(|read_text\(|Path\([^)]+\)\.read|readFileSync\(|fs\.readFile|fs\.readFileSync)\b
```

**Severity default:** HIGH (filesystem is slow per-call).

**Evidence template:**

```markdown
**N+1 filesystem read** (HIGH) — `scripts/migrate.py:88`
> for path in changed_files:
>     content = Path(path).read_text()  # ← one syscall per file

Each iteration triggers an `open()`+`read()`. For 5000 files this is
5000 syscalls; if the files are small the syscall overhead dominates.

**Fix:** parallel read via `asyncio.gather` + `aiofiles`, or batch
with concurrent.futures.ThreadPoolExecutor.
```

---

## Pattern 4 — O(N²) over same collection

**Signature:**

```
Files: *
Detect: nested `for`/`while`/`forEach`/`map` where the inner loop
iterates over the same variable as the outer loop (or a slice/copy
of it). E.g.:

    for a in items:
        for b in items:  # ← same collection
            ...
```

**Severity default:** HIGH if `items` is request-scoped and unbounded;
CONCERN otherwise.

**Evidence template:**

```markdown
**O(N²) loop** (HIGH) — `apps/api/services/recommendations.py:114`
> for candidate in candidates:
>     for other in candidates:  # ← nested iteration over same list
>         if candidate.cluster_id == other.cluster_id and candidate.id != other.id:
>             ...

For N candidates, this runs N² comparisons. At N=1000 the loop body
executes 1,000,000 times.

**Fix:** group by `cluster_id` once via dict/groupby (O(N)) then
process each group separately.
```

**False-positive guidance:** the inner loop is a different collection
(despite same variable name — check scoping); or N is bounded ≤ 100
by upstream invariant.

---

## Pattern 5 — Synchronous waterfall

**Signature:**

```
Files: *.py *.js *.ts (async-aware languages)
Detect: 3+ sequential `await` calls where the outputs are
inspected in order but not data-dependent — i.e., each await's
result is bound to a variable, but the variables aren't used until
all awaits complete.
```

This pattern is harder to detect mechanically — heuristic: look for
3+ `await` statements in a row with simple variable assignments
followed by a code block that uses ALL the variables together.

**Severity default:** CONCERN.

**Evidence template:**

```markdown
**Synchronous waterfall** (CONCERN) — `apps/api/routes/profile.ts:23`
> const user = await getUser(id);
> const settings = await getSettings(id);
> const preferences = await getPreferences(id);
> return { user, settings, preferences };

The three calls are independent (none uses the prior's result). They
serialise unnecessarily — total latency is sum of three RTTs.

**Fix:** `const [user, settings, preferences] = await Promise.all([getUser(id), getSettings(id), getPreferences(id)]);` — total latency becomes max of three.
```

---

## Pattern 6 — Unbounded materialisation

**Signature:**

```
Files: *.py *.ts *.js
Match: \b(\.all\(\)|list\([^)]*qs[^)]*\)|\.collect\(\)|Array\.from\(|\[\.\.\.\w+\])\b
where the resolved expression is a query/iterator type without a
.limit() / take() / paginate() in the same chain.
```

**Severity default:** HIGH if the loaded object is request-scoped;
CONCERN if init/batch.

**Evidence template:**

```markdown
**Unbounded materialisation** (HIGH) — `apps/api/services/users.py:55`
> users = list(User.objects.filter(active=True))  # ← loads all matching rows

Materialises the entire active-user set into memory. As the active
user count grows, memory + DB time grow linearly with no ceiling.

**Fix:** paginate (`.limit(100).offset(page * 100)`) or stream (use
`.iterator()` for one-pass processing).
```

---

## Pattern 7 — Repeated invariant computation in loop

**Signature:**

```
Files: *
Match: inside a loop body, a function call or expression whose
arguments don't depend on the loop variable and that doesn't have
side effects — e.g., len(items) recomputed; config.get("key")
inside loop; len(some_set) inside loop.
```

**Severity default:** ADVISORY.

**Evidence template:**

```markdown
**Repeated invariant computation** (ADVISORY) — `scripts/process.py:34`
> for item in items:
>     if i < len(items) - 1:  # ← len(items) recomputed each iteration

`len(items)` is loop-invariant; hoisting it saves N-1 function calls.

**Fix:** `n = len(items)` before the loop; use `n` inside.
```

---

## Pattern 8 — Wasted DB roundtrips

**Signature:**

```
Files: *.py *.ts *.js
Match: 3+ sequential `.first()` / `.get()` / `.findOne()` calls in
the same function on the same model class, where a single query
with `IN`/`filter` could fetch all of them.
```

**Severity default:** CONCERN.

**Evidence template:**

```markdown
**Wasted DB roundtrips** (CONCERN) — `apps/api/services/audit.py:101`
> primary = User.objects.get(id=primary_id)
> secondary = User.objects.get(id=secondary_id)
> backup = User.objects.get(id=backup_id)

Three sequential queries for three known IDs; a single `User.objects.filter(id__in=[primary_id, secondary_id, backup_id])` does it in one round trip.

**Fix:** one query with `id__in=[...]` plus dict lookup by `id`.
```

---

## Pattern 9 — String concat in hot loop

**Signature:**

```
Files: *.py *.java
Match: inside a loop, `+=` operator with string operand, OR
string concatenation via `+` accumulator.
```

**Severity default:** ADVISORY (correctness-equivalent; style/perf only).

**Evidence template:**

```markdown
**String concat in loop** (ADVISORY) — `scripts/render.py:22`
> result = ""
> for chunk in chunks:
>     result += chunk  # ← O(N²) accumulation in Python's immutable strings

In Python, string `+=` in a loop is O(N²) total (each iteration
copies the accumulated result). For large N this dominates.

**Fix:** use `result = "".join(chunks)` — single allocation, O(N).
```

**Language note:** in modern JavaScript engines, `+=` on strings
inside loops is optimised; pattern doesn't apply to `*.js` / `*.ts`.
Skip for those file types.

---

## Pattern 10 — Scan-heavy filter on non-indexed column

**Signature:**

```
Files: *.py *.ts (ORM-using code)
Match: `.filter()` / `.where()` clause with column that is not
in the indexed-columns list for that table.
```

This pattern requires schema knowledge (which columns are indexed).
Implementation: read project's migration files / `schema.prisma` /
`models.py` for `db_index=True` / `@@index` annotations; build an
index allowlist per table; flag filter columns not in the allowlist.

**Severity default:** CONCERN (best-effort; schema parsing may miss
recently-added indexes).

**Evidence template:**

```markdown
**Scan-heavy filter** (CONCERN) — `apps/api/services/search.py:73`
> users = User.objects.filter(bio__icontains=query)  # ← `bio` is not indexed

The `bio` column is not in `User`'s indexed-column list (checked
against `models.py:42`). At table size > 100k rows this filter
triggers a full scan.

**Fix:** add a GIN index on `bio` for trigram search, OR move to a
dedicated search index (Postgres `tsvector`, ElasticSearch).
```

**False-positive guidance:** the column WAS recently indexed but the
migration hasn't been read yet; OR the filter is acceptable because
the table is known-small (config-table-sized).

---

## Self-attestation in the report

When `/code-review` runs CR-10, it records this row in the
Methodology checklist (per CR-08):

```markdown
- [✓] **CR-10 Performance procedural checks.** Patterns scanned: 10. Findings: N (severity breakdown). Downgrades applied: M (with one-line justification per finding).
```

If a pattern was skipped (e.g., Pattern 10 because schema files
weren't parseable):

```markdown
- [—] **CR-10 Performance procedural checks.** Patterns scanned: 9 of 10. Pattern 10 (scan-heavy filter) skipped: schema files at `apps/api/models/*.py` not parseable in this review's scope; flagged for follow-up.
```

---

## Calibration

CR-10 enters a 90-day calibration window from 2026-05-22. During this
window:

- Each finding's severity decision (default + any downgrade) is
  recorded in the report's Methodology section
- Findings that were downgraded to ADVISORY or omitted are tracked
  alongside their justification
- After 90 days, the signature regexes + severity defaults are
  reviewed against accumulated data and tuned

If a pattern produces >50% false-positive rate during the calibration
window, its severity default drops one tier OR the signature is
tightened. Conversely, a pattern that consistently fires on real
defects with no false positives can be promoted (default severity
raised).

## Boundary

This document defines mechanically-detectable anti-patterns. It does
NOT define:

- Algorithmic complexity review (the reviewer's judgement on whether
  an O(N log N) algorithm is right vs O(N))
- System-wide performance review (cache hierarchies, connection
  pools, queue depths)
- Profiling-driven optimisation (no static-analysis tool catches
  hotspots discovered by `py-spy` or `perf`)
- Frontend-specific performance (bundle size, render passes, layout
  thrashing) — those belong in a separate frontend-quality standard

The reviewer's Quality lens (CR-07) covers those concerns through
LLM judgement; CR-10 covers the cheap mechanical floor.

## Composition

- **CR-01 Mechanical Baseline** — CR-10 runs alongside CR-01 (regex
  scan, fast, deterministic)
- **CR-04 Evidence Discipline** — every CR-10 finding cites file:line + quoted text
- **CR-05 Severity Rubric** — CR-10 severity defaults are starting
  points; CR-05's adjustment rules apply
- **CR-07 Lens Completion** — CR-10 findings are recorded as output
  item 7 in the Quality lens
- **CR-08 Self-Attestation** — CR-10 row in the Methodology checklist
- **CP-01..CP-05 (Convention Preference)** — every "Fix" in a CR-10
  finding follows the established convention for that pattern
- **HD-01..HD-NN (Hardening Delta)** — accepted CR-10 findings emit
  as deltas with `source: code-review:CR-10:pattern-N`

## Version history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-05-22 | Initial release. 10 patterns. Calibration window starts. |
