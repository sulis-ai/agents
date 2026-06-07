# Recorded `claude` stream-json fixtures

These are **recorded reality** (MEA-09 / contract §2.10), not hand-mocked JSON.
Each file is verbatim stdout from the real `claude` CLI (v2.1.165) run with
`--output-format stream-json`, captured once. The Claude `decode()` adapter
(WP-003) is driven by these lines so the mapping rules can never silently drift
from the real CLI's output shape.

| File | How it was captured | What it proves |
|---|---|---|
| `happy.jsonl` | `claude -p --output-format stream-json --include-partial-messages --verbose --dangerously-skip-permissions "Reply with exactly the two words: hello world"` | A normal turn: `system/init` (bookkeeping), `stream_event`/`content_block_delta` (chunks), `result`/`subtype=success`/`is_error=false` (the turn-terminal result with usage + stop_reason). |
| `error.jsonl` | `claude -p --output-format stream-json --verbose --model "no-such-model-xyz" "hi"` | A failed turn: the terminal `result` line carries `is_error=true` + `api_error_status=404`. Confirms `is_error` — not `subtype` — is the error discriminator (the line still reads `subtype:"success"`). |

To re-capture, run the commands above and overwrite the files. Keep them
verbatim — do not trim or reshape lines, or the fixtures stop being reality.
