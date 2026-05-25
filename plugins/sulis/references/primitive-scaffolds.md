# Primitive Scaffolds

Per-primitive Red-Green-Blue scaffolds. The executor branches on the
WP's `primitive` field (one of 22 from `change-primitives.md`) to
apply the right shape.

**v0.5 covers all 22 primitives across all 5 MECE groups.**

- **EXPAND (5)** — Reuse, Compose, Extend, Generate, Create
  (shipped in v0.1).
- **REORGANISE (6)** — Move, Refactor, Inline, Merge, Decompose,
  Abstract (shipped in v0.5; require characterisation tests).
- **SUBSTITUTE (3)** — Replace, Strangle, Wrap (shipped in v0.5).
- **CONTRACT (2)** — Deprecate, Delete (shipped in v0.5; always
  Deprecate → Delete sequence).
- **REINFORCE (6)** — Test, Instrument, Secure, Harden, Gate,
  Document (shipped in v0.5; orthogonal to core primitives).

The executor reads the WP's `primitive` field and applies the matching
scaffold below.

---

## EXPAND group (v0.1)

The EXPAND group adds new behaviour to the system. Listed cheapest →
most invasive (CP-01 priority 0 favours the cheapest applicable).

### 1. Reuse

**Definition.** The new behaviour comes entirely from calling an
existing primitive at a new site. No new logic is introduced.

**Red.**

```
# Test that the existing primitive is now consumed at the new site.
# The test asserts the behaviour at the new site, not the primitive's
# internal behaviour (that has its own tests).
def test_<new_site>_calls_<existing_primitive>():
    # Arrange the new site's input
    # Act: invoke the new site
    # Assert: the outcome that the existing primitive produces
```

**Green.**

```python
# At the new call site:
from <module> import <existing_primitive>

def <new_site>(...):
    return <existing_primitive>(...)
```

The Green step adds the import + the call. Nothing else.

**Blue.** Look for duplicated wrappers — if multiple call sites wrap
the same primitive in similar boilerplate, extract the wrapper.

**Anti-pattern.** Re-implementing the primitive at the new site
instead of calling the existing one. CP-01 priority 0 (internal
prior art) is non-negotiable; if the existing primitive doesn't quite
fit, the right move is `Extend` (next primitive), not re-implementation.

---

### 2. Compose

**Definition.** The new behaviour comes from wiring existing pieces
together. No new logic; the composition is the contribution.

**Red.**

```
# Integration test of the composition's contract.
def test_<composition>_produces_<expected_outcome>():
    # Arrange: the inputs the composition takes
    # Act: invoke the composition
    # Assert: the end-to-end outcome
```

**Green.**

```python
def <composition>(input):
    a = <existing_primitive_1>(input)
    b = <existing_primitive_2>(a)
    return <existing_primitive_3>(b)
```

The Green step wires the pieces. Each piece's internal behaviour is
already tested; the composition's tests cover the wiring.

**Blue.** If the composition appears ≥ 2 times across the codebase,
extract it as a named primitive. (If only at this one site, leave it
inline.)

**Anti-pattern.** Reaching into a primitive's internals to "tweak"
it during composition. If the primitive doesn't quite fit, use
`Extend` (which modifies the primitive itself in a controlled way),
not a tweak that bypasses the primitive's contract.

---

### 3. Extend

**Definition.** The new behaviour adds a branch / parameter / overload
to an existing primitive without disrupting its existing callers.

**Red.**

```
# Test the new branch/parameter/overload specifically.
def test_<existing_primitive>_with_<new_param>():
    # Arrange: input that exercises the new branch
    # Act: invoke with the new param
    # Assert: the new branch's behaviour

# Plus: existing tests for <existing_primitive> still pass
# unchanged (regression check).
```

**Green.** Add the minimum change to the primitive:

- **New optional parameter** with a default that preserves existing
  behaviour. Old callers don't notice.
- **New branch** keyed off a flag or input shape, with the existing
  behaviour as the default path.
- **New overload** when the language supports it (TypeScript
  overloads, Python `@overload` decorator, Go variadic).

**Blue.** Refactor to keep the extension narrow. If the primitive
is now branchy enough that comprehension is suffering, the next
primitive to consider is `Refactor` (REORGANISE group — extract the
branches into named helpers).

**Anti-pattern.** Extending in a way that breaks existing callers.
The contract is: existing callers don't notice. If you have to
update other call sites for compilation to succeed, the extension
is wrong — either find a backward-compatible shape or escalate
(this is now a SUBSTITUTE pattern: `Strangle` or `Replace`,
v0.5).

---

### 4. Generate

**Definition.** The new behaviour is produced by a templating or
codegen rule applied to a source definition (schema, IDL, OpenAPI,
GraphQL SDL, protobuf, etc.).

**Red.**

```
# Test the generator's output shape, not its internals.
def test_<generator>_produces_<expected_artifact>():
    # Arrange: the source definition
    # Act: run the generator
    # Assert: the generated artifact has the expected shape
```

Plus integration tests: the generated artifact is consumed
correctly by the rest of the system.

**Green.**

```bash
# Add the generator rule (Makefile, package.json script, etc).
generate:
    <generator-binary> --input schema.proto --output generated/
```

Run the generator; commit the generated artifacts AND the rule.

**Blue.** Look for duplicated generator templates — if multiple
generation rules use near-identical templates, consolidate.

**Anti-pattern.** Hand-editing generated artifacts. If the generator
doesn't produce what's needed, fix the generator (or extend the
source definition); don't hand-edit downstream.

---

### 5. Create

**Definition.** The new behaviour is genuinely new code — no
existing primitive applies (Reuse), no composition of existing
primitives fits (Compose), no extension preserves contracts
(Extend), and no generator pattern applies (Generate).

**Internal-prior-art check is mandatory before Create** (EP-03 +
CP-01 priority 0). If a search of the codebase (and of
`.architecture/{project}/probe-raw/1_2_capabilities.json` if it
exists) surfaces a near-match, the WP's primitive is wrong — halt
and escalate; the WP should be re-classified as one of the cheaper
primitives.

**Red.**

```
# Failing test for the genuinely-new behaviour.
def test_<new_behaviour>():
    # Arrange: input
    # Act: invoke the new code
    # Assert: outcome per WP Contract
```

Plus edge cases and hardening assertions per RGB-01.

**Green.** Write the minimum implementation. Boring per CP-01..05:

- Explicit types.
- Explicit error handling (no bare `except`, no swallowed errors).
- No metaprogramming, no clever shortcuts.
- Convention-defaulted protocol / format / library choices.

**Blue.** Refactor to boring shape. Common Blue cleanups for Create:

- Extract magic numbers / strings to named constants.
- Split functions ≥ 30 lines into named smaller functions.
- Replace nested conditionals with early returns or guard clauses.
- Add docstrings / doc comments per language convention.

**Anti-pattern.** Creating from scratch what already exists. The
internal-prior-art check is the gate; if it surfaces a match, the
WP's classification is wrong.

---

## Primitive selection check at step 3 (GREEN)

Before writing any Green-step code, the executor verifies the WP's
declared `primitive` field is consistent with the codebase state:

1. **Reuse / Compose / Extend / Generate** declared but no existing
   primitive matches → halt + escalate. The WP's classification is
   wrong; SEA should re-decompose with a different primitive.
2. **Create** declared but a near-match exists in the codebase →
   halt + escalate. The WP should be re-classified to Reuse,
   Compose, or Extend.
3. **REORGANISE primitive declared without a `characterisation_test`
   field in the WP frontmatter** → halt + escalate. Characterisation
   tests are mandatory for REORGANISE per `change-primitives.md`;
   SEA must specify the test before the executor refactors.
4. **Strangle declared without a `removal_plan` field** → halt +
   escalate. The Fowler Strangler-Fig pattern requires an explicit
   removal plan; permanent strangling is technical debt.
5. **Wrap declared without `subject_ownership` field** → halt +
   escalate. Wrap is only justified when the subject is external or
   legacy; missing field signals SEA didn't classify correctly.
6. **Delete declared without prior Deprecate** in the codebase (a
   grep for the primitive being deleted should find the deprecation
   warning) → halt + escalate. Deprecate → Delete sequence is
   non-negotiable.

In all cases the BLOCKER record's "Suggested next step" names the
specific re-classification or upstream fix.

---

## REORGANISE group (v0.5)

The REORGANISE group restructures existing code without changing its
external behaviour. **All REORGANISE primitives require a
characterisation test first** (per `change-primitives.md`) — captures
current behaviour as the spec the refactor must preserve. The
executor reads the WP's `characterisation_test` field; runs the
characterisation test; confirms it passes against the current code;
refactors; re-runs the characterisation test; confirms no behavioural
drift.

### 6. Move

**Definition.** Relocate a primitive from one module / package /
file to another without changing its behaviour or signature.

**Red.** Characterisation test (existing tests, verified passing
against the current location).

**Green.**

```bash
# Move the file/symbol to its new home; update imports across the
# codebase that reference it.
git mv old/path/foo.py new/path/foo.py
# Update import sites with a structural search-and-replace.
```

Re-run characterisation test. Must still pass.

**Blue.** Look for stale imports in the old module's other files
(forgotten transitive imports). Clean up.

**Anti-pattern.** Moving a file AND changing its behaviour in the
same Green step. The Move is a pure relocation; behavioural changes
need their own primitive (typically `Extend` or `Refactor`).

---

### 7. Refactor

**Definition.** Restructure a primitive's internals (rename
variables, extract functions, simplify conditionals) without
changing its external contract.

**Red.** Characterisation test of the primitive's external behaviour.

**Green.** Apply the refactor. Examples:

- Extract a complex condition into a named helper.
- Rename a variable to express intent.
- Replace nested conditionals with early returns.
- Extract a long function into 2-3 named smaller functions.

**Blue.** Look for adjacent code that would benefit from the same
refactor pattern (within the same file, per EP-07 Boy Scout).

**Anti-pattern.** Refactoring across multiple files in one Refactor
WP. The scope is **inside one primitive** (or one file's worth of
related primitives). Cross-file refactors are `Decompose` or
`Merge`.

---

### 8. Inline

**Definition.** Replace a call to a primitive with the primitive's
body, then delete the primitive.

**Red.** Characterisation test of the calling site (the inlined
behaviour preserves the caller's outcome).

**Green.**

```python
# Before:
def helper(x): return x * 2 + 1
def caller(): return helper(5)

# After:
def caller(): return 5 * 2 + 1
```

Delete `helper`. Re-run characterisation test.

**Blue.** Confirm `helper` is no longer referenced anywhere.

**Anti-pattern.** Inlining a primitive that has ≥ 2 call sites
(would duplicate the body). Inline is only for single-caller
primitives. If multiple callers exist, the right move is to leave
the primitive in place or `Merge` it with similar primitives.

---

### 9. Merge

**Definition.** Combine 2+ near-identical primitives into one.

**Red.** Characterisation tests of all the primitives being merged
(behaviour of each must be preserved by the merged version).

**Green.** Implement the merged primitive — typically parameterised
where the originals differed. Update all call sites to use the
merged version. Delete the originals.

**Blue.** Confirm all originals are removed. Confirm the merged
version's signature is at least as flexible as the union of the
originals'.

**Anti-pattern.** Merging primitives that look similar but have
genuinely different semantics. The characterisation tests must all
pass against the merged version; if they don't, the primitives
weren't actually duplicates.

---

### 10. Decompose

**Definition.** Split one primitive into 2+ smaller primitives.

**Red.** Characterisation test of the original (the decomposed
pieces' composition must preserve the original's behaviour).

**Green.** Implement the smaller primitives. Update the original's
call sites to compose them (or leave the original in place as a
thin wrapper that composes them — defer the choice to Blue).

**Blue.** If the original is now a trivial wrapper around the
composition, `Inline` it (becomes its own follow-up WP).

**Anti-pattern.** Decomposing into pieces that are individually too
small to be useful primitives. Decompose because of cognitive load
or testability — not because "smaller is always better."

---

### 11. Abstract

**Definition.** Extract a shared abstraction from 2+ concrete
primitives that share a common pattern.

**Red.** Characterisation tests of all the concrete primitives
(behaviour of each must be preserved when re-implemented in terms
of the abstraction).

**Green.**

```python
# Before:
def process_email(notif): send_via_smtp(notif)
def process_sms(notif): send_via_twilio(notif)

# After: introduce abstraction
class NotificationChannel(Protocol):
    def send(self, notif): ...

class EmailChannel: ...
class SmsChannel: ...
def process(notif, channel: NotificationChannel): channel.send(notif)
```

Re-run all characterisation tests. Must still pass.

**Blue.** Look for other primitives that could also implement the
abstraction (within the same file, per EP-07 scope).

**Anti-pattern.** Abstracting prematurely with one concrete
implementation. The threshold is **≥ 2 concrete primitives sharing
the pattern** (per EP-03 Reuse First). Single-implementation
abstractions are speculative and almost always wrong.

---

## SUBSTITUTE group (v0.5)

### 12. Replace

**Definition.** Swap one implementation for another with the same
external contract.

**Red.** Tests of the contract (the new impl must pass the same
tests as the old).

**Green.** Implement the new version. Swap the call sites. The old
version is deleted in the same Green step (atomic swap).

**Blue.** Confirm the old version is no longer referenced.

**Anti-pattern.** Replacing without preserving the contract. If the
new impl can't pass the old tests, this is `Strangle` or a breaking
change, not Replace.

---

### 13. Strangle

**Definition.** Gradual replacement using the Fowler Strangler-Fig
pattern. The new impl ramps up behind a flag while the old impl
remains; eventually the flag flips fully to the new impl and the
old impl is deleted.

**Red.** Tests of both implementations (both must work for the
duration of the strangling).

**Green.** Add a feature flag. New impl behind `if flag.enabled:`,
old impl in `else:`. Both code paths kept until the strangle plan
completes.

**Removal plan (required).** The WP's frontmatter must include
`removal_plan` per `change-primitives.md` — when does the old impl
get deleted? What conditions trigger the flag flip? Without a
removal plan, Strangle is permanent technical debt.

**Blue.** Confirm both code paths are tested. Confirm the removal
plan is documented in `## Acceptance Evidence`.

---

### 14. Wrap

**Definition.** Adapter pattern around something outside the
system's control (external SDK, legacy system, third-party library).

**Subject ownership (required).** Per `change-primitives.md`, the
WP frontmatter must declare `subject_ownership: external` or
`subject_ownership: legacy` — Wrap is only justified when the
wrapped subject isn't the team's to modify.

**Removal plan (required when ownership is `legacy`).** When does
the legacy system get replaced and the wrapper deleted? For
`external` ownership, the wrapper is permanent.

**Red.** Tests of the wrapper's contract (NOT the wrapped subject's
internals).

**Green.** Implement the wrapper as a thin adapter — translate the
external API's shape to the system's preferred shape; nothing more.
Resist the temptation to add behaviour the system "wishes" the
external API had — that belongs in a separate primitive that uses
the wrapper.

**Blue.** Confirm the wrapper's surface is minimal. If the wrapper
is growing logic, that logic belongs above the wrapper, not in it.

**Anti-pattern.** Using Wrap for something the team owns. If the
team owns the subject, the right move is `Replace` or `Refactor`,
not Wrap.

---

## CONTRACT group (v0.5)

### 15. Deprecate

**Definition.** Mark a primitive as deprecated. Add a deprecation
warning emitted on use; add a migration guide. **Do not remove
yet.** Deprecation is a signal to callers, not a removal.

**Red.** Test that the deprecation warning fires when the
deprecated primitive is called.

**Green.**

```python
import warnings

def old_primitive(...):
    warnings.warn(
        "old_primitive is deprecated; use new_primitive instead. "
        "Removal target: v3.0.0 (see ADR-NNN).",
        DeprecationWarning,
        stacklevel=2,
    )
    # original behaviour preserved
```

Update the docs / README / migration guide.

**Blue.** Confirm the deprecation warning is wired into the
project's CI (deprecation-as-error in test runs forces callers to
notice).

**Anti-pattern.** Deprecating without a migration path. The
deprecation warning must point at the new primitive (or document
why removal is the migration). Naked deprecation strands callers.

---

### 16. Delete

**Definition.** Remove a deprecated primitive. **Always
Deprecate → Delete in sequence.** Never Delete without prior
Deprecate (callers got no warning).

**Red.** Tests confirming no callers remain (a static-analysis pass
or a project-wide grep that finds zero references).

**Green.** Remove the primitive's code, tests, and documentation.

**Blue.** Confirm no orphan references in docs, ADRs, or other
files.

**Anti-pattern.** Deleting without confirming zero call sites. The
Red step's contract is "no callers exist"; if any do, the WP is
not ready — Strangle or Migrate them first.

---

## REINFORCE group (v0.5; extends beyond v0.1's Test)

REINFORCE primitives are **orthogonal to the core primitives** —
they add quality / observability / hardening to existing primitives.

### 17. Test (covered in v0.1 as part of every RGB cycle)

Tests are added implicitly during the Red step of every WP. The
`Test` primitive specifically refers to **retrofitting tests onto
existing untested code** — a WP whose primary purpose is increasing
coverage without changing behaviour.

**Red.** Characterisation tests of the existing behaviour (these
are the tests being added).

**Green.** Run the tests; confirm they pass against the existing
code (no behaviour change).

**Blue.** Look for adjacent untested primitives in the same file
(per EP-07 scope). Add tests within scope.

---

### 18. Instrument

**Definition.** Add observability (logs, traces, metrics) to an
existing primitive per OpenTelemetry conventions (CP-04 dominant
player).

**Red.** Tests asserting the instrumentation is emitted at the
right call sites (use a test-time exporter to capture spans/metrics).

**Green.**

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

def existing_primitive(...):
    with tracer.start_as_current_span("existing_primitive"):
        # existing behaviour
        ...
```

**Blue.** Confirm the span / metric names follow project naming
conventions; confirm no sensitive data leaks into log attributes.

---

### 19. Secure

**Definition.** Apply a security control per the security-standard
to an existing primitive. Examples: input validation, output
encoding, rate limiting, authentication check, authorisation check.

**Red.** Tests of the security control (attempted bypass produces
the expected denial; legitimate use still succeeds).

**Green.** Apply the control. Composes with the security-standard's
specific control recipes.

**Blue.** Confirm the control is wired into the right code paths
(no bypass routes around it).

**Anti-pattern.** Adding the control without testing the bypass
attempt. Security controls without negative tests are theatre.

---

### 20. Harden

**Definition.** Wrap calls in resilience policies — timeouts,
retries, circuit breakers — per the dominant-player conventions
(typically gRPC retry policy, tenacity for Python, resilience4j for
Java).

**Red.** Tests with deterministic fault injection (toxiproxy, mock
clock, etc.) — assert the resilience policy fires when the call
times out / fails / hits the circuit-breaker threshold.

**Green.** Apply the policy. Use the project's resilience library
of choice (CP-01 priority 0 — check for existing internal
resilience helpers first).

**Blue.** Confirm the timeout / retry / circuit-breaker numbers
match the project's existing resilience config (CP-01 priority 0
— don't introduce a new tuning unless justified).

---

### 21. Gate

**Definition.** Add a feature flag / kill switch around an existing
primitive.

**Red.** Tests of both code paths — flag on (new behaviour) and
flag off (existing behaviour preserved).

**Green.**

```python
if flag('cancel_subscription_v2'):
    # new path
else:
    # existing path
```

Wire the flag through the project's feature-flag system (often a
`Gate` primitive composes with a `Reuse` of the existing flag
client).

**Blue.** Document the flag's lifecycle (rollout plan, kill criteria,
sunset target) in the WP's `## Acceptance Evidence`.

**Anti-pattern.** Adding a flag without a sunset target. Permanent
flags are technical debt; every flag is either on its way to
universal-on (and removal) or universal-off (and removal).

---

### 22. Document

**Definition.** Write or update documentation (README, ADR, runbook,
inline docstrings) for an existing primitive.

**Red.** N/A for Document — docs aren't a runtime artifact. The
"test" is a review pass.

**Green.** Write the docs. Convention: docstring per language norm
(reST for Python, JSDoc for JS, godoc for Go); README updates
follow the project's existing README style; new ADRs use the
project's ADR template.

**Blue.** Confirm cross-references — if the docs name other
primitives, those names are accurate; if they cite ADRs, the ADRs
exist.

**Anti-pattern.** Documenting code that doesn't exist yet (write
docs after the code is real, not in advance — the code may drift
from the docs during implementation).

