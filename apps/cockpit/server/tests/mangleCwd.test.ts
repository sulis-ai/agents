// WP-009 — unit tests for mangleCwd.
//
// Per WP Contract "Mangling rule" + ADR-004 §Context. Replace every
// `/` with `-`; a leading `/` becomes a leading `-`. Observed Claude
// Code behaviour for the `~/.claude/projects/<mangled-cwd>/` directory
// naming convention.

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
});
