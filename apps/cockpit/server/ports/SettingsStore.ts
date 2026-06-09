// WP-002 — SettingsStore port (TDD §2.3; ADR-019/020).
//
// The DOMAIN-OWNED interface the Settings router (WP-006) and the client
// depend on — never the adapter. This is an EXPAND-Create on a port that is
// *ours* (defined inside the cockpit domain), not a wrapper around someone
// else's surface (the discriminator in references/change-primitives.md). Two
// implementations satisfy it: the in-memory `FakeSettingsStore` (WP-002) and
// the real `SpineSettingsAdapter` (WP-005), proven equivalent by the shared
// contract test (`SettingsStore.contract.ts`, MEA-08).
//
// The port speaks the camelCase WIRE shapes (owned by WP-001 in
// shared/api-types). The snake_case brain schema (`Project.source`, etc.)
// stays inside the real adapter, exactly as `ChangeStoreReader` keeps the
// change-store schema inside its adapter.

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern blocks escapes OUT of apps/cockpit/, which import/no-restricted-paths enforces correctly). Mirrors ChangeStoreReader.ts.
import type {
  SettingsTree,
  ProductWrite,
  ProjectWrite,
  RepoAttachWrite,
  SettingsProduct,
  SettingsProject,
  SettingsErrorCode,
} from "../../shared/api-types";

export type {
  SettingsTree,
  ProductWrite,
  ProjectWrite,
  RepoAttachWrite,
  SettingsProduct,
  SettingsProject,
  SettingsErrorCode,
};

/**
 * The cockpit's one and only port to the settings write surface (ADR-019).
 * Every settings mutation in the change goes through one of these calls —
 * never around them. `upsert*` is the unifier: create (no id) mints a fresh
 * id; edit (with id) overwrites in place, because the brain mint is already
 * idempotent on the entity id (ADR-020). `remove*` is a soft-delete
 * (`sys_status="deleted"`) — a removed entity never reappears in `readTree`
 * and no file is ever deleted from disk.
 */
export interface SettingsStore {
  /** The full tree the Settings screen renders — active entities only,
   *  products and their projects each sorted by name. */
  readTree(): Promise<SettingsTree>;

  /** Create (no `productId`) or edit (with `productId`) a product. Idempotent
   *  on the id: re-upserting the same id overwrites in place, never grows the
   *  tree. */
  upsertProduct(input: ProductWrite): Promise<SettingsProduct>;

  /** Create or edit a project under a product (parent immutable on edit, v1). */
  upsertProject(input: ProjectWrite): Promise<SettingsProject>;

  /** Soft-delete a product (`sys_status="deleted"`). The next `readTree`
   *  omits it. Never touches disk. */
  removeProduct(productId: string): Promise<void>;

  /** Soft-delete a project. The next `readTree` omits it. Never touches disk. */
  removeProject(projectId: string): Promise<void>;

  /** Attach an existing local folder to a project (ADR-021 local-path-only).
   *  A missing path raises a `PATH_NOT_FOUND`-coded error; a folder without a
   *  `.git` child still attaches with `present:false`. The founder's folder is
   *  only ever read (`existsSync`), never written. */
  attachRepo(input: RepoAttachWrite): Promise<SettingsProject>;

  /** Clear a project's repo link (`Project.source` → empty). The founder's
   *  folder and its `.git` are never a write target. */
  unlinkRepo(projectId: string): Promise<SettingsProject>;
}

/**
 * The single typed error every `SettingsStore` implementation throws — never
 * an opaque `throw`. Code-on-the-instance keeps the route handler's
 * Result-mapping a flat lookup (no `instanceof` chains), mirroring
 * `ChangeStoreReaderError`. The code is a `SettingsErrorCode`, a subset of the
 * cockpit `ApiErrorCode` envelope (CF-03 — reused, never redeclared).
 */
export class SettingsStoreError extends Error {
  readonly code: SettingsErrorCode;

  constructor(code: SettingsErrorCode, message: string) {
    super(message);
    this.name = "SettingsStoreError";
    this.code = code;
  }
}
