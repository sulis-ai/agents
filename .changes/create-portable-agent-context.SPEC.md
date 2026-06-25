---
founder_facing: false
---

# Spec — Portable agent context: rich by default, raw discoverable

**Change:** CH-GJ9KQR · create

> Grounds on the critical-thinking analysis (run `01KVX0BQE2…`) that established
> portable, Sulis-owned context as the enabler for provider failover and for
> hardened resume/audit, and on this change's recon
> (`.changes/create-portable-agent-context.RECON.md`).

## Intent

Give every spawned agent **rich, curated context by default** assembled from
the durable sources Sulis already owns, and let the agent **discover the raw
full record on demand** — backed by a **Sulis-owned per-session/thread message
log** that tracks every prompt and message. Today the rich view exists
(folded turn-summaries) but the *raw* full history is read from **Claude's own
session transcript files** (`~/.claude/projects/…`, via `locateTranscripts`) —
i.e. the complete record depends on the provider's storage. This makes our
context **provider-locked** and fragile (lost if the provider's files rotate,
unrecoverable on a different provider). This change makes the context
**Sulis-owned and provider-agnostic**: our store is the source of truth, so a
session can be resumed — or restarted on any provider — from *our* context,
not the provider's memory. It is the foundational enabler for headless
failover, and it independently hardens crash-resume and auditability.

## Scope

**1 — Sulis-owned message log (the new core).** Append **every** prompt and
message in a session/thread to a Sulis-owned, append-only store, keyed by
session/thread (and the bound change, where there is one). One record per
message: role (founder / agent / tool), timestamp, content, and a stable
ordering. Provider-agnostic shape — not Claude's JSONL format. This is the
authoritative raw record; the provider's own transcript becomes a convenience,
not the source of truth.

**2 — The context payload assembler.** Build the **rich, curated** payload that
is injected into a (re)spawned agent, assembled from sources Sulis already
owns:
- the **brief** (`pre_prompt.txt` / `CONTEXT.md` — the change identity + recon);
- the **Working Set** (live reasoning state — problem / current best solution /
  decisions-in-flight / the *why* / rejected-with-rationale);
- the **relevant brain entities** (the change's Opportunity / Requirements /
  Decisions / Design / Scenarios — selected by relevance, not the whole graph);
- a **structured/summarised transcript** of the thread (decisions taken, tool
  outcomes, open threads) — **never the raw turn-by-turn dump**.
The payload has a defined schema and a token-budget tier (lean / standard /
full) chosen by task stakes, so it fits a provider's context window.

**3 — The discovery seam (progressive disclosure).** The agent receives the
rich payload by default **plus a pointer/tool to fetch the raw full set** (part
or all of the message log for the session/thread) when it genuinely needs the
detail. Rich-by-default keeps every call cheap; raw-on-demand means nothing is
lost.

**4 — Provider-agnostic injection.** Deliver the payload through the existing
`ProviderAdapter` seam (the brief is already injected as an argv element, not
via provider memory), so the **same** payload can seed a Claude session, a
resumed session, or (later) a different provider — the assembler and the log do
not know or care which provider consumes them.

## Non-goals

- **Building the second provider / the failover policy itself.** This change is
  the *enabler* (portable context); the Gemini-CLI adapter + failover trigger
  are separate, deferred work (per the analysis: build the contract now, defer
  the second provider behind an outage-frequency signal).
- **Ripping out Claude's own transcript** for Claude sessions — we *add* our own
  authoritative log; Claude's session resume still works for the Claude path.
- **The remote/cloud cockpit deployment** (parked by the founder).
- **A new founder-facing UI** for browsing the raw log — the raw is for the
  *agent's* discovery; any cockpit raw-view is out of scope here (the cockpit
  already has a transcript view it can later point at our store).
- **Deep brain Q&A / semantic retrieval** over the log — relevance selection
  starts simple (the bound change's entities + recency); smarter retrieval is later.

## Acceptance

Observable, provider-independent behaviour:

- **Every message is logged in our store.** After a session exchanges N
  prompts/messages, the Sulis-owned message log for that session/thread
  contains N records (role + timestamp + content + order), independent of
  Claude's `~/.claude/projects` files.
- **Resume recovers from OUR context.** A session can be ended and resumed — or
  restarted fresh — and the agent comes back with the rich payload (brief +
  Working Set + relevant entities + structured summary) **without reading the
  provider's stored transcript**. Delete/ignore the provider's transcript files
  and the resume still has full working context.
- **Raw on demand returns the full set.** The agent can request the raw record
  for the session/thread and receive the complete, correctly-ordered message
  log (or a requested slice).
- **The payload fits the budget.** The default (standard-tier) payload stays
  within a defined token budget — it carries the structured summary, not the
  raw dump; the raw is reached only via the discovery seam.
- **Provider-agnostic shape.** The payload + log are expressed in a
  Sulis-owned, vendor-neutral shape (no Claude-JSONL-specific assumptions), so
  the same payload could seed a non-Claude session.

## Constraints

- **Reuse, don't rebuild.** The `ProviderAdapter` seam, the provider-neutral
  event vocabulary, the brief/`pre_prompt` injection, the Working Set tool, and
  the brain are existing and are the inputs — this change adds the message log,
  the assembler, and the discovery seam, not a new architecture.
- **Append-only + ordered** message log (an audit record; never rewritten).
- **Rich-by-default / raw-on-demand** (progressive disclosure) — the default
  call never ships the raw dump; the window budget is a hard constraint.
- **Structured summary, freshly regenerated** at session/checkpoint boundaries
  (tie into the Working Set's crystallisation moments) so the rich payload
  doesn't go stale.
- **No secret leakage** into the log/payload beyond what the session already
  handles (honour the existing anonymiser/redaction posture; the log is a new
  persistence surface for message content — treat it with the same care).

## Verification Plan

How we'll know it works — the journeys to drive (each with an observable
outcome), provider-independence being the load-bearing one:

- **Every-message tracking:** run a session through several prompts → open the
  Sulis-owned log → **see** one ordered record per message (role + content +
  time).
- **Provider-independent resume (the key one):** run a session, capture some
  decisions; end it; **make the provider's transcript unavailable**; resume →
  **observe** the agent comes back with the rich payload (brief + Working Set +
  relevant entities + structured summary) and can continue coherently — proving
  recovery came from *our* store, not Claude's.
- **Raw on demand:** from a rich-payload session, have the agent request the raw
  full set → **observe** it receives the complete, correctly-ordered log.
- **Budget:** assemble a standard-tier payload for a long thread → **observe** it
  stays within the token budget (carries the summary, not the raw dump).
- **Provider-agnostic shape:** assemble the payload → **observe** it contains no
  Claude-JSONL-specific structure (vendor-neutral), so it could seed another
  provider.

**Third-party platform touch:** none in this change. (The later Gemini-CLI
adapter would be a platform touch; out of scope here.)

## Open questions for the design pass

- Where the message log physically lives (per-change under `~/.sulis/changes/…`
  alongside the brief/Working Set, vs a session-keyed store) and its exact
  record schema.
- How "relevant brain entities" are selected for the payload (start: the bound
  change's entities + recency; smarter retrieval later).
- The exact discovery-seam shape the agent uses to pull raw (a tool call vs a
  pointer in the payload) — reconcile with the safe-tools MCP model.
- The structured-transcript summariser: rule-based extraction from the log +
  Working Set vs a summarisation pass; freshness/checkpoint triggers.
