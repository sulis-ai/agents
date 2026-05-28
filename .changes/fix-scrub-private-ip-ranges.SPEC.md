---
founder_facing: false
---
# Spec — scrub private IP ranges (closes #40)

**Closes:** [#40](https://github.com/sulis-ai/agents/issues/40)

## What this should do

Scrub IP addresses in private / loopback / link-local ranges; preserve
globally-routable ones (likely public DNS / well-known service IPs
that the maintainers may need to see).

### Categories scrubbed → `<ip>`

| Family | Range | RFC |
|---|---|---|
| IPv4 private | `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` | RFC 1918 |
| IPv4 loopback | `127.0.0.0/8` | — |
| IPv4 link-local | `169.254.0.0/16` | RFC 3927 |
| IPv6 ULA | `fc00::/7` | RFC 4193 |
| IPv6 loopback | `::1` | — |
| IPv6 link-local | `fe80::/10` | RFC 4291 |

### Categories PRESERVED (globally-routable / well-known)

- `8.8.8.8`, `1.1.1.1` (public DNS — maintainer context)
- `2001:4860::8888` (Google public DNS)
- Any other public IPv4/IPv6 that's not in the above ranges

### Implementation approach

Use Python's stdlib `ipaddress` module — it knows all the relevant
ranges via `is_private`, `is_loopback`, `is_link_local`. Avoids
hand-coding range checks (which the lesson body itself starts to
do, then suggests RFC-citing — `ipaddress` IS the citation).

1. New regex `_IP_ADDRESS` matches IPv4 dotted-quads AND IPv6 strings
   (including the compact `::` form).
2. New `_replace_ip(match, keep)` replacement function:
   - `_is_kept(s, keep)` short-circuit (founder opt-in)
   - Parse via `ipaddress.ip_address(s)`. On parse failure → preserve
     (false-positive caught the regex match).
   - If `is_private or is_loopback or is_link_local` → `<ip>`.
   - Else → preserve.
3. Add to `_PASSES` between `<domain>` and `<project>` (the
   broadest passes already at the end).

## How we'll know it's done

- New tests:
  - Each documented range: pinned redaction (e.g. `192.168.1.1` →
    `<ip>`, `10.0.0.5` → `<ip>`, `fc00::1` → `<ip>`)
  - Each well-known public IP preserved (`8.8.8.8`, `1.1.1.1`,
    `2001:4860::8888`)
  - Non-IP-shaped numbers in text NOT misclassified (e.g. version
    strings `3.11.2`, port numbers `8080`)
  - Keep-list short-circuit honoured
- Full anonymiser test suite still GREEN (no regression on the
  other 8 categories).
- Step 4.5 review gate PASS.

## What to avoid

- **Do NOT hand-code the range bounds.** Use `ipaddress` stdlib.
  Hand-rolled regex bounds for CIDR ranges drift; the stdlib doesn't.
- **Do NOT scrub version strings or other dotted-quads.** A version
  like `3.11.2` has only 3 octets and won't match a v4 IP regex
  (needs 4). A timestamp like `1.2.3.4` is the corner case — the
  regex matches but `ipaddress.ip_address` parses to the (correct)
  `1.2.3.4` which is NOT private — preserved. Good.
- **Do NOT scrub public IPs.** Globally-routable IPs in feedback
  bodies usually identify public services (DNS, well-known APIs)
  that the maintainer triage needs.

## References

- `plugins/sulis/scripts/_anonymiser.py`
- `tests/unit/test_anonymiser.py`
- Issue [#40](https://github.com/sulis-ai/agents/issues/40)
- Python stdlib `ipaddress` module
