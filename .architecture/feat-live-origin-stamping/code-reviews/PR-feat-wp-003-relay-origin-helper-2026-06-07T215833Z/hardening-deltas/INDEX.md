# Hardening Deltas — PR feat/wp-003-relay-origin-helper

No draft fixes produced. The single low-severity quality observation (a
defensive unreachable branch in `LocalTranscriptConversationIdentity`) is an
intentional-robustness note on the Watch List, not a delta: it has no failing
characterisation test (CR-04) and removing the guard would be a regression
(coupling the adapter to `sessionStemFromRef`'s internal trimming).
