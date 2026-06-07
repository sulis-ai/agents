// Chat-redesign (chat-B2) — the turn-grouping model now lives in `shared/`
// so the server (which summarises turns) and the client (which renders them)
// produce the SAME per-turn keys. This file re-exports it for the existing
// client import paths.

export * from "../../../shared/groupTurns";
