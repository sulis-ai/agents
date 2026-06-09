# Inspiration board — cockpit board refresh

Curated from Mobbin (web) for three founder concerns on the changes board.
Current state captured in `board-current.png` (6-column kanban: Recon→Ship).

## Concern 1 — Columns should be full height

The current columns size to their content (they stop after the last card). Every
mature board fills the viewport height and scrolls *inside* the column.

- **Trello** · [screen](https://mobbin.com/screens/c6ccc5a7-b2d0-46cb-a7f4-a3d9435b18ef) — columns are full-height lanes; the list header is sticky, cards scroll within, the "+ Add a card" pins to the bottom.
- **Jira board** · [screen](https://mobbin.com/screens/8ae369e0-fe5c-43d0-b2da-2509daa2e3c6) — full-height columns with a tinted lane background, count in the header, "+ Create" per column.
- **GitHub Projects** · [screen](https://mobbin.com/screens/c4b0e743-6a1f-4d52-9b81-2f72cca5f592) — full-height columns, "+ Add item" pinned at the bottom of each.
- *Steal:* the column is a full-height lane (sticky header + internal scroll + a pinned bottom action). The board fills the viewport; columns don't float as short cards.

## Concern 2 — The stage pill on each card is duplicative (column already says the stage)

Every card carries a "RECON · 1/6" pill that repeats its column. Good boards put
**information the column doesn't already convey** on the card instead.

- **Trello cards** · [screen](https://mobbin.com/screens/7ca44382-f961-4093-b11e-bd925e4283d7) · [screen](https://mobbin.com/screens/5e62cc85-b58f-472f-b425-b0a30ccecfc5) — card foot shows **comment count, checklist progress (0/2), attachment count, due date, member avatars** — never the list's own name.
- **ClickUp** · [screen](https://mobbin.com/screens/6ab16201-dbf4-470e-ad65-cf7d2d916822) — compact metadata row (assignee, dates, tags) under the title.
- *Steal:* replace the redundant stage pill with 1–3 **at-a-glance signals the column can't tell you**. Candidates the cockpit can actually compute (it already has the transcript + the diff):
  - **Conversation length** — message/turn count (Trello's comment-count idiom).
  - **Files changed** — count from the change's diff.
  - **Liveness / last active** — is a session live now; recency made prominent.
  - The slim **"· N/6" progress** can stay as a tiny step indicator (it's the one non-redundant part of the old pill) — but drop the stage *name*.
- *Avoid:* a label that just re-states the column. One genuinely-informative signal beats a redundant badge.

## Concern 3 — There's no visible "add a change" affordance

The board has no way to start a change. Two complementary patterns:

- **Global new action** — Jira/GitHub/Trello all keep a prominent **"+ Create" / "New"** in the top bar, always visible. (For Sulis this is the "Start something new" button — the parked `CH-01KTMF` work — which belongs in the persistent top bar so it shows on the board too.)
- **Per-column add** — Trello "+ Add a card", Jira/GitHub "+ Create / Add item" pinned at the bottom of each column.
- *For Sulis specifically:* a change always **starts at Recon** (you don't add one directly to "Review"), so a **single global "Start something new"** in the top bar is the right primary affordance — not a per-column add. The per-column "+" pattern doesn't map to the change lifecycle. (A subtle "+ Start here" only under the Recon column could be a secondary touch, optional.)

## Cross-cutting takeaways

1. **Full-height lanes, internal scroll, sticky headers, pinned bottom action.**
2. **Cards earn their badges** — show what the column can't (conversation length / files changed / liveness), drop the stage name.
3. **One always-visible "Start something new"** in the top bar (revive the parked button), not a per-column add — because changes start at Recon.
