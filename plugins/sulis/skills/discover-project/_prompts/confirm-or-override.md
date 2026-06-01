<!-- canonical:step:confirm-or-override-inferences -->

# Confirm or override the proposed values

The Infer phase produced a guess for every configuration value the
skill could read from your repo (your main branch, where you publish
releases, your release cadence, your package manifests, and so on).
Walk through each one. Press **Enter** to keep the guess. Type a new
value to override it.

One field at a time. No bulk-accept shortcut — every proposed value
needs an explicit keep-or-override from you. This is the
consumer-confirmation gate: nothing the LLM proposed reaches the
written Project entity without you saying yes to it.

## Prompt template

For each proposed value, render exactly:

```
<friendly-name> — proposed: <inferred-value>
Keep that, or type a new value to override?
[Enter] to keep · type a new value to override
> _
```

`<friendly-name>` is the plain-English version of the configuration
field. The rendered prompt never names the underlying schema field
directly — the founder reads "where you publish releases", not the
raw machine identifier.

## Friendly-name dictionary

The Configuration Vocabulary field names get rendered as:

| Schema field | Friendly name in the prompt |
|---|---|
| `primary_branch` | your main branch |
| `release_branch_model` | how you cut releases |
| `deploy_target` | where you publish releases |
| `package_manifest_path` | your package manifest |
| `ci_provider` | your CI provider |
| `release_cadence` | how often you ship |
| `versioning_scheme` | how you version |
| `language_runtime` | your primary language and runtime |
| `test_command` | how you run your tests |
| `lint_command` | how you lint your code |
| `build_command` | how you build a release artifact |
| `pull_request_required` | whether changes need a pull request |

If the Infer phase couldn't propose a value (the repo didn't reveal
it), the field is handled by the ambiguous-fields prompt instead, not
here. This loop only walks the proposed values.

## What happens to your answers

Each kept-or-overridden answer is held in memory until every prompt
in this loop is answered. Once you've walked every one, the next
phase writes them to your Project entity as a single atomic update —
nothing partial reaches disk. If you cancel before the loop
completes (Ctrl-C, or close the terminal), nothing is written and
the discovery starts fresh next time.
