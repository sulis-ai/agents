---
founder_facing: false
---
# Spec — fix anonymiser URL userinfo handling (closes #39)

**Change:** fix · CH-01KSNY (autonomous session 2026-05-28)
**Closes:** [#39](https://github.com/sulis-ai/agents/issues/39)

## What this should do

When the anonymiser's URL pass encounters a URL with embedded
credentials (RFC 3986 `userinfo@` between scheme and host),
ALWAYS redact the full URL to `<url>` — regardless of whether the
host is on the public-domain allowlist.

### The bug

`_extract_host_from_url` in `_anonymiser.py:259-266` strips the scheme
then splits on `[/:?#\s]`. For `https://user:password@host/path` the
split-on-`:` produces "user" as the "host". Today this is lucky-safe
("user" doesn't match the allowlist so the URL falls through to
`<url>`), but if the parser is ever "fixed" naively to strip userinfo
without redacting the URL, credentials in allowlisted-host URLs would
leak.

### The fix

1. Add `_url_has_userinfo(url) -> bool` predicate. True iff there's
   `userinfo@` between the scheme and the next slash/end. Matches the
   RFC 3986 form `[user[:password]]@`.
2. In `_replace_url`: check userinfo FIRST. If present and not in
   the keep-list, return `<url>` immediately — skip the allowlist
   check entirely. Credentials are always sensitive.
3. Keep the existing host-allowlist logic for URLs without userinfo
   (unchanged).

## How we'll know it's done

- New tests:
  - URL with `user:pass@github.com/...` → `<url>` (NOT preserved
    despite allowlisted host)
  - URL with `user@github.com/...` (user-only, no password) → `<url>`
  - URL with `user:pass@private.com/...` → `<url>` (same outcome
    as today; pinned)
  - URL with NO userinfo on allowlisted host → preserved (regression
    pin)
  - URL with NO userinfo on non-allowlisted host → `<url>` (regression
    pin)
- `_url_has_userinfo` unit-tested directly: positive on common
  userinfo shapes; negative on path-only URLs, query strings, fragments.
- Existing 29 anonymiser tests still pass.
- Full unit + integration suite green.
- Step 4.5 review gate (#30) PASS.

## What to avoid

- **Do NOT try to "extract the host" from a userinfo-bearing URL.**
  The lesson body explicitly says: credentials are sensitive, the
  whole URL should be redacted, no allowlist evaluation.
- **Do NOT add userinfo to the runtime keep-set.** Even if the
  founder opts to keep the URL via the preview gate, the URL going
  to the public issue is the ORIGINAL with credentials — that's
  the founder's call but it's not something to make easier.

## References

- `plugins/sulis/scripts/_anonymiser.py` — `_extract_host_from_url`
  (lines 259-266) + `_replace_url` (lines 269-281)
- `plugins/sulis/scripts/tests/unit/test_anonymiser.py` — URL tests
  start around line 138
- Issue [#39](https://github.com/sulis-ai/agents/issues/39)
