# Reliability Pattern Catalogue

Patterns the scanner detects. Three categories, kept narrow for low FP rate.

## Missing-timeout patterns

Each pattern matches a call WITHOUT a `timeout=` kwarg on the same line
or within 3 lines (multi-line call). asyncio.wait_for wrapping
(detected in preceding 3 lines) suppresses the finding.

### Python

| Library | Call pattern | Timeout convention |
|---|---|---|
| `requests` | `requests.{get,post,put,patch,delete,head,options,request}(` | `timeout=N` kwarg |
| `httpx` | `httpx.{get,post,put,patch,delete,head,options,request}(` | `timeout=N` kwarg |
| `subprocess` | `subprocess.{run,call,check_call,check_output,Popen}(` | `timeout=N` kwarg (Popen needs `.wait(timeout=N)`) |
| `urllib` | `urllib.request.urlopen(` | `timeout=N` arg |
| `socket` | `socket.create_connection(` | `timeout=N` kwarg |

### Async exemption

asyncio-style timeouts look different. If the preceding 3 lines contain
`asyncio.wait_for` or `wait_for`, the call is considered wrapped:

```python
# NOT flagged — async timeout wrapping
result = await asyncio.wait_for(
    aiohttp_session.get(url),  # this call has no timeout= kwarg, but it's wrapped
    timeout=30,
)
```

### Library-specific timeout aliases

Some libraries use different parameter names. v1 catalogue knows:
- `requests` / `httpx`: `timeout=`
- `aiohttp`: `timeout=ClientTimeout(total=N)` — not yet detected (deferred to v1.1)
- `boto3`: `Config(connect_timeout=, read_timeout=)` — not yet detected
- `kafka-python`: `request_timeout_ms=` — not yet detected

If your project uses one of the deferred libraries, add a custom-pattern
allowlist entry to `.checkup/{project}/check-reliability-allowlist.md`
until v1.1 ships explicit support.

## Silent-except patterns

Detects:

```python
try:
    something()
except:
    pass

# or

try:
    something()
except Exception:
    pass

# or

try:
    something()
except Exception as e:
    pass
```

The detector looks at the next non-blank, non-comment line after the
`except:` — if it's a bare `pass`, the finding fires.

NOT detected (out of scope for v1):
- `except: continue` in a loop (also a swallow but harder to distinguish from legitimate retry control)
- Multi-line bodies that effectively pass (`x = None; pass`)

## Broad-except patterns

Detects:

```python
try:
    something()
except Exception:
    log.error("oops")
    # no raise

# or

try:
    something()
except:
    log.error("oops")
    # no raise
```

The detector looks at the except-body (until dedent or 12 lines max).
If the body contains `raise` / `raise X` / `reraise(`, NOT flagged
(re-raise is the correct wrap pattern).

NOT detected:
- `except Exception:` followed by re-throw via custom exception (most
  cases are caught by `raise X` pattern, but framework-specific
  re-throws via `self.fail(...)` etc. are missed — v1 limit)

## Anti-pattern: things that LOOK like bugs but aren't

These patterns are deliberately NOT flagged:

| Pattern | Why not flagged |
|---|---|
| `try: ... except Exception: log.error(...); raise` | Canonical wrap-and-rethrow; re-raise detected |
| `try: ... except ValueError: ...` | Specific exception type; legitimate |
| `requests.get(url, timeout=30)` | Has timeout |
| `subprocess.run(["ls"], timeout=10)` | Has timeout |
| `await asyncio.wait_for(coro, timeout=30)` | Async timeout wrapping |
| `try: ... finally: ...` | finally is cleanup, not error swallow |
| `except Exception as e: return None  # by-design fallback` | Caught at concern severity; founder reviews |

## Adding a new pattern

To extend the catalogue:

1. Add a `(call_re, timeout_re, name, message, suggestion)` tuple to
   `MISSING_TIMEOUT_PATTERNS` in `scripts/scanner.py`
2. OR add a new top-level pattern check function for a different
   category (e.g., `scan_observability_gap()`) and call it from
   `scan_file_python()`
3. Document the new pattern in this file (signal + intent + FP risk)
4. Test against the marketplace + synthetic fixture

## What this catalogue does NOT cover

Per SKILL.md "What this skill catches vs misses":
- Distributed-systems patterns (retries / circuit breakers / bulkheads)
- Data integrity (flush / fsync / transactional boundaries)
- Idempotency (replay-safety, dedup-via-keys)
- Chaos test coverage
- Async cancellation correctness
- Resource leak detection (sockets / file handles / DB connections)

These require deeper analysis. Use `sulis-security:codebase-assess`
(Armor pillar — 25 primitives, OODA-spiral).
