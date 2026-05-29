// WP-003 — contract-manifest consumer tests (TDD §2.3 "How (the data seam)";
// ADR-001 read-only cockpit; CF-05/06 consumer side).
//
// The cockpit CONSUMES the shared manifest the renderers (WP-001/002) write
// at `<worktree>/CONTRACT.manifest.json` — it never parses contracts itself.
// `readContractManifest(worktreeRoot)` is the single consumer-side reader:
// it returns a typed, defensive projection of the manifest's two halves
// (`data_contract` + `ui_contract`), and degrades gracefully on an absent
// or corrupt manifest rather than throwing into the serving path.
//
// These tests pin the manifest SHAPE the renderers actually write (mirrored
// from wpx-render-contract's `manifest.update({...})` and _render_ui.py's
// `write_manifest`) so the consumer is built against the real contract mock
// (CF-05), not a guessed shape.

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtemp, rm, writeFile, realpath } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { readContractManifest } from "../routes/_contract-manifest";

describe("readContractManifest (consumer side of the manifest seam)", () => {
  let worktree: string;

  beforeEach(async () => {
    worktree = await realpath(
      await mkdtemp(join(tmpdir(), "contract-manifest-")),
    );
  });

  afterEach(async () => {
    await rm(worktree, { recursive: true, force: true });
  });

  /** Write a CONTRACT.manifest.json matching the renderers' real shape. */
  async function writeManifest(obj: unknown): Promise<void> {
    await writeFile(
      join(worktree, "CONTRACT.manifest.json"),
      JSON.stringify(obj, null, 2),
      "utf8",
    );
  }

  it("parses a full manifest (data_contract present + ui_contract present)", async () => {
    await writeManifest({
      data_contract: {
        format: "servicespec",
        name: "Platforms",
        contracts: [
          { path: "/wt/spec.servicespec.json", format: "servicespec" },
        ],
      },
      contract_html: join(worktree, "CONTRACT.html"),
      ui_contract: "present",
      path: join(worktree, "UI.html"),
    });

    const manifest = await readContractManifest(worktree);

    expect(manifest.present).toBe(true);
    expect(manifest.dataContract).not.toBeNull();
    expect(manifest.dataContract?.format).toBe("servicespec");
    expect(manifest.dataContract?.name).toBe("Platforms");
    expect(manifest.contractHtml).toBe(join(worktree, "CONTRACT.html"));
    expect(manifest.uiContract.status).toBe("present");
    if (manifest.uiContract.status === "present") {
      expect(manifest.uiContract.path).toBe(join(worktree, "UI.html"));
    }
  });

  it("parses a manifest where ui_contract is 'none' (carries a note, not a path)", async () => {
    await writeManifest({
      data_contract: { format: "openapi", name: null, contracts: [] },
      contract_html: join(worktree, "CONTRACT.html"),
      ui_contract: "none",
      note: "No UI contract for this change — it carries no visual contract.",
    });

    const manifest = await readContractManifest(worktree);

    expect(manifest.present).toBe(true);
    expect(manifest.uiContract.status).toBe("none");
    if (manifest.uiContract.status === "none") {
      expect(manifest.uiContract.note).toMatch(/no ui contract/i);
    }
  });

  it("degrades to present:false when the manifest file is absent (never throws)", async () => {
    const manifest = await readContractManifest(worktree);
    expect(manifest.present).toBe(false);
    expect(manifest.dataContract).toBeNull();
    expect(manifest.contractHtml).toBeNull();
    // An absent manifest means no render has happened yet — ui defaults to
    // a "none" note rather than a phantom "present".
    expect(manifest.uiContract.status).toBe("none");
  });

  it("degrades to present:false on a corrupt (non-JSON) manifest (never throws)", async () => {
    await writeFile(
      join(worktree, "CONTRACT.manifest.json"),
      "{ this is not valid json ",
      "utf8",
    );
    const manifest = await readContractManifest(worktree);
    expect(manifest.present).toBe(false);
  });

  it("is defensive about missing keys (partial manifest does not throw)", async () => {
    // Only the data half written (the renderers run independently; either
    // may land first). The consumer must not assume both halves are present.
    await writeManifest({
      data_contract: { format: "raw", name: null, contracts: [] },
      contract_html: join(worktree, "CONTRACT.html"),
    });
    const manifest = await readContractManifest(worktree);
    expect(manifest.present).toBe(true);
    expect(manifest.contractHtml).toBe(join(worktree, "CONTRACT.html"));
    // ui half absent → defaults to a "none" note, not a crash.
    expect(manifest.uiContract.status).toBe("none");
  });
});
