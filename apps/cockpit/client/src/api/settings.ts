// WP-007 — the typed settings client fetcher (errors-are-values; WPF-02).
//
// The consumer-side typed client for the settings seam: a thin fetcher that
// turns each settings route into a Promise<Result<T>> returning a typed value
// or a typed SettingsError — NEVER a thrown opaque for an EXPECTED error. The
// page (WP-008) and forms (WP-009) depend on this: they render
// VALIDATION_FAILED / PATH_NOT_FOUND inline and never catch a thrown settings
// error.
//
// It does NOT call fetch directly (the client inventory gate allow-lists only
// api/client.ts); it goes through the apiGet/apiPost/apiDelete funnel, which
// throws ApiError on non-2xx. This module catches that ApiError and converts it
// into { ok:false, error }. Only a genuine TRANSPORT failure (the network
// rejects with a non-ApiError) propagates — the page treats that as a generic
// retry-able state.
//
// All wire shapes are imported verbatim from shared/api-types (CF-02/06); none
// are redeclared here.
//
// References:
//   - WP-007 Contract (the seven typed methods + invariants).
//   - TDD §8 (Client design — errors are values).
//   - ADR-019 (settings write surface), ADR-021 (local-path-only attach).

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits)
import type {
  SettingsTree,
  ProductWrite,
  ProjectWrite,
  RepoAttachWrite,
  SettingsProduct,
  SettingsProject,
  SettingsErrorCode,
} from "../../../shared/api-types";
import { ApiError, apiGet, apiPost, apiDelete } from "./client";

/** A typed settings error (the SettingsErrorCode subset + a human message). */
export type SettingsError = { code: SettingsErrorCode; message: string };

/** Errors-are-values: a typed success value OR a typed error, never a throw. */
export type Result<T> =
  | { ok: true; value: T }
  | { ok: false; error: SettingsError };

// The settings error codes that may travel in the ApiError envelope. A non-2xx
// whose code isn't one of these (or a non-JSON body → code:null) is mapped to
// WRITE_FAILED — the Internal-category settings code — so the fetcher still
// returns a typed value rather than leaking an opaque code to the UI.
const SETTINGS_ERROR_CODES: readonly SettingsErrorCode[] = [
  "NOT_FOUND",
  "VALIDATION_FAILED",
  "PATH_NOT_FOUND",
  "PATH_NOT_A_REPO",
  "WRITE_FAILED",
  "IMMUTABLE_IMPLICIT",
];

function toSettingsError(err: ApiError): SettingsError {
  const code: SettingsErrorCode =
    err.code !== null &&
    (SETTINGS_ERROR_CODES as readonly string[]).includes(err.code)
      ? (err.code as SettingsErrorCode)
      : "WRITE_FAILED";
  return { code, message: err.message };
}

/**
 * The ONE place ApiError → Result mapping lives (EP-03 — the 7 methods are the
 * consumers). Runs the funnel call; an EXPECTED settings error (a thrown
 * ApiError) becomes { ok:false, error }; a genuine transport failure (any
 * non-ApiError rejection) propagates — the page's generic retry state. Every
 * method below is a thin one-liner over this wrapper, so it carries no
 * behaviour of its own (errors-are-values, WPF-02).
 */
async function request<T>(call: () => Promise<T>): Promise<Result<T>> {
  try {
    return { ok: true, value: await call() };
  } catch (err) {
    if (err instanceof ApiError) {
      return { ok: false, error: toSettingsError(err) };
    }
    throw err;
  }
}

export function getSettings(): Promise<Result<SettingsTree>> {
  return request(() => apiGet<SettingsTree>("/api/settings"));
}

export function writeProduct(
  input: ProductWrite,
): Promise<Result<SettingsProduct>> {
  return request(() =>
    apiPost<SettingsProduct>("/api/settings/products", input),
  );
}

export function removeProduct(id: string): Promise<Result<void>> {
  return request(() =>
    apiDelete<void>(`/api/settings/products/${encodeURIComponent(id)}`),
  );
}

export function writeProject(
  input: ProjectWrite,
): Promise<Result<SettingsProject>> {
  return request(() =>
    apiPost<SettingsProject>("/api/settings/projects", input),
  );
}

export function removeProject(id: string): Promise<Result<void>> {
  return request(() =>
    apiDelete<void>(`/api/settings/projects/${encodeURIComponent(id)}`),
  );
}

export function attachRepo(
  input: RepoAttachWrite,
): Promise<Result<SettingsProject>> {
  return request(() =>
    apiPost<SettingsProject>(
      `/api/settings/projects/${encodeURIComponent(input.projectId)}/repo`,
      input,
    ),
  );
}

export function unlinkRepo(
  projectId: string,
): Promise<Result<SettingsProject>> {
  return request(() =>
    apiDelete<SettingsProject>(
      `/api/settings/projects/${encodeURIComponent(projectId)}/repo`,
    ),
  );
}
