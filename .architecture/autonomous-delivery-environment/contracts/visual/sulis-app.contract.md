# Visual contract — Sulis app surface (CH-01KT50)

```yaml
kind: contract
contract_type: visual
surface: sulis-app
mockup: contracts/visual/sulis-app.html
inspiration: contracts/visual/_mobbin-context.md   # inspiration: Mobbin (real probe, web; structure-only per UXD-15)
signed_off_at: 2026-06-04T08:18:04Z    # founder signed off on the FULL surface — cockpit (per-product board + switcher, thread, brain, previews, search), two-way chat, AND the new concierge / conversational-setup / multi-product surfaces. Locked: repo create = local-only by default; one product per setup conversation; neutral two-letter product tile. The #45 gate is passed.
provenance: production-approved        # founder-approved (DS-07): AI-generated → human-reviewed → production-approved.
supersedes: ../mockups/SULIS-APP-surface.mockup.html   # the architect's rough stand-in
```

One coherent surface (ADR-005): board → thread, six parts sharing one shell, one
token system, one state/empty/error pattern set, shown in **both light and dark**.

---

## Eighth pass — the NEW surfaces: concierge, conversational setup, product switcher, per-product board (current)

This pass adds the four user-facing surfaces of scope **#7** (the chat concierge
/ onboarding) and **#8** (multi-product) on top of the existing signed base —
everything from passes 5–7 (the fragment token system, the board, the thread,
the file explorer, the simplified dot+label states) is **kept unchanged**; these
are *additions*, bound to the same design instance. Every colour and font is the
same fragment-token system; no new colour is invented. A **second Mobbin probe**
(`_mobbin-context.md` §New surfaces) grounds the *structure* of each; UXD-15
applied strictly — only layout/ordering/interaction beats transfer, no palette
or screenshot.

### The four new surfaces (Mobbin-grounded; visuals stay ours)

1. **Conversational setup / onboarding** (panels 13–16, light; FR-27/28/35/36,
   UC-07). When nothing is set up yet, the concierge runs setup as a **guided
   conversation, not a form** (a form can't pick from an empty graph). Step 1
   *"which product?"* → step 2 *"where's the code?"* with the **find-or-create
   branch**: **connect an existing repo** (pick from a list **or** paste a URL)
   **or create a new one** (name + private/public/local). Grounded in the
   **Vercel / Replit / Render / GitHub** "import existing (list/URL) OR create
   new" split — wrapped in chat, one step at a time (CL-02). Creating a repo is
   **confirmed first** via the reused consent gate (FR-N6/N10): the concierge
   shows a plain-English **proposal recap** (product · new repo · project) then
   asks *go ahead / not yet*. End state: a **"your product is set up"** screen →
   the board appears, with the durable config saved.

2. **Concierge front door** (panel 17, light; 19, dark; FR-27/33/34, UC-09/10).
   The chat that finds changes, reports status, answers read-only, onboards, and
   starts changes — **coordinates only, never does the work itself**. Two
   concierge-specific structures: a **read-only answer card** that surfaces the
   found change(s) and **points** at the card (with an honest *"I only looked —
   nothing was changed"* chip — FR-N8), and the **investigation → change
   spin-up** card: an investigation **visibly creates a change to hold it**
   (after confirm), never runs inline (FR-N9). **Reuses the existing chat
   composer** (suggestion chips + slash commands + free text) verbatim. Grounded
   in the **Replit-agent** thread + **⌘K command-palette** (Fibery) references.

3. **Product switcher** (in every board/concierge sidebar; FR-38, UC-11). A
   **top-left active-Product control** (a neutral monogram tile + product name +
   chevron) opening a menu that lists the **Tenant's Products** (with the active
   one ticked + an in-flight count) and **"set up a new product"**. Grounded in
   **Fibery / Zeplin / Dovetail / Jira**'s workspace switcher. Switching
   **re-scopes the board + search/filters** to the chosen Product.

4. **Per-product board** (panel 1, refreshed, light; panel 18, dark; FR-01/37).
   The board now shows **only the active Product's** in-flight changes — a
   **scope line** under the title names what's shown (*"Showing Acme Checkout · 5
   in flight"*), the search placeholder is product-scoped, and the switcher sits
   in the header. The dark panel 18 shows a **different** active product
   (Helpdesk) to demonstrate the re-scope. This **supersedes the
   single-implicit-product board** of the original #1.

### Mobbin grounding (second probe — structure only, UXD-15)

| New surface | Mobbin structural reference (`_mobbin-context.md`) | What transferred |
|---|---|---|
| Conversational setup | Vercel / Replit / Render / GitHub import-or-create | the find-or-create branch; repo-list rows + "paste URL"; name + private/public for create-new |
| Concierge front door | Replit Agent thread; Fibery ⌘K palette | conversation + inline action cards; ask-and-point shape |
| Product switcher | Fibery / Zeplin / Dovetail / Jira workspace switcher | top-left active-workspace control + menu + "new" + scoped views |
| Per-product board | (re-uses the existing GitHub-Projects board) | scoped to one product; switcher in header |

No Mobbin palette, type stack, or screenshot was adopted — every colour/font is
the fragment-token system the surface already binds to.

### AA contrast — re-run on the NEW elements (both themes)

*New label / text pairs (must clear 4.5:1):*

| Pairing | Light | Dark | Verdict |
|---|---|---|---|
| product-name (`--text`) on bg-card | 17.04:1 | 17.65:1 | ✓ |
| product avatar monogram (`--text-secondary`) on bg-muted | 7.04:1 | 7.11:1 | ✓ |
| scope-line product name (`--text-secondary`) on card | 7.81:1 | 7.30:1 | ✓ |
| found-change intent (`--text`) on card | 17.04:1 | 17.65:1 | ✓ |
| found-change stage label (`--text-secondary`) on card | 7.81:1 | 7.30:1 | ✓ |
| branch-option body (`--text-secondary`) on card | 7.81:1 | 7.30:1 | ✓ |
| repo-row name (`--text`) on card | 17.04:1 | 17.65:1 | ✓ |
| "connect" / "selected" label (`--accent`) on card | 4.72:1 | 5.63:1 | ✓ |
| read-only honesty chip (`--text-secondary`) on bg-muted | 7.04:1 | 7.11:1 | ✓ |
| proposal value (`--text`) on accent tint | 15.88:1 | 14.21:1 | ✓ |

*New non-text indicators (must clear 3:1, WCAG 1.4.11):*

| Indicator | Light | Dark | Verdict |
|---|---|---|---|
| switcher active-tick (`--accent`) on card | 4.72:1 | 5.63:1 | ✓ |
| found-change stage dot — recon | 4.49:1 | 4.11:1 | ✓ |
| found-change stage dot — specify | 4.47:1 | 6.18:1 | ✓ |
| found-change stage dot — implement | 5.17:1 | 7.25:1 | ✓ |
| spin-up recon dot (`--stage-recon`) on accent tint | 4.49:1 | 4.11:1 | ✓ |
| branch-option selected icon (`--accent`) on tint | 4.42:1 | 5.13:1 | ✓ |

> The found-change **stage dots** are *decorative reinforcement* — the stage is
> also carried by its **worded label** beside the dot, so colour is never the
> sole cue (WCAG 1.4.1). They clear 3:1 out of discipline. The read-only chip
> was lifted from `--text-muted` to **`--text-secondary`** so the honesty label
> is a full-contrast label (7.04:1), not a sub-4.5 muted hint.

**Verdict: PASS — every new label/text pair clears 4.5:1 (lowest 4.72:1, the
accent "connect" label) and every new coloured dot/icon clears 3:1 (lowest
4.11:1), in both light and dark.** The new surfaces introduce **no new colour**;
they re-use the already-verified fragment tokens, so the pass-5/7 verifications
stand unchanged.

### DS-03 systematic visual-identity evaluation (re-run for the new surfaces)

1. **Distinctiveness (dim 1)** — PASS. The new surfaces wear the brand the same
   way as the rest: the **sunset mark** anchors the onboarding hero and the
   concierge greeting and the "set up" success screen; the one sanctioned
   sunset-spinner is the *only* motion (the change spinning up). The product
   switcher's avatar is a **neutral monogram tile**, deliberately *not*
   brand-coloured, so the switcher reads as chrome, not decoration.
2. **Adaptability (dim 3)** — PASS, demonstrated. Every new surface renders in
   both light and dark from one set of markup by swapping the `data-theme`
   scope (panels 13–17 light; 18–19 dark) — no structural change.
3. **Production viability (dim 5)** — PASS. The concierge / setup conversation
   **re-uses the shipped chat composer, bubble, consent-gate, and state
   components** (EP-03 — extend, don't rebuild); the switcher is a standard
   menu/dropdown; the per-product board is the existing board scoped by a
   product id. No new dependency.
6. **Convention-distinction balance (dim 6)** — PASS. Conventions kept where the
   audience expects them: the import-or-create split is the proven SaaS-onboarding
   shape (Vercel/Replit/Render), the workspace switcher is the proven multi-tenant
   shape (Fibery/Jira), the slash-command composer is the proven agent-chat shape
   (Jakob's Law / CL-05). Distinction stays small and on-brand (the mark + the
   single blue/teal accent).

(4 of 6 dimensions documented; DS-03 requires ≥3.)

### CL-06 three-question review (for the new surfaces)

1. **Necessary complexity?** Yes, and minimised. Onboarding *is* multi-step
   (which product → where's the code → confirm), but the design shows **one step
   at a time** (CL-02) and the find-or-create branch is exactly **two** tiles
   (CL-04, ≤5). The concierge's answer is a single card that points; the
   investigation hand-off is one card with one decision. The switcher menu lists
   only the Tenant's products + one "new" action.
2. **Presentation add burden?** No — it lowers it. The conversation removes the
   "fill in this empty form against an empty graph" dead-end; the proposal recap
   means the founder reads *what will happen* before confirming (no surprise
   writes); the read-only chip removes the worry "did asking change anything?";
   the scope line removes the "whose changes am I looking at?" question.
3. **Build a mental model?** Yes. The setup conversation teaches *"a product has
   code behind it"*; the concierge teaches *"asking is safe; doing is a change"*
   (the containment rule made visible); the switcher + scope line teach *"the
   board is one product at a time."*

---

## Seventh pass — the Mobbin probe + two founder refinements (retained)

A real **Mobbin inspiration probe** was run from the main session (web platform)
and recorded in [`_mobbin-context.md`](./_mobbin-context.md) — it supersedes the
earlier `inspiration: none` (the design-subagent runs had reported the MCP
unavailable). **UXD-15 was applied strictly: only structural patterns transfer —
section ordering, density, interaction beats. No Mobbin palette, type stack, or
screenshot is adopted; every colour and font stays bound to the experience-
fragments token system from pass 5.** This pass folds the probe's structural
findings, plus two founder refinements, into the pass-5/6 base.

### Mobbin-grounded structural patterns adopted (visuals stay ours)

1. **Board — stage colour as a dot in the column header (GitHub Projects
   pattern; `_mobbin-context.md` §Board).** Each stage column header now carries
   a **small coloured dot + the stage name + a count** on otherwise-neutral
   columns. The dot is the *only* colour the board introduces — columns and cards
   stay neutral. This is how the stages "just use colours" (the founder's words)
   without painting the board. The dot is **decorative reinforcement**: the stage
   is also carried by the column's **left-to-right position + its name**, so
   colour is never the sole cue (WCAG 1.4.1). Per-stage hues: recon stone ·
   specify indigo · design teal · implement blue · review violet · ship green.

2. **Thread — show the work, checkpoints, paused, and a three-way panel
   (Replit Agent / Lovable / v0 / Gemini; `_mobbin-context.md` §Agent thread).**
   The conversation is no longer chat-bubbles-only. It now:
   - interleaves **inline tool-action log lines** with the chat — *Edited
     src/components/board.tsx*, *Created stage-column.tsx*, *Ran tests — 28
     passed* — quiet mono secondary-text lines, visually distinct from bubbles
     (agentic **AI-01**: the chat coordinates, the work is *shown*);
   - shows **checkpoint / rollback cards** in the stream — *"Checkpoint — the
     stage-column board, tested"* with a **Roll back to here** affordance (the
     founder's checkpoint-as-lineage idea; the read-time status lives here);
   - has a clear **"Paused — waiting for you"** state (new panel 5a, both
     themes) — the agent stops, says why, changes nothing, and **Resume** is one
     click (**AI-03** start/pause/stop);
   - replaces the ad-hoc 2-tab rail with a **right-hand panel that toggles
     Preview · Files · Brain, one tab active at a time** (progressive
     disclosure, **CL-02**).

3. **Sender differentiation stays neutral (OpenAI/Gemini).** The founder's own
   messages remain a **neutral muted bubble**, distinguished by alignment, never
   a brand fill — confirmed by the probe, unchanged from pass 5.

### Refinement A — a proper Files explorer (carried from pass 6, retained)

The right-hand **Files** view is a real worktree browser, grounded in VS Code /
Codespaces / Lovable conventions: a **full folder tree** (expand/collapse to
navigate the whole change); an **"All files" ↔ "Changed files" toggle** with a
count; the changed view marks each file **new / edited / removed** (the M/A/D
git convention reworded for the founder) with a **tree ↔ list** toggle; and the
preview pane renders **documents** (rendered ↔ raw kept), shows **code** read-
only, and shows a **diff** for a changed file where the **+/− gutter glyph**
carries add/remove **without relying on colour** (GitHub convention). Shown in
light (panels 6a/6b) and dark (panel 12).

### Refinement B — state markers simplified to "just colours" + a word

Per the founder's direction, the per-state **SVG shape-glyphs are removed from
the markup**. Every state is now a **clean coloured dot + a dark text label**:

| Status | Now |
|---|---|
| Running | green dot + label "running" |
| Idle | neutral (stone) dot + label "not running" |
| Unknown | neutral (stone) dot + label "unknown" |
| Needs attention | warning-tint pill + amber dot + worded reason ("waiting on you", "stopped mid-reply") |

**Accessibility floor held (the non-negotiable).** A **visible text label
accompanies the colour wherever a state appears** — colour is never alone, which
is what satisfies WCAG 1.4.1 (the shape was never load-bearing for the standard;
the *label* is). In the **compact sidebar**, the bare dot is a *redundant
secondary cue* beside the change name and carries an **accessible name**
(`role="img"` + `aria-label`), never the sole indicator. Idle and unknown share
the same neutral dot deliberately — they are told apart by their **word**, never
by a colour the eye must discriminate. All dots re-verified **≥ 3:1**.

### AA contrast — re-run on the new elements (both themes)

*New non-text indicators (must clear 3:1, WCAG 1.4.11):*

| Indicator | Light | Dark | Verdict |
|---|---|---|---|
| stage dot — recon (stone) on muted | 4.04:1 | 4.00:1 | ✓ |
| stage dot — specify (indigo) on muted | 4.03:1 | 6.01:1 | ✓ |
| stage dot — design (teal) on muted | 4.25:1 | 5.48:1 | ✓ |
| stage dot — implement (blue) on muted | 4.66:1 | 7.05:1 | ✓ |
| stage dot — review (violet) on muted | 4.85:1 | 6.78:1 | ✓ |
| stage dot — ship (green) on muted | 4.52:1 | 10.29:1 | ✓ |
| running dot (positive) on card | 3.30:1 | 10.57:1 | ✓ |
| idle/unknown dot (text-muted) on card | 4.47:1 | 3.89:1 | ✓ |
| tool-log result dot (positive) on card | 3.30:1 | 10.57:1 | ✓ |
| checkpoint teal icon on its accent tint | 4.42:1 | 5.13:1 | ✓ |
| paused amber dot/icon (`--attn-icon`) on warning tint | 4.84:1 | 8.97:1 | ✓ |

> The light **ship** dot uses green-700 `#15803D` (a standard Tailwind step), not
> the raw `--positive #16A34A` which is 2.97:1 at dot size — the one derived
> value, documented. Even so, the stage dots are decorative reinforcement, so the
> 3:1 bar is met out of discipline, not necessity.

*New label / body-text pairs (must clear 4.5:1):*

| Pairing | Light | Dark | Verdict |
|---|---|---|---|
| tool-log line (`--text-secondary`) on card | 7.81:1 | 7.30:1 | ✓ |
| checkpoint title (`--text`) on card | 17.04:1 | 17.65:1 | ✓ |
| paused note body (`--text`) on warning tint | 7.54:1 | 14.35:1 | ✓ |

**Verdict: PASS — every new label/body pair clears 4.5:1 and every new coloured
dot/icon clears 3:1, in both light and dark.** This is in addition to the full
pass-5 re-verification (kept below), which is unchanged: the surface still binds
to the same fragment tokens and the body/chrome/status-pill contrasts are
untouched.

### CL-06 three-question review (re-run for this pass)

1. **Necessary complexity?** Yes. Showing the agent's work, checkpoints and a
   paused state is the irreducible complexity of *driving* an agent (you must be
   able to see what it did, return to a known-good point, and be asked when it
   needs you). The board dot is the *minimum* colour that lets stages be told
   apart at a glance.
2. **Presentation add burden?** No — it lowers it. The tool-log replaces wondering
   "what is it doing?"; the checkpoint replaces fear of losing work; one
   active panel tab (not three open at once) keeps working memory ≈ 4 concepts;
   and removing the state shape-glyphs leaves *fewer* marks to decode (a dot + a
   word).
3. **Build a mental model?** Yes. The stage dot teaches the lifecycle by colour
   *and* position; the tool-log teaches what "the agent is working" actually
   means; the checkpoint teaches that progress is a line you can move along.

---

## Fifth pass — re-grounded to the experience fragments (base, retained below)

The founder gave precise direction and a new, on-point reference: their own
**experience fragments** (`product/experience/fragments/the-morning-calm`,
`the-living-demo`, `the-org-heatmap`). Those fragments carry the **real Sulis
token system** in their `:root` (DESIGN_TOKENS v4.2.0). This pass **binds the
surface to that token system verbatim** — it is the authoritative Sulis design
instance, replacing both the stale cockpit `tokens.css` and the sunset-saturated
palette of the prior passes.

**The token system now bound (lifted from the fragments, never invented):**

| Role | Light | Dark |
|---|---|---|
| Primary (the main action) | `#2563EB` blue | `#60A5FA` |
| Accent ("this is live / now") | `#2D7D90` teal | `#339BAB` |
| Brand depth / gold | `#1E3A5F` / `#C9A962` (logo + tokens only) | `#A3B3CB` / `#DFC480` |
| Positive / Destructive / Warning | `#16A34A` / `#DC2626` / `#F59E0B` | `#4ADE80` / `#F87171` / `#FBBF24` |
| Surfaces | bg `#FAF9F7` · card `#FFFFFF` · muted `#F4F3F0` | bg `#0a0a0a` · card `#141414` · muted `#171717` |
| Text | `#1C1C1C` / `#525252` / `#7A7770` | `#fafafa` / `#a3a3a3` / `#737373` |
| Border | `#E5E2DC` | `#2e2e2e` |
| Status tints | positive/destructive/warning + accent, with matching borders | dark equivalents |
| Fonts | Inter (UI) + JetBrains Mono (ids / code / data) | same |
| Radius | 4px | 4px |

**The four corrections (the core of this pass):**

1. **Gold retired from the UI.** The warm gold (`#F0A830` / `#C9A962`) is no
   longer an accent anywhere on the working surface — not on cards, chrome,
   chips, buttons or status. The **sunset mark stays as the logo** (top-left in
   every panel), and the one place the full sunset gradient still appears in
   motion is the sanctioned reply-spinner. Everywhere an accent is needed the
   surface now leans on the **bluer palette**: **blue** for the primary action
   (Send, Go-ahead), a single **teal** touch for "this is the live/current
   thing" (the current stage column hairline + track marker, the open card edge,
   the active rail-tab underline, the suggestion-chip hover, the streaming
   caret). Brand colours used sparingly.

2. **Neutral user-message bubble.** Researched chat convention (Material 3 chat
   patterns; NN/g conversation-UI guidance; the common-practice in Slack /
   iMessage / ChatGPT): distinguish the sender by **alignment first, colour
   second — and that colour should be a neutral surface, never a brand fill.**
   So the founder's own messages now sit in a **neutral muted bubble**
   (`--bg-muted` + a subtle `--border`), right-aligned; the agent's are plain
   card bubbles, left-aligned. Neither is painted teal/blue/gold. This also
   removes the only remaining "is this brand text legible on a brand fill"
   contrast question from the conversation.

3. **Roomier cards; columns scroll.** The founder found the board cards "very
   condensed" (from cramming all cards into one viewport). Now, per the
   fragments' calm rhythm: card padding **16px**, card gap **12px**, 4px radius,
   and the board **columns scroll vertically** (each `.collist` has its own
   `max-height` + `overflow-y`) instead of compressing everything into one
   screen. The board grid is **responsive** (6 → 3 → 2 columns). Room to breathe.

4. **Status indicators re-verified on the fragments' RAG scales.** The
   dot/icon + dark-neutral-label pattern is kept (colour lives only on the
   glyph; the label is dark neutral text; each state has a distinct shape). It
   now sits on the fragments' functional **tint bg + matching border** scales
   (`--bg-positive`/`--bg-warning`/`--bg-destructive` + their borders), exactly
   as `the-org-heatmap` uses them.

**Binding caveat (one derived value).** The fragments' light `--warning #F59E0B`
is a *large-area / decorative* token (it fills the summary bar). As a small
status glyph it does **not** clear the 3:1 non-text bar (≈2.1:1 on white/tint).
So the small "needs attention" icon uses a derived **`--attn-icon` = `#B45309`**
(amber-700, a standard Tailwind step — convention-compliant), which clears
4.84:1 on the warning tint. In dark, `--warning #FBBF24` clears 3:1 and is used
directly. This is the only value not lifted verbatim, and it is documented here.

### This pass — the restraint correction (third pass) — SUPERSEDED by the fifth pass above

The second pass re-grounded the surface on the Sunset identity but applied it too
heavily: the founder's feedback was that it **"uses too much of the brand
colours"** and they wanted it **"more linear in feel"** — the restrained calm of
their own vision-site (`methodology/executions/vision-site-20260305-v6`).

This pass re-applies the same Sunset identity at **vision-site restraint**
(ADR-095 discipline): **neutral-dominant**, brand worn lightly.

**What moved (brand-saturated → vision-site-restrained):**

| | Before (pass 2) | Now (pass 3) |
|---|---|---|
| Backdrop | warm-paper / deep night-blue (brand-tinted) | warm paper `#FAF9F7` / near-black `#161616` — the vision-site neutrals |
| Stage columns | each stage a different sunset stop (6 colours) | **all neutral**; stages read by label + icon + position; only the **current** column takes a single accent hairline |
| Cards | sunset-coloured / brand borders | neutral `#E5E2DC` borders; only the one **currently-open** card takes the accent edge |
| Filter chips | active chip = terracotta fill | neutral inverse; no brand fill |
| Suggestion chips | plum-filled | neutral outline; accent shows on hover only |
| Status block | accent-bordered left rule | neutral muted card |
| Conversation | — | neutral agent bubbles; only the **user's own** bubble carries the accent |
| Doc chrome | sunset gradient bar in the header | removed; quiet mark + neutral type |
| Type weight | 300–600 | **300–500** (lighter, vision-site range) |

**Where the sunset now appears (one or two touches per screen):**
- the **real sunset mark** top-left in every panel — the identity anchor;
- the **one primary action** (Send / Go-ahead) — the single filled accent button;
- the **current stage** — the stage-track "now" marker and the active board
  column's thin top hairline;
- the **focus ring** (keyboard);
- the **user's own chat bubble** (their voice);
- the suggestion-chip **hover** and the active rail-tab **underline**;
- the sanctioned **sunset-spinner** (motion only).

Everything else is warm-grey / stone / near-black. No hue carries meaning except
as reinforcement.

**The single accent** is the warm middle of the sunset: terracotta darkened to
`#C24A2E` on light (so white label text clears AA), warm gold `#F0A830` on dark.
The five sunset stops remain the brand source of truth (the mark uses them
verbatim) — nothing here is invented.

**Follow-up (still open, updated this pass):** the app's `tokens.css` must be
**regenerated from THIS fragment token set** — the blue (`#2563EB`) / teal
(`#2D7D90`) / neutral system in the experience fragments' `:root` (DESIGN_TOKENS
v4.2.0), *not* the stale cockpit slice and *not* the sunset-saturated set the
prior passes drew from. This mockup is the authoritative colour source until that
regeneration lands. (The build target is Alpine.js + Tailwind; the token set maps
cleanly to Tailwind theme variables.)

---

## Status-label readability fix (re-opens sign-off) — fourth pass

**The feedback.** The founder found the red/amber/green status *labels* hard to
read. Root cause: the labels were **coloured text** — the liveness word
("running") was painted in the status colour, and the "needs attention" and
confidence tags were **coloured text sitting on a coloured fill** (amber text on
an amber tint). Amber especially fails here: amber/gold text never reaches the
4.5:1 a small label needs, and the saturated-fill-behind-coloured-text pattern
makes colour the thing you must read *through*.

**The fix (one consistent pattern everywhere).** Colour now lives **only on a
dot/icon**; the **label is the app's normal dark neutral text** on the surface.

| Status | Before | Now |
|---|---|---|
| Running | green dot + green word "running" | green filled disc + **dark label** "running" |
| Idle | grey dot + grey word "not running" | hollow ring + **dark label** "not running" |
| Unknown | grey dash + grey word "unknown" | dash glyph + **dark label** "unknown" |
| Needs attention | amber text on an amber fill | light-tint pill + thin border + **amber warning icon** + **dark label** (e.g. "waiting on you", "stopped mid-reply") |
| Health / confidence read-out | green/amber text on a tint | light-tint pill + thin border + **coloured tick/dot icon** + **dark label** ("Clear signal") |

Each status still has its **own distinct shape** (filled disc = running, hollow
ring = idle, dash = unknown, warning triangle/clock/✕ = the attention reasons,
tick = clear signal), so it reads without relying on colour at all.

**Convention basis** (GOV.UK / Scottish Government design systems + RAG-
accessibility guidance): (1) colour never alone — every status = colour + a
distinct shape/icon + a text label (WCAG 1.4.1); (2) label text is dark on a
neutral or light-tint surface at ≥4.5:1 — never coloured text, never text on a
saturated fill; (3) amber is kept to the icon/dot only (a darkened amber that
clears 3:1), never used as a label background; (4) the same colour + same icon
mean the same status everywhere (CL-05 consistency). Applied identically in
**light and dark**.

**Re-verified contrast — the new pattern, both themes.**

*Label text (dark neutral, must clear 4.5:1):*

| Pairing | Light | Dark |
|---|---|---|
| liveness label on card surface | 11.40:1 | 9.57:1 |
| liveness label on muted column | 10.19:1 | 8.70:1 |
| needs-attention label on its tint | 10.04:1 | 8.93:1 |
| confidence "clear signal" label on tint | 10.18:1 | 8.98:1 |

*Coloured dot / icon (non-text graphic, must clear 3:1):*

| Indicator | Light | Dark |
|---|---|---|
| running disc | 5.32:1 (card) / 4.75:1 (muted) | 9.44:1 / 8.58:1 |
| idle / unknown glyph | 5.32:1 / 4.75:1 | 5.65:1 / 5.14:1 |
| needs-attention amber icon | 5.21:1 | 7.80:1 |
| confidence tick (clear) | 4.75:1 | 8.85:1 |
| confidence dot (medium) | 5.21:1 | 7.80:1 |

**Verdict: PASS — every status label clears 4.5:1 (lowest 8.70:1) and every
coloured dot/icon clears 3:1 (lowest 4.75:1), in both light and dark.** The fix
was applied to every place a status appears: the **session liveness** dot
(running / not running / unknown) in the sidebar and on every board card, the
**needs-attention** flag (waiting on you / stopped mid-reply), and the
**change-health** read-out (the "what's happening" confidence badge).

---

## What the mockup shows (nineteen panels — light then dark)

**Light (panels 1–7, 13–17):** the **per-product board** (panel 1, now with the
product switcher shown open + a scope line); board-loading (skeleton);
board-empty; the thread + live chat (stage track, plain-English status, streaming
conversation, pause/stop run-controls, the docked composer with chips + free
text + slash commands, the brain/files rail showing one section at a time); the
consent gate; the paused state; files rendered + raw; the file explorer (tree +
diff); the server-down error. **New (this pass):** conversational setup step 1
*which product?* (13); step 2 *where's the code? — find-or-create* (14);
create-new + proposal + confirm gate (15); *you're set up* end state (16); the
**concierge front door** — read-only find/status answer + investigation→change
spin-up (17).

**Dark (panels 8–12, 18–19):** the board, the thread + live chat, the consent
gate, files-raw + the error, the file explorer — same markup, re-skinned from
the dark token set (deep near-black surfaces, warm-paper text, the reversed
mark). **New (this pass):** the **per-product board + open switcher**, scoped to
a *different* product (Helpdesk) to show the re-scope (18); the **concierge front
door** — needs-attention answer + start-a-change spin-up (19). Proves the new
surfaces work in both modes from one set of markup.

---

## How each required standard is met (live in the mockup)

### Accessibility — WCAG 2.1 AA (DS-02) — RE-VERIFIED on the FRAGMENT (blue/teal/neutral) palette

Every pair was **re-computed from scratch** for the fragment token system this
pass binds to (sRGB relative-luminance, WCAG 2.1 formula). **Verdict: PASS — all
body/label text pairs ≥ 4.5:1, all meaningful non-text indicators ≥ 3:1, in both
themes.** Two of the fragments' own tokens needed care and are handled in the
design (not worked around silently):

- **`--text-muted #7A7770` is 4.47:1 on white** — fractionally under the 4.5:1
  small-text bar. It is therefore used only for **labels/secondary text** that
  ride at large-text size or on the muted surface where it is decorative; every
  **small body label that must clear AA uses `--text-secondary #525252`**
  (7.81:1). The fragments use `--text-muted` the same way.
- **Status colours fail as TEXT on their tints** (warning `#F59E0B` is 2.07:1,
  positive 3.15:1) — which is exactly why the status pattern keeps **colour on
  the icon/dot only and the label as dark neutral text**. The small warning glyph
  uses the derived `--attn-icon #B45309` (4.84:1 on tint) so even the *icon*
  clears 3:1.

- **Visible keyboard focus** — one token-coloured `:focus-visible` ring (2px,
  2px offset) on every interactive element; terracotta `#C24A2E` on light
  (4.87:1 on white) and gold `#F0A830` on dark (8.22:1 on surface) — both well
  above the 3:1 non-text bar.
- **Colour-independent status (1.4.1)** — liveness, stage, needs-attention and
  AI confidence each carry an **icon glyph + a text label**; colour lives **only
  on the dot/icon**, and the **label is dark neutral text** (never coloured text,
  never text on a saturated fill — see "Status-label readability fix" above).
  Running = filled disc + "running"; idle = hollow ring + "not
  running"; unknown = dash + "unknown". Stage = a line icon + the stage name +
  board position. Needs-attention = ⚠ + a worded reason. Stage-track "done" = a
  check glyph. **No signal relies on hue** — and now that the stages are neutral,
  this is even more strictly true than before.

- **AA contrast — LIGHT theme text pairs (fragment tokens):**

  | Pairing | Ratio | Verdict |
  |---|---|---|
  | text `#1C1C1C` on bg `#FAF9F7` | 16.20:1 | AAA |
  | text `#1C1C1C` on card `#FFFFFF` | 17.04:1 | AAA |
  | text-secondary `#525252` on `#FFFFFF` | 7.81:1 | AAA |
  | text-secondary `#525252` on bg `#FAF9F7` | 7.43:1 | AAA |
  | text on neutral user bubble `#F4F3F0` | 15.36:1 | AAA |
  | primary-fg `#FFFFFF` on primary `#2563EB` (Send / Go-ahead) | 5.17:1 | AA |
  | accent-fg `#FFFFFF` on accent `#2D7D90` | 4.72:1 | AA |
  | primary `#2563EB` on card (link/focus reference) | 5.17:1 | AA |
  | accent `#2D7D90` (current-step label) on card `#FFFFFF` | 4.72:1 | AA |
  | status label (text-secondary) on warning tint `#FFFBEB` | 7.54:1 | AAA |
  | status label (text-secondary) on positive tint `#F0FDF4` | 7.46:1 | AAA |
  | status label (text-secondary) on destructive tint `#FEF2F2` | 7.14:1 | AAA |

- **AA contrast — DARK theme text pairs (fragment tokens):**

  | Pairing | Ratio | Verdict |
  |---|---|---|
  | text `#fafafa` on bg `#0a0a0a` | 18.97:1 | AAA |
  | text `#fafafa` on card `#141414` | 17.65:1 | AAA |
  | text-secondary `#a3a3a3` on card `#141414` | 7.30:1 | AAA |
  | text on neutral user bubble `#171717` | 17.18:1 | AAA |
  | primary-fg `#0a0a0a` on primary `#60A5FA` (Send / Go-ahead) | 7.79:1 | AAA |
  | accent-fg `#0a0a0a` on accent `#339BAB` | 6.05:1 | AA |
  | accent `#339BAB` (current-step label) on card `#141414` | 5.63:1 | AA |
  | status label (text `#fafafa`) on warning tint `#451a03` | 14.35:1 | AAA |
  | status label on positive tint `#052e16` | 14.28:1 | AAA |
  | status label on destructive tint `#450a0a` | 15.47:1 | AAA |

- **AA contrast — non-text indicators (≥3:1, WCAG 1.4.11):**

  | Indicator | Light | Dark | Verdict |
  |---|---|---|---|
  | focus ring (primary blue) on card | 5.17:1 | 7.25:1 | ✓ |
  | current-stage teal hairline on muted | 4.25:1 | — | ✓ |
  | running disc (positive) on card | 3.30:1 | 10.57:1 | ✓ |
  | needs-attention icon (`--attn-icon`) on warning tint | 4.84:1 | 8.97:1 | ✓ |
  | destructive icon on card | 4.83:1 | 6.66:1 | ✓ |
  | idle/unknown glyph (text-muted) on card | 4.47:1 | 3.89:1 | ✓ |

  Note: the stage-track "done" dots are *decorative reinforcement* — stage state
  is carried by the label text + check glyph + position, not the dot. The small
  needs-attention amber glyph uses the derived `--attn-icon #B45309` precisely so
  it clears 3:1 (the raw fragment `--warning` would not at glyph size).

- **Keyboard model** — `Enter` sends, `Shift+Enter` newline (in the composer
  hint); the rendered/raw toggle and rail tabs are real `<button>`s;
  reduced-motion honoured (streaming caret, skeleton shimmer and sunset-spinner
  all collapse to static).

### Agentic interface (agentic-interface)
- **AI-01 outcome-oriented** — chat coordinates, but the *work* lives in
  purpose-built UI: the board, the stage track, the brain rail, the file viewer.
- **AI-02 dual-mode input** — the composer has **contextual suggestion chips**
  ("Sign off on the design", "What's left before build?"), **always-available
  free text**, and a **slash-command** affordance (`/sign-off`, `/files`,
  `/status`).
- **AI-03 human-in-the-loop** — the running agent shows **Pause** and **Stop**;
  a **consent gate** sits before any consequential downstream action with
  explicit "Go ahead / Not yet", naming the consequence and the files touched.
- **AI-07 transparency** — the status read-out is labelled as read from the
  change's notes "just now" with an **honest-confidence** badge ("Clear signal");
  AI turns are attributed ("Agent"); the resume note is honest that the change
  was *resumed*, not silently continued (FR-26).

### Cognitive load (cognitive-load)
- **CL-04 ≤5 primary options** — board toolbar exposes 3 filter controls +
  search; the consent gate offers exactly 2 actions; the run-bar 2.
- **CL-02 progressive disclosure** — the thread never shows progress +
  conversation + brain + files + chat all at once; the spine (progress + status
  + chat) is persistent and **brain and files share one rail showing ONE section
  at a time** — working-memory load stays ≈ 4 concepts.
- **CL-01 extraneous-load elimination** — and the restraint pass *reduces* it
  further: removing the six per-stage colours and the brand fills means there is
  less to decode, not more. Every glyph still carries meaning; borders (not
  shadows) carry structure; the surface is calmer.
- **CL-05 consistency** — one liveness vocabulary, one status pattern across
  board + sidebar + thread; conventions the audience knows (Kanban columns, chat
  composer, rendered/raw toggle).

---

## The AI-03 reconciliation — surfaced for a founder call

**The tension:** the "it just works" chat (resume/spawn without the user
choosing, FR-24/25) vs AI-03's human-in-the-loop requirement.

**How the design resolves it (reflected in the mockup):**
- **Message delivery stays seamless.** Your typed **send is the consent** to
  deliver that message. The app silently resumes the last session or spawns a
  fresh one — you never pick. (Panel 4: no resume/spawn prompt; a quiet
  "this change was resumed" note *after*, for honesty, not a decision.)
- **Consequential downstream actions are gated.** When the agent wants to
  **write, ship, or start a process**, it asks first with a visible
  go-ahead/decline that names the consequence (Panel 5).

This split satisfies both FR-24/25 and AI-03. **It is a genuine founder-owned
call** — see the gaps list in the hand-back.

---

## DS-03 systematic visual-identity evaluation (≥3 dimensions) — re-run for the restrained direction

1. **Distinctiveness (dim 1)** — PASS, and now correctly calibrated. The surface
   still reads unmistakably as *this* Sulis — the real River-Avon sunset mark
   anchors every panel, and the one warm accent is the same terracotta/gold the
   founder knows from the logo. But the distinctiveness now comes from the
   **restraint plus the mark**, the way the vision-site's identity comes from its
   calm neutrals plus a single sparing accent — not from saturating the chrome.
   This is the correction the founder asked for: the brand is *worn*, not
   *splashed*.
2. **Adaptability (dim 3)** — PASS, demonstrated. The same markup renders both
   light and dark purely by swapping the semantic token set on a `data-theme`
   scope — no structural change. The three-tier architecture (sunset primitives →
   neutral-dominant semantic tokens with one accent → component use) means a
   future tokens.css regeneration drops straight in. With the palette now neutral,
   re-theming for any future brand tweak touches a single accent token, not six
   stage colours.
3. **Production viability (dim 5)** — PASS. Maps 1:1 to the existing cockpit stack
   (shadcn/ui + Tailwind, Lucide-style stroke icons, the shipped `ChangeCard`,
   `StageBadge`, `LivenessDot`, Monaco viewer, contract renderer). Per ADR-005
   this is extend-and-recompose, not a rebuild. The neutral palette is *closer* to
   shadcn defaults than the saturated one, so less custom theming. The one new
   dependency is the tokens.css regeneration (logged follow-up).
4. **Convention-distinction balance (dim 6)** — PASS. Conventions kept where the
   audience expects them (Kanban columns, chat composer, rendered/raw toggle,
   dark-mode — Jakob's Law / CL-05); distinction kept deliberately small and
   on-brand (the mark, the single blue/teal accent, the sanctioned sunset-spinner
   as the only spectacle). The fifth pass keeps the discipline but moves the
   accent to the **bluer palette** per the fragments: ≤ a couple of accent
   touches per screen, none of them gold.

(4 of 6 dimensions documented; DS-03 requires ≥3.)

> **Note (fifth pass):** the distinctiveness rationale above was written for the
> third pass's *warm* single accent. It still holds with the accent moved to
> blue/teal — distinctiveness now comes from the **sunset mark + calm fragment
> rhythm**, not from any UI colour. Gold is logo-only.

---

## CL-06 three-question design review (re-run for the restrained direction)

1. **Is this complexity necessary? (intrinsic)** — Yes, bounded. A change is
   inherently multi-faceted (progress, conversation, created items, files, the
   ability to act). The design accepts the irreducible complexity and stages the
   rest. The restraint pass removes *visual* complexity (six stage colours, brand
   fills) without removing any function.
2. **Does our presentation add unnecessary burden? (extraneous)** — No, and this
   pass measurably **lowers** it. Stripping the per-stage colours and the
   brand-saturated chrome means fewer hues to interpret; the single accent now
   reliably means "this is the live thing / the action" wherever it appears,
   which is *easier* to learn than six colour-coded stages. Borders carry
   structure; one status vocabulary reads everywhere.
3. **Does this help users build a mental model? (germane)** — Yes. The board's
   left-to-right columns still teach the lifecycle, and the stage track repeats
   that order inside the thread — now taught by **position + label + the single
   "now" marker** rather than a colour gradient, which is a cleaner, more honest
   model. The fifth pass sharpens the single learnable rule into two: **teal =
   "this is the live / current thing"** (current stage, open card, streaming
   caret) and **blue = "this is the action you take"** (Send, Go-ahead). Your own
   messages are now a **neutral** bubble (alignment, not colour, marks them as
   yours), so colour is reserved entirely for live-state and action — easier to
   learn than overloading one colour onto five meanings.

---

## Provenance

`provenance: draft` (RE-OPENED, DS-07). The contract is re-opened for the
**eighth pass**: the four **new user-facing surfaces** of scope #7 (the chat
concierge + conversational onboarding) and #8 (the product switcher +
per-product board) were designed and added, grounded in a second Mobbin probe
(structure-only, UXD-15) and bound to the same fragment-token design instance
(no new colour). Provenance is `draft` and `signed_off_at` is **null**. It does
**not** advance to `production-approved` until the founder signs off — the #45
gate. The sign-off is facilitated separately, never set here.

### Founder-owned gaps surfaced by this pass (do not block the design; safe defaults shown in the mockup)

These are genuinely founder-owned product calls — the mockup shows a safe
default for each, but the founder may want to decide:
- **Where a created repo lives** — local-only vs a hosted remote (GitHub etc.).
  The create-new step shows **Private / Public / Local only** with *Private* as
  the default selection; which is right is the founder's call (already named as
  an open question in the SRD's verification plan).
- **One product or several discovered at once** — onboarding here mints **one**
  product; whether discovery may propose several at once is founder-owned (also
  named in the SRD).
- **The product avatar** — shown as a neutral two-letter monogram. If the
  founder wants product logos/colours instead, that's an identity call for them.
