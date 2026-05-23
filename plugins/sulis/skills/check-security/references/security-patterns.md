# Security Pattern Catalogue

Patterns the scanner checks for. Two categories: credential patterns
(regex-matched against literals in source) and dangerous-code patterns
(regex-matched against code constructs).

False-positive notes per pattern. v1 ships high-confidence patterns
only; lower-confidence patterns deferred until allowlist UX is solid.

## Credential patterns

### AWS

| Name | Pattern | FP risk |
|---|---|---|
| AWS Access Key ID | `\bAKIA[0-9A-Z]{16}\b` | Low — distinctive prefix |
| AWS Session Token | `\bASIA[0-9A-Z]{16}\b` | Low |
| AWS Secret Access Key (heuristic) | 40-char base64-ish near `AWS_SECRET_ACCESS_KEY` or `aws_secret` | Medium — depends on context proximity |

### GitHub

| Name | Pattern | FP risk |
|---|---|---|
| GitHub Personal Access Token (classic) | `\bghp_[A-Za-z0-9]{36}\b` | Very low |
| GitHub OAuth Token | `\bgho_[A-Za-z0-9]{36}\b` | Very low |
| GitHub User-to-Server Token | `\bghu_[A-Za-z0-9]{36}\b` | Very low |
| GitHub Server-to-Server Token | `\bghs_[A-Za-z0-9]{36}\b` | Very low |
| GitHub Refresh Token | `\bghr_[A-Za-z0-9]{36}\b` | Very low |
| GitHub Fine-Grained PAT | `\bgithub_pat_[A-Za-z0-9_]{82}\b` | Very low |

### Other providers

| Name | Pattern | FP risk |
|---|---|---|
| Stripe Secret Key | `\bsk_(live|test)_[A-Za-z0-9]{24,}\b` | Very low |
| Stripe Restricted Key | `\brk_(live|test)_[A-Za-z0-9]{24,}\b` | Very low |
| Stripe Publishable Key | `\bpk_(live|test)_[A-Za-z0-9]{24,}\b` | Low — publishable keys are PUBLIC; flagged advisory only |
| OpenAI API Key | `\bsk-[A-Za-z0-9]{48}\b` | Very low |
| Slack Bot/User Token | `\bxox[bpoa]-[0-9]+-[0-9]+-[0-9]+-[a-z0-9]+\b` | Very low |
| Slack Webhook URL | `https://hooks\.slack\.com/services/[A-Z0-9/]+` | Low — these ARE secrets |
| Anthropic API Key | `\bsk-ant-(api|tok)\d+-[A-Za-z0-9_-]{32,}\b` | Very low |

### Generic / heuristic

| Name | Pattern | FP risk |
|---|---|---|
| High-entropy near suspicious keyword | string of length 16+ near `(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]` with entropy ≥ 4.5 bits/char | Medium |
| Private Key Header | `-----BEGIN (RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----` | Very low |

## Dangerous code patterns

### Python

| Name | Pattern (heuristic) | Severity |
|---|---|---|
| `eval()` on potential user input | `eval\s*\(\s*(request\.|input\(|sys\.argv|os\.environ\[)` | High |
| `exec()` on potential user input | `exec\s*\(\s*(request\.|input\(|sys\.argv)` | High |
| `pickle.loads` on untrusted input | `pickle\.loads?\s*\(\s*(request\.|payload|data\b)` | High |
| `subprocess(shell=True)` with format-string | `subprocess\.(call|run|Popen)\s*\([^)]*shell\s*=\s*True[^)]*(%|f['\"]|\.format\()` | High |
| `os.system` with format-string | `os\.system\s*\(\s*(f['\"]|.*%|.*\.format\()` | High |
| Yaml load (unsafe) | `yaml\.load\s*\((?!.*Loader\s*=\s*yaml\.Safe)` | Concern |

### JavaScript / TypeScript

| Name | Pattern (heuristic) | Severity |
|---|---|---|
| `eval()` of dynamic value | `eval\s*\(\s*(?![\"'`])` | High |
| `new Function()` constructor | `new\s+Function\s*\(` | Concern |
| React `dangerouslySetInnerHTML` | `dangerouslySetInnerHTML\s*=` | Advisory (real uses exist; flag for review) |
| `innerHTML` assignment with variable | `\.innerHTML\s*=\s*[a-zA-Z_$]\w*` | Concern |
| `document.write` with variable | `document\.write\s*\([a-zA-Z_$]` | Concern |

### SQL injection (heuristic)

| Name | Pattern | Severity | FP risk |
|---|---|---|---|
| Format-string in SQL execute (Python) | `\.execute\s*\(\s*(f['\"]|.*%|.*\.format\()` | High | Medium |
| Template-literal in SQL execute (JS) | `\.query\s*\(\s*`[^`]*\$\{` | High | Medium |
| String concat in SQL execute | `\.(execute|query)\s*\(\s*['\"][^'\"]*['\"]\s*\+\s*` | High | Medium |

## Allowlist mechanics

### Path-based allowlist (pre-loaded)

Patterns SKIPPED automatically:

- `tests/fixtures/**`
- `__tests__/fixtures/**`
- `testdata/**`
- `mocks/**`
- `docs/examples/**`
- `**/security-patterns.md` (this file references patterns; would self-match)
- `**/.checkup/**` (skill state)
- `node_modules/**`, `.git/**`, `vendor/**`, `dist/**`, `build/**`

### Per-finding allowlist

`.checkup/{project}/security-allowlist.md` — founder-edited file with
one entry per line:

```
# AKIA1234567890ABCDEF: docs example, not a real key
# eval(JSON.parse(text)): we control the source, intentional
finding-id-or-pattern: reason
```

Allowlist matching is by exact finding signature (file + line + pattern name)
OR by literal-string match.

### Entropy threshold

High-entropy detection requires:
- Shannon entropy ≥ 4.5 bits/char
- Length ≥ 16
- Adjacent to suspicious keyword (within 50 chars before)
- Not contained in a comment block
- Not a documented allowlist entry

This combination keeps FP rate low while catching most real high-entropy
secrets.

## Adding a new pattern

To extend the catalogue:

1. Add a `Pattern` dataclass entry in `scripts/scanner.py`
   (`CREDENTIAL_PATTERNS` or `DANGEROUS_PATTERNS` list)
2. Document the false-positive risk in this file
3. Test against the marketplace + a synthetic fixture
4. Document the FP rate seen during testing

## What this catalogue does NOT cover

Per the SKILL.md "What this skill catches vs misses" table, the following
are explicitly out of scope:
- Auth-bypass logic errors
- Race conditions
- Business-logic flaws
- Cross-tenant data leaks
- Missing rate limiting
- Privilege escalation
- Time-of-check vs time-of-use (TOCTOU)
- Side-channel attacks

These require `sulis-security:codebase-assess` (25-primitive OODA-spiral
audit) or human security review.
