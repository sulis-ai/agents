# Visual contract — Sulis change workspace (Files view · Direction B · repo browser)

```yaml
kind: contract
contract_type: visual
surface: change-workspace-files
mockup: files-B-repo-browser.html
binds_to: ../chat-redesign/chat-B2-tabbed-workspace.html   # the signed app shell
supersedes: ../sulis-app.html                              # file-explorer panels 6 / 6a / 6b
inspiration: >-
  the signed Mobbin probe (../_mobbin-context.md) — VS Code / GitHub Codespaces
  explorer tree + README-rendered preview, Lovable / v0 read-only-code + preview
  toggle, GitHub-Projects worded status. Structure / interaction only, no palette
  or screenshot (UXD-15).
signed_off_at: 2026-06-05   # founder signed off (repo-browser; md-rendered-default + couldn't-load state)
provenance: production-approved
```

The founder picked **Direction B — the repo browser** from the Files & Folders
brainstorm. This is that one direction built as a real-token mockup, rendered
inside the signed tabbed-workspace shell (`chat-B2-tabbed-workspace.html`) with
**Files** selected in the change's left nav, so it reads in context. Every
colour, font, radius, and status treatment is lifted verbatim from the signed
design instance (`tokens.css` / `sulis-app.html` / `chat-B2`); this contract
changes layout + interaction + adds the new **folder-overview list** only.

## The two-level interaction (the signature of Direction B)

A single full-width Files view with a ~280px **tree column** + a **content
column** that renders at one of two levels:

1. **Folder / overview level** (the default landing state). With a folder — or
   nothing — selected, the content column shows that folder's contents as a
   clean **list** (type icon · name · status badge for changed files), and if
   the folder has a README it renders **below** the list using the same
   rendered-markdown treatment. The breadcrumb shows the folder path.
2. **Single-file level.** Selecting a file turns the content column into the
   file: breadcrumb path · **Copy path** · a **rendered ↔ raw** toggle (for
   docs) · a **Current ↔ Diff** toggle (for changed files) · the content —
   syntax-highlighted code in the mono face, or rendered markdown. **Docs open
   rendered by default** (see decision 7).

## Locked decisions

1. **Files is full-width, a repo browser** — not a right-rail panel. Tree on the
   left (~280px), content fills the rest. Replaces the old `sulis-app` rail-tab
   Files panel; carries forward its tree + rendered/raw/diff intent (panels
   6/6a/6b).
2. **Tree column.** A small "Files in this change" header → an **All files ↔
   Changed · N** segmented switch → a **search/filter** box → the tree
   (folders-first, expand/collapse chevrons, file-type icons). Changed files
   carry a small status dot in the tree; the full worded badge appears in the
   overview list and the file-level breadcrumb.
3. **Folder overview + README below** (new). The list-of-contents + the folder's
   README rendered underneath is the one piece of layout this direction adds on
   top of the signed instance. It reuses the existing rendered-markdown look
   (`.rendered`), so it introduces interaction, not palette/type.
4. **Worded status, never colour-alone (WCAG 1.4.1).** Changed files read
   `● new` / `● edited` / `● removed` — a tinted single-letter chip (N / E / R)
   **plus the spelled word**. The word in `--text-muted` carries the meaning; the
   colour is redundant reinforcement.
5. **Every required state is rendered** so sign-off covers them — including the
   couldn't-load / read-error state (see below).
6. **Heroicons throughout** (MIT, Tailwind Labs), real SVGs, `currentColor`: 24
   outline for the left-nav views; 20 mini-solid for tree/list/toolbar/inline.
7. **Docs default to RENDERED; code defaults to source** (founder change, this
   round). A rendered-capable doc (markdown / html) opens in its **rendered**
   state — read the way it's meant to look — with the **Rendered ↔ Raw** switch
   set to "Rendered" so the founder can flip *back* to the exact source. Code
   files keep opening as their syntax-highlighted source. This rendered-default
   rule is docs-only; it reuses the existing `.rendered` treatment + the existing
   `seg-toggle`, so it adds a default, not new palette/type.
8. **Honest failure — the couldn't-load state** (founder change, this round).
   When Sulis tried to read a file and something went wrong (it vanished, a read
   error, the change's workspace was unreachable), the content column shows a
   calm worded message: "Couldn't load this file" + a "Couldn't read the file"
   word-chip (the amber attention glyph is redundant reinforcement, never the
   sole cue — WCAG 1.4.1) + a plain-English why + a **Try again** action and
   **Copy path**. Distinct from "can't preview" (image/binary) and "too big" —
   those are *we won't render this*; this is *we couldn't read it*. Mirrors the
   chat's honest-failure treatment: surface the problem without alarm (no
   destructive-red banner).

## Tokens consumed (all `var(--*)`, no invented hex)

- **Surfaces** — `--background` (canvas), `--card` (tree column, content cards,
  list, rendered panel), `--muted` / `--bg-muted` (search field, segmented-track,
  diff/hunk meta), `--border` / `--border-muted` (column + card hairlines).
- **Text** — `--foreground` (body, code, paths), `--text-secondary` (README body,
  breadcrumb segments), `--text-muted` (counts, kickers, the worded status word).
- **Accent (teal `--accent` #2D7D90)** — folder icons, the selected tree node
  (`--bg-accent` fill + `--bg-accent-border`), toggle-on icon, the stage badge.
- **Status** — `--bg-positive`/`--bg-warning`/`--bg-destructive` tints + their
  `*-border` for the N/E/R chips; `--positive`/`--destructive` for the diff
  add/remove lines and the tree dots; `--attn-icon` for the edited glyph.
- **Type** — `--font-sans` (Inter) for prose/labels, `--font-mono` (JetBrains
  Mono) for filenames, paths, breadcrumbs, code, and the diff.
- **Three AA-internal text shades** — `--new-mk` (#15803D, == existing
  `--stage-ship`) and `--rm-mk` (#B91C1C) darken **only the single-letter badge
  glyph** so the letter clears WCAG AA on its tint; `--accent-ink` (#246676)
  darkens **only the "Try again" label text** on the accent tint so it clears AA
  *as text* (5.9:1 vs the base accent's 4.3:1). All three are the same hue family
  as their base token; no new surface colour is introduced. (See a11y note.)

## Heroicons used (verify in post-build review)

- left-nav **folder** (24 outline) for the Files view switch; chat-bubble /
  cube-transparent / eye carried verbatim from `chat-B2`.
- **folder** + **folder-open** (mini) — tree nodes + breadcrumb + overview rows.
- **chevron-right / chevron-down** (mini) — expand/collapse + breadcrumb
  separators.
- **document** (mini + 24 outline) — markdown / text files + the file-too-big
  state icon.
- **code-bracket-square** (mini) — code files + the Current toggle.
- **photo** (mini + 24 outline) — image files + the can't-preview state icon.
- **magnifying-glass** (mini) — the filter box.
- **clipboard** (mini) — Copy path.
- **arrows-right-left** (mini) — the Diff toggle.
- **eye** (mini) — the Rendered toggle (read-the-way-it's-meant-to-look).
- **code-bracket** (mini) — the Raw toggle (the exact source).
- **document-magnifying-glass** (24 outline) — the couldn't-load state icon
  (we went looking and couldn't read it).
- **exclamation-triangle** (mini) — the "Couldn't read the file" word-chip glyph.
- **arrow-path** (mini) — the Try again action.

## States rendered (panels in the mockup)

1. **Folder overview + rendered README** — the default landing state.
2. **Single file open (code)** — with the **Current ↔ Diff** toggle visible,
   syntax-highlighted in the mono face; breadcrumb + Copy path. Code defaults to
   source.
3. **A doc open, RENDERED by default** — a markdown file (`README.md`) opens in
   its rendered state (read-the-way-it's-meant-to-look), with the **Rendered ↔
   Raw** switch set to "Rendered" so the founder can flip *back* to the source.
   Reuses the `.rendered` treatment + the `seg-toggle`. (Founder change.)
4. **Can't preview this (image / binary)** — matches the live `FileBinaryState`:
   the friendly line + the path + **Copy path**, never a blank pane. Copy mirrors
   the component's intent ("copy the path to open it locally").
5. **File too big to preview** — matches the live `FileTruncatedState`: same
   pattern, size shown.
6. **Loading** — a calm skeleton in the tree + content (the shimmer from
   `sulis-app`), plus a spinner "Loading this file…", never a blank flash.
7. **Couldn't load / read error** — distinct from states 4 & 5: we *tried* to
   read the file and something went wrong (vanished, read error, workspace
   unreachable). The same calm `.state` pattern: "Couldn't load this file" + a
   worded "Couldn't read the file" chip + a plain-English why + **Try again** +
   **Copy path**. `role="alert"`. Honest failure, no alarm. (Founder change.)

## Structural patterns borrowed from the Mobbin references (UXD-15)

> Visuals stay ours; only these structural beats transfer. Logged so the
> post-build review can verify them against the running surface.

- **Explorer tree + rendered preview** — VS Code / GitHub Codespaces
  (`510732c4`, `81856131`): canonical folders/files tree on the left, README
  rendered on the right. We adopt the *structure* (folders-first tree → preview),
  not their chrome.
- **Changed-files source-control view** — the GitHub/VS Code "Changed" scope
  with per-file status markers; we render it as the **Changed · N** switch +
  worded N/E/R badges (GitHub-Projects-style worded status from the board probe).
- **Read-only code + preview/diff toggle** — Lovable / v0 (`150f7186`,
  `0e51be15`): read-only code with a rendered/preview toggle and version diff.
  We adopt the **rendered ↔ raw** and **current ↔ diff** toggle beat.

## Accessibility (design-time, WCAG 2.1 AA)

- **Contrast verified** on every token pair the surface uses (programmatic
  check): body 17.2:1, secondary text 7.8:1, muted labels 4.7:1, accent icon on
  white 4.7:1 (≥3:1 non-text), accent badge label 4.7:1, mono code/paths 17.9:1.
- **Status badge glyphs** — the N/E/R letters initially read 3.2:1 (NEW) and
  4.4:1 (REMOVED) against their tints; darkened to `--new-mk` (4.8:1) and
  `--rm-mk` (5.9:1) so the glyph clears AA *as text*. The meaning never depends
  on the glyph or its colour: the spelled word ("new"/"edited"/"removed") is
  present and passes (1.4.1 colour-independence).
- **"Try again" label (couldn't-load state)** — the base `--accent` on the
  `--bg-accent` tint reads 4.28:1, just under AA for text; the label text is
  darkened to `--accent-ink` (#246676 → 5.9:1) so it clears AA *as text*, while
  the icon (3:1 non-text) and the fill/border stay on the accent. The action's
  meaning is the word "Try again", never the colour.
- **Rendered/Raw toggle (state 3)** — the active "Rendered" segment uses the
  same `seg-toggle` treatment as the Current/Diff toggle; on-state is carried by
  the raised card fill + the accent icon (4.7:1, ≥3:1 non-text), and the word
  label, not colour alone.
- **Couldn't-load colour-independence** — the read-error meaning is carried by
  the heading text + the worded "Couldn't read the file" chip; the amber
  attention glyph (`--attn-icon`, 4.6:1 on its tint) is redundant reinforcement,
  never the sole cue (1.4.1). The panel is `role="alert"` so assistive tech
  announces it.
- **Keyboard** — every tree node / list row / toggle / action is focusable;
  `:focus-visible` is a 2px `--ring` outline with offset (from the shell).
  Tree uses `role="tree"`/`treeitem` with `aria-expanded`/`aria-selected`;
  toggles use `role="group"` + `aria-pressed`; the scope switch uses
  `role="tablist"`.
- **Live regions** — the loading and the binary/too-big panels are
  `role="status"`; the loading note is `aria-live="polite"`.

## Cognitive load (UXD-16 / CL-01..06)

- **≤5 primary options** at any point: the tree column has three controls
  (scope switch, filter, tree); the file toolbar has at most two toggles + Copy
  path. CL-04 holds.
- **Progressive disclosure** (CL-02): folders collapse; the README sits below
  the list rather than competing; diff is a toggle off the file, not always-on.
- **Every element earns its place** (CL-01): no decorative chrome; the status dot
  in the tree is the only redundant-with-the-badge cue and it aids fast scanning.
- **Consistency** (CL-05 / Jakob's Law): the tree, breadcrumbs, rendered/raw and
  diff toggles all follow the IDE/code-host conventions the audience knows; the
  status badge + rendered-markdown treatments are reused verbatim from the signed
  instance.

## L-13 — fonts actually load

Rendered in a real browser (Playwright, networkidle + `document.fonts.ready`):
**Inter 400/500/600/700, JetBrains Mono 400/500, Satoshi 700 all reported
`loaded`** (re-verified after this round's changes). Sign-off is on the rendered
surface, not a token diff. All seven states screenshotted; the markdown-rendered
state and the couldn't-load state checked visually + every new token pair
re-run through the contrast check (all AA-pass).

## Build note (after sign-off)

Build against this mockup: the full-width Files view = tree column
(scope switch + filter + tree) + content column with the two-level render
(folder overview/list + README, and single-file rendered/raw/diff). Reuse the
existing `FileBinaryState` / `FileTruncatedState` / rendered-markdown / diff
components behind the new layout; the new piece is the **folder-overview list**
and the breadcrumb-driven level switch. Post-build visual check looks at the
running surface vs this file (L-13), not just a token diff.
