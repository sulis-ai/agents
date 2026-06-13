# Sandbox-enable recipe — the OS backstop (locus iii)

> **Status:** shipped defaults + recipe. **Enforcement-locus:** iii (OS).
> **Threat-scope:** closes GAP-α (accidental over-reach) **only when enabled**;
> GAP-β (deliberate TLS exfil) **DEFERRED**. **Single source of truth:** the
> writable paths are generated from `sandbox_write_roots` (ADR-004) — never
> hand-maintained.

Claude Code **ships** an OS sandbox (macOS Seatbelt / Linux bubblewrap). Sulis
does **not** build one. This recipe enables and configures the shipped sandbox
with safe defaults, so that a spawned subprocess — the one thing the harness
PreToolUse hook (locus ii) can never see — is contained.

This is **locus iii (OS)**: the only layer that catches an adversarial
subprocess bypass (`python -c 'urllib…'`, an obfuscated `curl`). Locus i (prose)
is advisory; locus ii (the hook + permission rules) catches recognised direct
tool calls; **locus iii is the wall.** Each layer is labelled by what it
actually delivers — nothing here claims more safety than the OS gives.

---

## What the sandbox closes — and what it does not (be honest)

| Threat | Locus | Status with this recipe |
|---|---|---|
| **GAP-α — accidental over-reach** (a tool or subprocess writes/reads outside scope by mistake) | iii (OS) | **Closed — only when the sandbox is enabled.** Until a consumer enables it, the hook (locus ii) catches the *recognised* calls; subprocesses still slip. |
| **GAP-β — deliberate TLS exfil** (data smuggled over TLS to a permitted domain; domain-fronting) | — | **DEFERRED / roadmap.** The sandbox network proxy does **not** inspect TLS (verified in the Claude Code sandboxing docs). A broad `allowedDomains` therefore permits domain-fronting exfil. The mitigation here is to set `allowedDomains` to the **safe-fetch proxy egress host only** — but a TLS-aware safe-fetch-only egress proxy is **not built**. Named, not claimed closed. |
| **Operator-proof (unbypassable by the operator)** | iii (OS), managed | **Consumer-owned (SC-E9).** Requires consumer-applied **managed** settings (`failIfUnavailable` / `allowUnsandboxedCommands:false`). Sulis ships the recipe + defaults; it **cannot impose** managed policy on a downstream host. |

**Deferred-attested scenarios** (labelled, never faked green):

- **SC-E7 (sandbox-blocks half)** — that the enabled sandbox actually blocks a
  subprocess bypass. The *bypass-succeeds-without-the-sandbox* half is automated
  (WP-003); the *sandbox-blocks-it* half needs a sandbox-enabled host and is
  **human-attested / CI-where-available**.
- **SC-E8 (real session inside the sandbox)** — a real `claude --agent sulis`
  session completes a trivial change end-to-end inside the enabled sandbox with
  the resolver-computed allowlist, nothing legitimate blocked. **Driven /
  attested** on a sandbox-enabled host.
- **SC-E9 (operator-proof)** — as above: consumer-managed, **documented, not
  claimed**.

What an attested SC-E7/E8 run must show, and who owns it:

- **Show:** with the block below applied and the sandbox enabled, a raw
  subprocess egress (`python -c 'import urllib.request; urllib.request.urlopen("http://example.com")'`)
  is **refused** at the OS layer, while the agent's legitimate in-scope writes,
  `sulis-*` / `wpx-*` CLIs, and `safe_fetch` research all succeed.
- **Owner:** the consumer / operator running on a Seatbelt or bubblewrap host
  (the `sandbox-enabled-host` infrastructure need). Sulis cannot attest it in
  CI on a host without the sandbox.

---

## The recipe — generate the block, do not hand-write it

The `filesystem.allowWrite` list is the **single source of truth** shared with
the L2 file-tools scope check. It is **generated** from the write-roots resolver
(`sandbox_write_roots`, ADR-004) — never hand-maintained, so it cannot drift
from what the file-tools actually permit.

Run the generator (it reads the change scope from the launch environment):

```bash
SULIS_CHANGE_ID="$SULIS_CHANGE_ID" SULIS_REPO_ROOT="$SULIS_REPO_ROOT" \
  sulis-sandbox-config --proxy-host egress.proxy.internal
```

It prints a `sandbox` block ready to merge into `settings.json`:

```jsonc
{
  "sandbox": {
    "enabled": true,
    "filesystem": {
      // GENERATED from sandbox_write_roots() — do NOT hand-edit. Re-run the
      // generator if the change scope (worktree / relocated brain) changes.
      "allowWrite": [
        "/private/var/.../worktree",
        "~/.sulis/changes/<THIS_ID>/",
        "..."
      ],
      // Credential dirs: the default read policy ALLOWS these unless denied.
      "denyRead": ["~/.aws", "~/.ssh"]
    },
    "network": {
      // The safe-fetch proxy egress host ONLY. A broad allowlist is the GAP-β
      // exfil surface — keep this to the one proxy host.
      "allowedDomains": ["egress.proxy.internal"]
    }
  }
}
```

> The sandbox auto-allows a linked worktree's shared `.git` (verified in the
> docs), so the git-common-dir entry the generator emits is partly redundant
> *under the sandbox* — but the L2 file-tools check still needs it, and emitting
> it keeps both consumers reading one set (ADR-004). Harmless; documented rather
> than special-cased out.

### Strict (consumer-managed, operator-proof) variant

Operator-proof (SC-E9) needs **managed** settings — applied by the consumer's
device-management / managed-settings layer, which only a consumer controls.
Generate the strict block with:

```bash
sulis-sandbox-config --proxy-host egress.proxy.internal --strict
```

which adds:

```jsonc
{
  "sandbox": {
    "enabled": true,
    "failIfUnavailable": true,        // refuse to run unsandboxed (no silent fallback)
    "allowUnsandboxedCommands": false // no per-command escape hatch
    // ... filesystem / network as above
  }
}
```

Apply these as **managed** settings to make them unbypassable by the operator.
Sulis ships this recipe and the defaults; it cannot impose the managed policy
on a downstream host. This is the honest boundary of locus iii: the wall is real
only once a consumer builds it.

---

## Cross-references

- **ADR-004** (`.architecture/harden-embed-safe-tools/adrs/ADR-004-write-roots-resolver-single-source.md`)
  — one resolver, two shapes (Python roots + this sandbox emit). The
  single-source guarantee made structural.
- **WP-002** (`_file_scope.sandbox_write_roots`) — the generator's only source
  of writable paths.
- **WP-005 — the governed-action-surface standard** — the durable home of the
  enforcement-locus / threat-scope labelling rule; it references this recipe as
  the locus-iii backstop and its `test_locus_honesty.py` reads these labels.
- **Prior change L3 deferral** — `harden-agent-execution-boundary/TDD.md` named
  the OS sandbox (`l3-os-egress-denial`) as the follow-on wall to L1+L2; this
  recipe is that follow-on, enabling the shipped sandbox rather than building
  one.
- **Verified contract** — Claude Code sandboxing docs
  (https://code.claude.com/docs/en/sandboxing): `sandbox.enabled`,
  `filesystem.allowWrite` / `denyRead`, `network.allowedDomains`, and the
  managed `failIfUnavailable` / `allowUnsandboxedCommands`.
