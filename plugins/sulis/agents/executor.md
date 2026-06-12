| 1 | Worktree + branch | `wpx-worktree create` cuts a branch `wp/{primitive-slug}/wp-NNN-<slug>` off the base branch (the change branch, or `origin/main`); dev SHA recorded in sidecar; `wpx-journal init` runs; pre-flight tooling checks recorded |
`wpx-journal complete-step --step 7 --outcome "Pushed to wp/{primitive-slug}/wp-NNN
/code-review wp/{primitive-slug}/wp-NNN-<slug> <project-name>
    --suggested-next "Re-invoke /code-review wp/{primitive-slug}/wp-NNN-<slug> <project>; then resume Step 6.5"
| Step 1: resolve the canonical branch name (MUST — do NOT hand-template) | `wpx-wp branch-name --wp WP-NNN --project <slug> --repo-root <target-change-worktree>` → `.data.branch`. Inside a change this yields the canonical `wp/{primitive-slug}/wp-NNN-<slug>`; outside one, the legacy `feat/wp-NNN-<slug>`. Use this resolved value for `--branch` everywhere below — never hand-spell `feat/wp-NNN-*` (#336/#105/#106): the train's `queue-list` looks the WP up by the canonical name, and `branch-ci` now triggers on `wp/**` (#334), so a hand-templated `feat/` branch is both unfindable by the train AND a name the migration is retiring (#284). |
  --branch wp/feat-add-cancel/wp-007-cancel-flow \
--step 7 --outcome "Pushed to wp/{primitive-slug}/wp-NNN at SHA <sha>"`), you exit
- **Branch on remote** — `wp/{primitive-slug}/wp-NNN-<slug>` pushed; CI triggered.
  *"WP-NNN Step 7 complete — pushed to wp/{primitive-slug}/wp-NNN-<slug> at SHA