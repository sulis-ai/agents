# Governed Action-Surface Standard

> **Sulis-local v0.1.0 (2026-06-13).** The durable home of decision **D8** from
> the `harden-embed-safe-tools` change: how an agent's action-surface is
> shaped (raw-Bash / CLI / MCP) and *governed* (ungoverned / hook-governed /
> permission-denied), and the honesty discipline that labels every embedded
> rule by **where it is actually enforced**. This criterion outlives any one
> change — it is a Sulis-wide architecture principle. It composes with
> `CONTRACT_FIRST_STANDARD.md` (the schema↔transport split): that standard
> governs *the contract two sides meet at*; this one governs *which substrate a
> tool lives on and how its use is governed*.

<!-- summary -->
An agent's set of callable actions is described by **two orthogonal axes** —
**invocation-substrate** (raw-Bash / CLI / MCP) × **governance** (ungoverned /
hook-governed / permission-denied) — **not** by "what the action touches".
Governance is a free-standing layer: a PreToolUse hook governs existing CLIs
*without* converting them to MCP, so "this needs governing" never forces MCP.
**MCP is the narrow exception, not the default:** MCP-ify a tool **iff** *(a
typed/structured contract is needed* **OR** *a denyable identity at a trust
boundary is needed)* **AND** it doesn't bloat the tool-selection surface; the
default substrate is **CLI**. The binding constraint on MCP is tool-**selection
accuracy** (which degrades past roughly 30–50 tools and across similar-name
families), **not** token cost. And: **every embedded rule is labelled by its
enforcement-locus** (i model / ii harness / iii OS) **and threat-scope**
(GAP-α accidental over-reach / GAP-β adversarial deferred). An honest "not
enforced here" beats a false "enforced".
<!-- detail -->

## Severity convention

`MUST` — non-negotiable; violations block the change. `SHOULD` — default;
deviation needs a one-line rationale. `MAY` — judgement.

---

## 1. The two axes (the primitive)

An action's place in the surface is fixed by two **independent** axes. The
common mistake is to classify by *what the action touches* (network? files?
the brain?) — that conflates substrate with governance and produces a
CLI→MCP migration that nobody needs.

| Axis | Values | What it answers |
|------|--------|-----------------|
| **invocation-substrate** | **raw-Bash** · **CLI** · **MCP** | *How is the action invoked?* A bare shell command; a named program with flags (trained-on, ergonomic, cheap to add); or a typed MCP tool with a schema + a denyable identity. |
| **governance** | **ungoverned** · **hook-governed** · **permission-denied** | *How is the action's use adjudicated?* Nothing watches it; a PreToolUse hook inspects and may deny it; or a permission rule removes/denies it outright. |

**The axes are orthogonal.** A CLI can be ungoverned, hook-governed, or
permission-denied. An MCP tool can be allowed or denied. **Governance ≠ MCP**
— this is the load-bearing correction. A `PreToolUse` hook governs the
existing `sulis-*` / `wpx-*` CLIs (allow the family, deny raw `curl`/`wget`,
scope-check writes) **without converting any of them to MCP**. So "this action
needs governing" is satisfied at the *governance* axis and **never** drags the
*substrate* axis to MCP.

`MUST` — classify every action on both axes explicitly. `MUST NOT` — use "it
touches the network / the brain / files" as the classifier; that is the
anti-pattern this standard exists to retire.

---

## 2. The MCP criterion (narrow — default is CLI)

MCP is a real tool with a real cost. Add a tool to MCP **iff**:

> **(typed/structured contract needed** **OR** **denyable identity at a trust
> boundary needed)** **AND** **it does not bloat the selection surface.**

Otherwise the action **stays a CLI**. CLIs are the default because they are
trained-on, ergonomic, near-zero-cost to add, and already ship-gated by the
existing review/merge machinery.

- **Typed/structured contract needed** — the caller needs a schema-validated
  request/response (per `CONTRACT_FIRST_STANDARD.md`), not free-text argv.
- **Denyable identity at a trust boundary needed** — the action sits on a
  trust boundary where the policy is "allow *this* safe path, deny the raw
  one", and that policy is only *expressible* if the safe path is a distinct,
  enumerable tool **identity**. (A Python library function is not a denyable
  identity; an `mcp__server__tool` name is.) This is exactly what makes
  "allow-safe / deny-raw" expressible at the permission layer.
- **No selection-surface bloat** — the **binding constraint**. Tool-**selection
  accuracy** degrades once the surface grows past roughly **30–50 tools**, and
  worse across **similar-name families** (the model picks the wrong sibling).
  Token cost is **not** the binding constraint — the Tool Search Tool (default
  since Jan 2026) removed token cost as the gate; **selection accuracy** is what
  remains. Therefore: **collapse near-identical families to one parameterised
  tool** rather than minting one tool per variant (the emit-* lesson — see §4).

`SHOULD` — when a family of would-be tools differs only by a parameter, expose
**one** parameterised tool (e.g. `scoped_file(op, …)`, not four), per the
selection-accuracy constraint.

`MAY` — MCP-wrap a *hot-path* CLI purely for cost reasons **only** with a
measured benchmark on the real loop showing the per-call screening tax is
material; this is the single cost-driven exception and must cite its numbers.

---

## 3. The honesty-labelling rule (enforcement-locus + threat-scope)

Every embedded rule — in an agent prose nudge, a permission config, a
PreToolUse hook, or a sandbox recipe — is adjudicated at **exactly one
enforcement-locus** and is **labelled** with it plus its **threat-scope**. A
rule **MUST NOT** claim a locus it does not hold.

| Enforcement-locus | Mechanism | What it actually catches | Honest claim |
|-------------------|-----------|--------------------------|--------------|
| **locus i — model** | prose / convention in agent defs + skills | *nothing* — advisory only; the model may ignore it | a **quality / ergonomics** preference, **never** a safety control |
| **locus ii — harness** | permission deny-rules + the PreToolUse hook | recognised **direct** tool calls (e.g. `WebFetch`; out-of-scope `Write`/`Edit`; raw `curl`/`wget` in a Bash string the hook can parse) | **GAP-α (accidental over-reach) closed now** |
| **locus iii — OS** | the shipped Seatbelt / bubblewrap sandbox (enabled + configured by the recipe) | **all** processes including spawned subprocesses (`python -c 'urllib…'`, obfuscated curl) | adversarial subprocess bypass — **closed only when the consumer enables it**; TLS-exfil (GAP-β) **deferred** |

**Threat-scope vocabulary.** **GAP-α** = accidental over-reach (the #211-shaped
real threat — a tool or subprocess strays out of scope by mistake); closed now
at locus ii for recognised calls, and at locus iii for subprocesses once the
sandbox is enabled. **GAP-β** = deliberate adversarial exfil over TLS to a
permitted domain (domain-fronting); the shipped sandbox proxy does **not**
inspect TLS, so GAP-β is **deferred** — named, not built, never claimed closed.

Two honesty corollaries this standard makes binding:

- **MCP-identity is necessary-NOT-sufficient.** A denyable MCP identity is what
  makes "allow-safe / deny-raw" *expressible*; it is **not** itself the wall.
  The wall for the adversarial case is locus iii (the OS sandbox). `MUST NOT`
  label MCP exposure as "enforcement".
- **The sandbox recipe owns the adversarial-subprocess case (locus iii)** and
  **MUST** carry GAP-β as deferred. See
  [`../sandbox-enable-recipe.md`](../sandbox-enable-recipe.md).

`MUST` — every rule names exactly one locus + its threat-scope. `MUST NOT` — a
locus-i (prose) rule that claims it enforces / blocks / denies / prevents /
guarantees anything; prose is advisory by definition.

---

## 4. Worked classification (this change, as the reference example)

The `harden-embed-safe-tools` change applied the criterion. The result is a
**CLI-majority surface + one governance hook + a small typed-MCP carve-out** —
explicitly **not** a CLI→MCP migration:

| Action | Substrate | Governance | Why |
|--------|-----------|------------|-----|
| **safe-fetch** (`safe_fetch`/`safe_search`) | **MCP now** | permission-allowed (the safe path) | denyable identity at the network trust boundary — its identity is what makes "allow-safe / deny-raw web" expressible |
| **scoped file ops** (`scoped_file`, one parameterised tool) | **MCP now** | hook-governed (scope) | typed contract + denyable identity; **one** tool over `read/write/move/remove` to avoid selection bloat (the four-tool family would be the trap) |
| **~55 `sulis-*` / `wpx-*` CLIs** (incl. `gh`, `git push`) | **stays CLI** | hook-governed (allow the family) | trained-on, ergonomic, already ship-gated; no typed-contract / trust-boundary need; MCP-ifying them would blow the selection surface |
| **raw `curl` / `wget` / `WebFetch`** | raw-Bash / built-in | **permission-denied** + hook-denied | the unsafe network path; denied at locus ii, with locus iii as the subprocess backstop |
| **the 21 `emit-*` entity writers** | **stays CLI** | hook-governed (optional scope-check) | **NEVER 1:1 MCP-ify** — that is the similar-name selection-collision trap. If ever exposed, **one** `sulis_emit(entity_type, payload)`, not 21 tools |

Governance is a **single free-standing PreToolUse hook** plus permission rules
— it governs the CLI majority without converting any of them.

---

## 5. Provenance — the spiral chain

This criterion converged across a chain of critical-thinking spirals (the
durable record of *why* the two-axis model beats the touch-based classifier and
the false convention-vs-enforcement trichotomy):

- `01KW3BZNS` — enforcement-locus tiering first surfaced (the false trichotomy
  named).
- `01KTZRTN0` — convention survives only where bypass is a quality miss, never
  a safety hole (locus-i scoping).
- `01KTZTCSP2` — the shipped OS sandbox reframes "L3" as mostly-enable; GAP-α
  closed-now / GAP-β deferred.
- `01KV0G2GCKXZR82C03WHPA17XD` — allowed-write-roots as one config-derived
  resolver shared by the hook + the sandbox (no drift).
- `01KV0KGGQQ` — the governed-action-surface spiral that produced D8: the
  two-axis primitive, governance ≠ MCP, the narrow MCP criterion, and the
  worked classification above.

---

## 6. Cross-references

- [`../sandbox-enable-recipe.md`](../sandbox-enable-recipe.md) — the locus-iii
  backstop; consumes the same write-roots resolver; carries GAP-β deferred.
- [`CONTRACT_FIRST_STANDARD.md`](CONTRACT_FIRST_STANDARD.md) — the schema ↔
  transport split that the typed-contract half of the MCP criterion builds on.
- Prior change `harden-agent-execution-boundary/TDD.md` — the L1 safe-fetch +
  L2 scoped file-tools this surface governs; its §Armor L1/L2 design.
- This change's TDD `.architecture/harden-embed-safe-tools/TDD.md` §Armor —
  the enforcement-locus table this standard generalises; the locus-honesty
  test `test_locus_honesty.py` (SC-E6) reads these labels off the shipped
  surfaces.

---

## Version history

- **v0.1.0 (2026-06-13)** — initial. Graduates D8 (the two-axis
  governed-action-surface criterion + the enforcement-locus honesty rule) from
  the `harden-embed-safe-tools` Working Set into a durable Sulis standard.
