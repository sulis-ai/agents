<!-- canonical:step:gather-ambiguous-fields -->

# Fields the repo can't reveal

A few fields the Infer phase can't guess from your repo — they live
only in your head. Ask the founder directly. One question per
prompt. Required questions block the loop; optional questions accept
an empty answer.

## Required prompts

The project must have a name before the entity can be written. If
the repo doesn't reveal a reasonable default (no clear package name,
no clear repo slug), ask outright:

```
What should we call this project?
> _
```

The answer becomes the human-readable name on the Project entity.
The slug (filename on disk) is derived deterministically from this
name — same input, same slug, no surprises.

## Optional prompts

Description, brief, longer-form context — everything that helps a
future you remember what this project does. Skipped if blank.

```
Anything else worth knowing about this project? A short description
helps when you're looking at it six months from now.
[optional — press Enter to skip]
> _
```

```
Who should I tag for code questions? Comma-separated handles or
emails work.
[optional — press Enter to skip]
> _
```

## What happens if you press Enter on a required prompt

The skill re-prompts. Required fields cannot be left empty — leaving
the project nameless would produce an entity that can't be filed.
The re-prompt repeats the same question with a one-line nudge:

```
A name is required so the entity has somewhere to live on disk.
What should we call this project?
> _
```

## Cancel semantics

Ctrl-C at any point in the ambiguous-fields loop drops every answer
the founder typed and exits cleanly. No partial entity is written.
The next discovery run starts fresh.
