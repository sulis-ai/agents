# Sulis Concierge

**The Sulis AI marketplace's VP of Engineering for non-technical founders.**

A founder shouldn't have to know which agent does what or when to
invoke them — any more than a CEO needs to know which engineer is
working on which ticket. The Concierge runs the whole journey from
"I have an idea" to "my product is built, tested, and security-
reviewed" — owning every process and technical-sequencing decision,
and bringing the founder only the calls that genuinely belong to a
CEO: product, users, business model, brand, risk appetite.

## Quick start

```bash
claude --agent sulis-concierge
```

The Concierge will greet you and ask what you're trying to build.
That's it — you answer plain-English questions; it does the rest.

## What the Concierge does

1. **Greet** you and capture your goal in plain English.
2. **Check** what already exists in your project (greenfield or
   brownfield).
3. **Help you specify** what the product needs to do (via a guided
   conversation with the requirements analyst).
4. **Get the technical design** drafted (via the engineering architect).
5. **Build it** (via the work-package executor).
6. **Verify** the build matches the design.
7. **Security-review** the finished product.

Every step is announced before it happens. You never have to remember
which command to run — the Concierge tells you when needed (in v0.1) or
runs it for you (in v0.2+).

## How the marketplace organises itself

The Concierge invokes specialist plugins on your behalf:

- `sulis-context` — discovers existing project material.
- `srd` — facilitates requirements gathering through guided conversation.
- `sea` — designs the technical architecture, breaks it into tasks,
  verifies the build.
- `sulis-execution` — actually writes the code, one task at a time,
  using Red-Green-Blue test-driven discipline.
- `sulis-security` — assesses for security/business risk issues.

For non-build paths (pitch decks, brand identity, business strategy),
the Concierge points you to:

- `idc` — investor deck coach.
- `sulis-design` — design system and visual identity.
- `sulis-strategy` — vision, strategy, pricing, GTM.

## What makes this different

The marketplace agents (SRD, SEA, sulis-security) are highly specialised
— they use technical vocabulary appropriate for their domain. Without
the Concierge, the founder has to know which to call, when, and how to
translate their output.

With the Concierge:

- One command to start: `claude --agent sulis-concierge`.
- Every output translated to plain English before you see it.
- Journey state persists across sessions in
  `.concierge/{project}/JOURNEY.md`.
- Specialists are invoked only when needed; you're never asked
  permission for routine technical decisions.

## What it's not

The Concierge is not:

- An engineer (the executor writes code).
- An architect (SEA designs systems).
- A requirements analyst (SRD facilitates specs).
- A designer or strategist (those are separate specialist plugins).
- A product manager (the founder owns *what* the product is).

It's the **VP of Engineering**: it owns *how* the product gets built
and directs the specialist team, while the founder owns *what* the
product is. That's the load-bearing role non-technical founders need
filled when working with an AI marketplace.

## Resume an existing journey

```bash
claude --agent sulis-concierge
/sulis-concierge:start
```

Reads your `.concierge/{project}/JOURNEY.md` and picks up where you
left off.

## See where you are

```bash
/sulis-concierge:status
```

Read-only snapshot of the current phase, completed steps, and next
action — all in plain English.

## License

MIT — see `LICENSE` in the repo root.
