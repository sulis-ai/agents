# Recon — create-portable-agent-context

Stage 0 completed at: (see git) — investigation of #2 (portable context payload).

## The decisive finding
The "rich vs raw" split ALREADY half-exists in the cockpit — but the raw is the
WRONG owner:
- RICH (folded/curated): useTurnSummaries — Sulis-shaped turn cards. ✓
- RAW (full messages): useTranscript → locateTranscripts(worktreePath,
  claudeProjectsDir) — i.e. it reads CLAUDE'S OWN session transcript JSONL from
  ~/.claude/projects. So the raw record today is PROVIDER-STORED (Claude's
  transcript files), NOT Sulis-owned. This is exactly the lock-in the
  critical-thinking analysis flagged.

So the gap = a SULIS-OWNED per-session/thread message log: track each
prompt/message in our own store (provider-agnostic), so the agent can pull the
full raw set without depending on Claude's transcript files. That message log,
plus a curated payload assembled from the sources we already own, IS #2.

## What already exists to build on (Sulis-owned, portable)
- Working Set (sulis-working-set): structured live reasoning state — Problem /
  Current best solution / Decisions-in-flight / the why / Rejected-with-rationale
  / append-only log. Crystallizes into brain entities at boundaries.
- Brain (sulis-brain-query, .brain entities): durable Opportunity / Requirement
  / Decision / Design / Scenario entities.
- Brief / CONTEXT.md: the pre_prompt brief injected as an argv element into the
  spawned agent (already Sulis-owned + injected, not via provider memory).
- Provider-adapter seam (_session_manager/adapter.py): ProviderAdapter Protocol
  + Capabilities + provider-neutral event vocabulary — the injection point.

## The shape (rich-by-default, raw-discoverable, progressive disclosure)
1. A Sulis-owned MESSAGE LOG: append every prompt/message per session/thread to
   our own store (keyed by session/thread; provider-agnostic).
2. A PAYLOAD ASSEMBLER: build the curated rich payload from Working Set + relevant
   brain entities + brief + a STRUCTURED/summarised transcript (not the raw log).
3. A DISCOVERY SEAM: the agent gets the rich payload by default + a tool/pointer
   to fetch the raw full set on demand.
4. Provider-agnostic: this is the enabler for headless failover (re-inject our
   own context into any provider as a fresh session) + hardens resume/audit and
   removes Claude-transcript lock-in.

## Suggested next step
/sulis:specify — scope the capability + author verification journeys.
