// WP-009 — unit tests for mangleCwd.
//
// Per WP Contract "Mangling rule" + ADR-004 §Context. Claude Code
// replaces EVERY non-alphanumeric character with `-` (not just `/`)
// when naming `~/.claude/projects/<mangled-cwd>/`.

import { describe, it, expect } from "vitest";

import { mangleCwd } from "../lib/mangleCwd";

describe("mangleCwd", () => {
  it("mangles a typical macOS worktree path", () => {
    expect(mangleCwd("/Users/iain/Documents/repos/foo")).toBe(
      "-Users-iain-Documents-repos-foo",
    );
  });

  it("mangles a short absolute path", () => {
    expect(mangleCwd("/a/b/c")).toBe("-a-b-c");
  });

  it("mangles the filesystem root", () => {
    expect(mangleCwd("/")).toBe("-");
  });

  // CH-01KT50 regression: change worktrees live under ~/.sulis/, a DOTTED
  // path. The `.` must mangle to `-` too — so `/.sulis` becomes `--sulis`
  // (a double dash), matching the real Claude projects dir. The old
  // `/`-only rule kept the dot and never found any change's transcripts.
  it("mangles a dotted ~/.sulis change-worktree path (the . becomes - too)", () => {
    expect(
      mangleCwd("/Users/iain/.sulis/changes/01KT74R6N8ZCCEEHJ0V1CGFB2F/worktree"),
    ).toBe("-Users-iain--sulis-changes-01KT74R6N8ZCCEEHJ0V1CGFB2F-worktree");
  });
});
