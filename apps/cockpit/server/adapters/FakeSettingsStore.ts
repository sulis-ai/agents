// WP-002 — In-memory FakeSettingsStore (TDD §5.3, §6; WPB-03; ADR-019/020/021).
//
// The simplest reference implementation of the `SettingsStore` port. The
// router unit tests (WP-006) and the client contract test inject this instead
// of paying the cost of shelling out to the Python emitters. It is REAL code
// with REAL behaviour (WPB-03 "never mock what you can implement"), not a mock:
// it mints ids, soft-deletes via an in-memory status, sorts by name, and
// performs the SAME on-disk `present` check the real adapter does — so the
// shared contract (`SettingsStore.contract.ts`) holds identically for both.
//
// State lives on the instance (no module-level state, boring-code.md): each
// `new FakeSettingsStore()` is an empty, isolated store.

import { existsSync } from "node:fs";
import { join } from "node:path";

import type {
  SettingsStore,
  SettingsTree,
  ProductWrite,
  ProjectWrite,
  RepoAttachWrite,
  SettingsProduct,
  SettingsProject,
} from "../ports/SettingsStore";
import { SettingsStoreError } from "../ports/SettingsStore";
import { activeSortedByName } from "./settingsActiveSort";

/** Lifecycle status, mirroring the brain schema's `sys_status` (ADR-020). The
 *  fake only needs the two values the contract exercises. */
type EntityStatus = "active" | "deleted";

/** A repo link as stored internally — `localPath` always set once attached
 *  (unlink removes the whole record). */
type StoredRepo = { localPath: string; primaryBranch: string };

type StoredProject = {
  projectId: string;
  productId: string;
  name: string;
  status: EntityStatus;
  repo: StoredRepo | null;
};

type StoredProduct = {
  productId: string;
  name: string;
  editable: boolean;
  status: EntityStatus;
};

/** The default branch a freshly-attached repo reports, matching the wire
 *  shape's non-optional `primaryBranch`. */
const DEFAULT_PRIMARY_BRANCH = "main";

export class FakeSettingsStore implements SettingsStore {
  private readonly products = new Map<string, StoredProduct>();
  private readonly projects = new Map<string, StoredProject>();
  private idCounter = 0;

  /** Deterministic, monotonically-increasing fake id (TDD §5.3 "mints a
   *  deterministic fake id"). Prefixed so a fake id is never mistaken for a
   *  real ULID. */
  private mintId(prefix: string): string {
    this.idCounter += 1;
    return `fake-${prefix}-${this.idCounter}`;
  }

  async readTree(): Promise<SettingsTree> {
    const products = activeSortedByName(this.products.values()).map((p) =>
      this.toSettingsProduct(p),
    );
    return { products };
  }

  async upsertProduct(input: ProductWrite): Promise<SettingsProduct> {
    if (input.productId !== undefined) {
      const existing = this.products.get(input.productId);
      if (!existing || existing.status !== "active") {
        throw new SettingsStoreError(
          "NOT_FOUND",
          `product ${input.productId} not found`,
        );
      }
      existing.name = input.name;
      return this.toSettingsProduct(existing);
    }

    const productId = this.mintId("product");
    const product: StoredProduct = {
      productId,
      name: input.name,
      editable: true,
      status: "active",
    };
    this.products.set(productId, product);
    return this.toSettingsProduct(product);
  }

  async upsertProject(input: ProjectWrite): Promise<SettingsProject> {
    if (input.projectId !== undefined) {
      const existing = this.projects.get(input.projectId);
      if (!existing || existing.status !== "active") {
        throw new SettingsStoreError(
          "NOT_FOUND",
          `project ${input.projectId} not found`,
        );
      }
      existing.name = input.name;
      return toSettingsProject(existing);
    }

    const parent = this.products.get(input.productId);
    if (!parent || parent.status !== "active") {
      throw new SettingsStoreError(
        "NOT_FOUND",
        `product ${input.productId} not found`,
      );
    }

    const projectId = this.mintId("project");
    const project: StoredProject = {
      projectId,
      productId: input.productId,
      name: input.name,
      status: "active",
      repo: null,
    };
    this.projects.set(projectId, project);
    return toSettingsProject(project);
  }

  async removeProduct(productId: string): Promise<void> {
    const product = this.products.get(productId);
    if (!product || product.status !== "active") {
      throw new SettingsStoreError(
        "NOT_FOUND",
        `product ${productId} not found`,
      );
    }
    product.status = "deleted";
  }

  async removeProject(projectId: string): Promise<void> {
    const project = this.projects.get(projectId);
    if (!project || project.status !== "active") {
      throw new SettingsStoreError(
        "NOT_FOUND",
        `project ${projectId} not found`,
      );
    }
    project.status = "deleted";
  }

  async attachRepo(input: RepoAttachWrite): Promise<SettingsProject> {
    const project = this.requireActiveProject(input.projectId);

    if (!existsSync(input.localPath)) {
      throw new SettingsStoreError(
        "PATH_NOT_FOUND",
        `path ${input.localPath} does not exist`,
      );
    }

    // A folder without a .git child is a valid attach in v1 — `present:false`
    // is a non-blocking warning the UI shows (ADR-021), NOT a hard fail. The
    // `present` flag is computed at read time, so we record only the path.
    project.repo = {
      localPath: input.localPath,
      primaryBranch: DEFAULT_PRIMARY_BRANCH,
    };
    return toSettingsProject(project);
  }

  async unlinkRepo(projectId: string): Promise<SettingsProject> {
    const project = this.requireActiveProject(projectId);
    project.repo = null;
    return toSettingsProject(project);
  }

  private requireActiveProject(projectId: string): StoredProject {
    const project = this.projects.get(projectId);
    if (!project || project.status !== "active") {
      throw new SettingsStoreError(
        "NOT_FOUND",
        `project ${projectId} not found`,
      );
    }
    return project;
  }

  private toSettingsProduct(product: StoredProduct): SettingsProduct {
    const ownProjects = [...this.projects.values()].filter(
      (pr) => pr.productId === product.productId,
    );
    const projects = activeSortedByName(ownProjects).map(toSettingsProject);
    return {
      productId: product.productId,
      name: product.name,
      editable: product.editable,
      projects,
    };
  }
}

/** Project → wire shape. The `present` flag is a real on-disk check
 *  (`{localPath}/.git`), so the fake reports the SAME `present` semantics the
 *  real adapter and `resolveProjectRepo` use. */
function toSettingsProject(project: StoredProject): SettingsProject {
  return {
    projectId: project.projectId,
    name: project.name,
    repo: project.repo
      ? {
          localPath: project.repo.localPath,
          primaryBranch: project.repo.primaryBranch,
          present: existsSync(join(project.repo.localPath, ".git")),
        }
      : null,
  };
}
