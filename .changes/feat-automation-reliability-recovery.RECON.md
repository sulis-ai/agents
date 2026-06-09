# Recon — feat-automation-reliability-recovery

Stage 0 completed at: 2026-06-08T22:00:08Z

This marker indicates `/sulis:recon` has run for this change.

## Recon finding (corrected after back-integration from main)

NOTE: this branch was 78 commits behind origin/main at spawn (started at
860b6df2; main now 28059996). An initial recon pass against the stale
branch wrongly concluded the named seams were absent. After fast-forwarding
to origin/main the picture is clear: the seams EXIST and this is well-scoped
brownfield work for THIS repo.

The change extends the existing local autonomous-delivery-environment
session-manager package: `plugins/sulis/scripts/_session_manager/`.

Seams the intent names, mapped to actual code:
- "existing session-manager adapter seam"  -> `_session_manager/adapter.py`
  (`ProviderAdapter` Protocol: spawn_argv / encode / decode / turn_complete)
  with concrete providers in `_session_manager/adapters/` (claude.py,
  claude_pty.py). "Thin per-provider detection+re-auth" lands here.
- "the structured error stream"            -> `_session_manager/events.py`
  (`Event` kind="error", `EventError`, `ErrorCategory` =
  protocol|expected|internal, plus error-code constants SPAWN_FAILED,
  STDIN_BROKEN, SOCKET_CLOSED, NOT_AUTHORIZED, ...) + `event_log.py`.
  The reliability layer observes this stream.
- "platform messages store"                -> the ADE messages/event store;
  durable storage deferred to it (do not build a new store).

Supporting architecture already in repo:
- `.architecture/autonomous-delivery-environment/` — TDD, ARCH.yaml, SIZING,
  9 ADRs (chat stream, session-bridge resume/spawn, binding guard, etc.),
  contracts (openapi.yaml), features, work-packages.

The reliability classification (transient-blip retry+backoff / dead-end
abandon / login-expired pause+notify+resume) is a NEW layer on top of the
existing three-category error model.

Linked opportunity dna:opportunity:RD0MNJ3JHSER2SZVA4WA5B9PKT and
critical-thinking trace 01KTMJGQF2QEDZB7026AN3CZW1 were not found in this
repo's brain store (they may live in the founder's session context).

## Arrival-check note (non-blocking)

wpx-arrival-check reports default-branch=main where it expects dev (RC-01).
This is the arrival check lagging the trunk migration (#177 dev->main); the
repo intentionally uses main now. Not a repo gap — a stale check.
