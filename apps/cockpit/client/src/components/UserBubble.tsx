// WP-003 — <UserBubble>: the founder's message bubble in a Turn-Cards thread.
//
// Extracted at the 2-consumer threshold (EP-03 / Non-Negotiable #2): the
// in-change chat (`Chat.tsx`) and the universal chat (`ProductChat.tsx`) both
// render the founder's grouped `UserItem` as the exact same neutral bubble.
// Once WP-003 made the universal chat a second consumer of this byte-identical
// markup, the shared primitive must be extracted — in the same change, not
// later. The agent turn renderer is NOT shared here: the two chats differ on
// the turn (the in-change card carries a generated summary; the universal card
// uses the first-sentences fallback, ADR-003), so only the genuinely-identical
// user bubble is lifted.
//
// User text is rendered VERBATIM — never markdown-parsed (spec non-goal: user
// messages are shown exactly as typed).

import type { UserItem } from "../lib/groupTurns";
import { formatRelativeTime } from "../utils/relativeTime";
import convo from "../styles/Conversation.module.css";

interface Props {
  item: UserItem;
}

export function UserBubble({ item }: Props) {
  return (
    <div className={convo.msgUser} data-testid="chat-message-user">
      <div className={convo.who}>You</div>
      <div className={convo.say}>{item.text}</div>
      <div className={convo.userTime}>{formatRelativeTime(item.timestamp)}</div>
    </div>
  );
}
