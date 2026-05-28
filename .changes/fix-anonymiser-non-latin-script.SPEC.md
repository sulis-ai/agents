---
founder_facing: false
---
# Spec — NFKC-normalise input + explicit re.UNICODE on project pass (closes #41)

**Closes:** [#41](https://github.com/sulis-ai/repos/agents/issues/41)

## Bug

ASCII-only regex character classes (`[A-Za-z0-9_]`) skip:
- Full-width ASCII lookalikes (`ＳＴＲＩＰＥ＿ＳＥＣＲＥＴ＿ＫＥＹ` visually
  identical to `STRIPE_SECRET_KEY`).
- Compatibility-decomposable forms.

Probe (today's behaviour, captured):
```
ＳＴＲＩＰＥ＿ＳＥＣＲＥＴ＿ＫＥＹ=ｓｋ_ｌｉｖｅ_abc123def456ghi789jklmno
→ 0 redactions (passes through unchanged)
```

After NFKC normalisation this collapses to the canonical ASCII form
(`STRIPE_SECRET_KEY=<sk-live-shape-token>`) which the existing
env-secret pass catches correctly.

## Fix

1. NFKC-normalise the input at the start of `anonymise()` via
   `unicodedata.normalize('NFKC', text)`. The redacted output is the
   normalised form — slightly different to the original input but
   visually equivalent (NFKC is the unicode-compatibility composition
   form; full-width chars collapse to ASCII; lookalikes that
   compatibility-decompose normalize to their canonical form).
2. Project-name pattern: add explicit `re.UNICODE` flag. Python 3
   regex is unicode-aware by default, but the explicit flag documents
   intent for future readers and guards against subtle behaviour
   drift in future Python versions.

**What this DOES NOT fix:** homograph attacks (e.g. Cyrillic `а` (U+0430)
in place of Latin `a` (U+0061)). These are visually identical but
distinct code points; NFKC does NOT canonicalise them. Catching these
requires a confusable-script detection layer (e.g. unicode TR39).
Surfaced as **future-work follow-up** if needed.

## How we'll know it's done

- New test: full-width-secret input → redacted to
  `STRIPE_SECRET_KEY=<secret>` (or similar shape).
- New test: full-width email → redacted to `<email>`.
- New test: project-name pattern works for Cyrillic, Chinese,
  Arabic names (pinned regression — already works in Python 3 but
  worth pinning).
- New test: homograph-attack case explicitly noted as out-of-scope
  via a `skip` or `xfail` with rationale.
- Existing 63 anonymiser tests still pass (no regression on ASCII).
- Step 4.5 review gate PASS.

## What to avoid

- **Do NOT touch the email/secret regexes themselves.** NFKC at the
  ingress handles the lookalike problem without widening the regex
  surface (which would risk over-matching).
- **Do NOT attempt homograph detection in this change.** Defer to a
  follow-up if a real homograph-attack scenario surfaces.

## References

- Python stdlib `unicodedata.normalize('NFKC', s)` —
  https://docs.python.org/3/library/unicodedata.html#unicodedata.normalize
- Unicode TR39 — Security mechanisms (for future homograph-attack work)
