"""
Phase 1.16 — Deployment Topology (repo-wide).

Catalogues every deployment-related artifact across the repo:
  - Dockerfile / docker-compose
  - Kubernetes manifests (apiVersion: apps/v1, batch/v1, etc.)
  - Helm charts (Chart.yaml)
  - Terraform / Pulumi
  - GitHub Actions / CircleCI / GitLab CI / Argo CD / Flux
  - Vercel / Netlify / Fly / Heroku / Serverless / AWS SAM / AWS CDK / Skaffold
  - **Sulis manifests** (apiVersion: sulis.io/v1) with sub-kind specifics
    (Workload, Application, BusinessManifest, Plan, DomainRole, ...).

Secret references are captured by NAME only — never values.

PyYAML is optional. When absent, a minimal regex parser handles the most
common cases (single-doc and multi-doc YAML, top-level scalar fields).
"""

from __future__ import annotations

import fnmatch
import os
import re
import time
from pathlib import Path
from typing import Any

from ..config import (
    DEPLOYMENT_KIND_PATTERNS,
    DEPLOYMENT_SCAN_MAX_FILES,
    DEPLOYMENT_SCAN_SKIP_DIRS,
    DEPLOYMENT_YAML_PROBE_BYTES,
    SULIS_API_VERSION,
    SULIS_KNOWN_KINDS,
)
from ..models import (
    DeploymentArtifact,
    DeploymentPayload,
    RepoInput,
    RunnerResult,
)
from .base import make_result, now_iso

try:  # PyYAML is optional
    import yaml  # type: ignore[import-not-found]
    _HAS_YAML = True
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]
    _HAS_YAML = False


# ─── Regex helpers ────────────────────────────────────────────────────────

_API_VERSION_RE = re.compile(
    rb"^\s*apiVersion\s*:\s*(\S+)", re.MULTILINE,
)
_KIND_RE = re.compile(
    rb"^\s*kind\s*:\s*(\S+)", re.MULTILINE,
)
_METADATA_NAME_RE = re.compile(
    rb"^\s*name\s*:\s*[\"']?([A-Za-z0-9_.-]+)[\"']?", re.MULTILINE,
)
_GH_ACTIONS_SECRET_RE = re.compile(
    r"\$\{\{\s*secrets\.([A-Z0-9_]+)\s*\}\}",
)
_ENV_INTERP_SECRET_RE = re.compile(
    r"\$\{([A-Z][A-Z0-9_]{2,})\}",
)
_K8S_SECRET_REF_RE = re.compile(
    r"secretKeyRef\s*:\s*\n\s*name\s*:\s*[\"']?([A-Za-z0-9_.-]+)[\"']?",
)

_ENV_PATH_PATTERNS: tuple[tuple[re.Pattern[str], int], ...] = (
    (re.compile(r"/environments/([a-z0-9-]+)/", re.IGNORECASE), 1),
    (re.compile(r"\bdeploy[-_](dev|development|stg|staging|prod|production|qa|test)\b",
                re.IGNORECASE), 1),
    (re.compile(r"\b(dev|development|stg|staging|prod|production|qa|test)\b/",
                re.IGNORECASE), 1),
)


def _infer_env_from_path(rel_path: str) -> str | None:
    norm = rel_path.lower().replace("\\", "/")
    for pat, group in _ENV_PATH_PATTERNS:
        m = pat.search(norm)
        if m:
            val = m.group(group).lower()
            # Canonicalise
            if val in ("development", "dev"):
                return "dev"
            if val in ("staging", "stg", "stage"):
                return "staging"
            if val in ("production", "prod"):
                return "prod"
            if val in ("qa", "test"):
                return "qa"
            return val
    return None


def _scan_secret_refs(content: str) -> list[str]:
    """Return secret NAMES referenced in `content`. Deterministic order."""
    names: list[str] = []
    seen: set[str] = set()
    for pat in (_GH_ACTIONS_SECRET_RE, _ENV_INTERP_SECRET_RE, _K8S_SECRET_REF_RE):
        for m in pat.finditer(content):
            n = m.group(1)
            if n not in seen:
                seen.add(n)
                names.append(n)
    return names


# ─── File enumeration ─────────────────────────────────────────────────────


def _should_skip_dir(dirname: str) -> bool:
    return dirname in DEPLOYMENT_SCAN_SKIP_DIRS or dirname.startswith(".")


_CANDIDATE_EXTS: frozenset[str] = frozenset({
    ".yaml", ".yml", ".tf", ".tfvars", ".hcl",
    ".json", ".toml",  # cdk.json, vercel.json, fly.toml, netlify.toml
})

_CANDIDATE_BASENAMES: frozenset[str] = frozenset({
    "Dockerfile", "Procfile", "WORKSPACE", "WORKSPACE.bazel", "MODULE.bazel",
})

_CANDIDATE_GLOBS: tuple[str, ...] = (
    "Dockerfile.*", "*.Dockerfile",
    "Pulumi.*",
)


def _is_candidate_file(name: str) -> bool:
    """Cheap pre-filter — is this file plausibly a deployment artifact?

    Saves walking millions of source-code files in big repos. Anything that
    matches gets the full classification pass; anything that doesn't is
    silently ignored. Aggressive enough that the cap is reserved for
    pathological cases (e.g. a directory full of generated YAMLs).
    """
    if name in _CANDIDATE_BASENAMES:
        return True
    ext = Path(name).suffix.lower()
    if ext in _CANDIDATE_EXTS:
        return True
    for glob in _CANDIDATE_GLOBS:
        if fnmatch.fnmatch(name, glob):
            return True
    return False


def _iter_repo_files(root: Path, max_files: int) -> tuple[list[Path], int]:
    """Walk the repo, returning (candidate-files, files_skipped_cap).

    Pre-filters by `_is_candidate_file` so the per-tool cap protects against
    pathological cases (thousands of generated YAMLs) rather than against
    normal source-file volume.

    Skip rules:
      - DEPLOYMENT_SCAN_SKIP_DIRS by name (covers EXTRA_EXCLUDE_DIRS plus
        test/fixture subtrees).
      - Dotfile-prefixed directories EXCEPT the well-known deployment dirs
        `.github`, `.circleci`, `.gitlab` — workflows live there.
    """
    files: list[Path] = []
    skipped = 0
    allowed_dot_dirs = {".github", ".circleci", ".gitlab"}
    skip_set = set(DEPLOYMENT_SCAN_SKIP_DIRS)

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames
            if d not in skip_set
            and (not d.startswith(".") or d in allowed_dot_dirs)
        ]
        for fn in filenames:
            if not _is_candidate_file(fn):
                continue
            if len(files) >= max_files:
                skipped += 1
                continue
            files.append(Path(dirpath) / fn)
    return files, skipped


# ─── Kind classification ──────────────────────────────────────────────────


def _read_head(path: Path, n_bytes: int) -> bytes:
    try:
        with path.open("rb") as fh:
            return fh.read(n_bytes)
    except OSError:
        return b""


def _filename_matches(name: str, pattern: str) -> bool:
    return fnmatch.fnmatch(name, pattern)


def _classify(
    path: Path, root: Path
) -> tuple[str, bytes] | None:
    """Return (kind, head_bytes) for a deployment-related file, or None.

    Walks the DEPLOYMENT_KIND_PATTERNS table in order. Path-sensitive kinds
    (`github-actions`, `circleci`) check the relative parent path too.
    """
    name = path.name
    ext = path.suffix.lower()
    rel_parts = path.relative_to(root).parts
    parent_rel = "/".join(rel_parts[:-1])

    # First pass: filename / ext / dirfile / path-aware filters.
    for kind, signal_type, signal_value in DEPLOYMENT_KIND_PATTERNS:
        if signal_type == "filename":
            if name == signal_value:
                # path-sensitive cases
                if kind == "github-actions" and ".github/workflows" not in parent_rel:
                    continue
                if kind == "circleci" and ".circleci" not in parent_rel:
                    continue
                return kind, b""
        elif signal_type == "filename-glob":
            if _filename_matches(name, signal_value):
                if kind == "github-actions" and ".github/workflows" not in parent_rel:
                    continue
                if kind == "circleci" and ".circleci" not in parent_rel:
                    continue
                return kind, b""
        elif signal_type == "ext":
            if ext == signal_value:
                return kind, b""
        elif signal_type == "dirfile":
            # handled per-dir, not per-file (see _scan_dirfile_kinds)
            continue

    # Second pass: YAML apiVersion sniff and content sniff.
    if ext in (".yaml", ".yml"):
        head = _read_head(path, DEPLOYMENT_YAML_PROBE_BYTES)
        if not head:
            return None
        # Find first apiVersion line
        m = _API_VERSION_RE.search(head)
        if not m:
            # Try content-based kinds (aws-sam Transform)
            for kind, signal_type, signal_value in DEPLOYMENT_KIND_PATTERNS:
                if signal_type == "content" and signal_value.encode() in head:
                    return kind, head
            return None
        api = m.group(1).decode("utf-8", errors="ignore")
        for kind, signal_type, signal_value in DEPLOYMENT_KIND_PATTERNS:
            if signal_type == "yaml-api":
                if re.search(signal_value, api):
                    return kind, head
        return None
    return None


def _classify_from_api_version(api: str) -> str | None:
    """Map a YAML apiVersion string to a deployment kind."""
    if not api:
        return None
    for kind, signal_type, signal_value in DEPLOYMENT_KIND_PATTERNS:
        if signal_type == "yaml-api" and re.search(signal_value, api):
            return kind
    return None


def _scan_dirfile_kinds(root: Path) -> list[DeploymentArtifact]:
    """Detect dir-level kinds (e.g. helm-chart via Chart.yaml)."""
    artifacts: list[DeploymentArtifact] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames
            if d not in DEPLOYMENT_SCAN_SKIP_DIRS
            and not d.startswith(".")
        ]
        for kind, signal_type, signal_value in DEPLOYMENT_KIND_PATTERNS:
            if signal_type == "dirfile" and signal_value in filenames:
                p = Path(dirpath) / signal_value
                rel = str(p.relative_to(root))
                artifacts.append(DeploymentArtifact(
                    kind=kind,
                    sub_kind=None,
                    name=Path(dirpath).name,
                    path=rel,
                    line=None,
                    environment=_infer_env_from_path(rel),
                    target_platform=_platform_for_kind(kind),
                    secret_references=[],
                    extras={},
                ))
    return artifacts


# ─── Sulis + k8s parsing ──────────────────────────────────────────────────


def _platform_for_kind(kind: str) -> str | None:
    mapping = {
        "dockerfile": "docker",
        "docker-compose": "docker",
        "k8s-manifest": "kubernetes",
        "helm-chart": "kubernetes",
        "argocd": "kubernetes",
        "flux": "kubernetes",
        "skaffold": "kubernetes",
        "sulis-manifest": "sulis",
        "terraform": "terraform",
        "pulumi": "pulumi",
        "aws-sam": "aws-lambda",
        "aws-cdk": "aws",
        "vercel": "vercel",
        "netlify": "netlify",
        "fly": "fly",
        "heroku": "heroku",
        "serverless-framework": "aws-lambda",
        "github-actions": "ci",
        "circleci": "ci",
        "gitlab-ci": "ci",
    }
    return mapping.get(kind)


def _parse_yaml_docs(path: Path) -> list[dict[str, Any]]:
    """Parse multi-doc YAML. PyYAML preferred; regex fallback otherwise."""
    if _HAS_YAML:
        try:
            with path.open("r", encoding="utf-8", errors="replace") as fh:
                docs = list(yaml.safe_load_all(fh))
            return [d for d in docs if isinstance(d, dict)]
        except Exception:
            return []
    # Regex fallback — only extracts apiVersion, kind, metadata.name, and
    # flat top-level spec scalars. Sufficient for sulis manifests.
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    docs: list[dict[str, Any]] = []
    raw_docs = re.split(r"^---\s*$", text, flags=re.MULTILINE)
    for raw in raw_docs:
        if not raw.strip():
            continue
        doc: dict[str, Any] = {}
        meta: dict[str, Any] = {}
        spec: dict[str, Any] = {}
        current_block: dict[str, Any] | None = None
        for line in raw.splitlines():
            if not line or line.lstrip().startswith("#"):
                continue
            # Top-level key
            m_top = re.match(r"^([A-Za-z][A-Za-z0-9_]*)\s*:\s*(.*)$", line)
            if m_top and not line.startswith(" "):
                key = m_top.group(1)
                val = m_top.group(2).strip()
                if key == "metadata":
                    current_block = meta
                elif key == "spec":
                    current_block = spec
                else:
                    current_block = None
                    if val and not val.startswith("{"):
                        doc[key] = val.strip("'\"")
                continue
            # Indented entry under metadata/spec
            m_sub = re.match(r"^\s+([A-Za-z][A-Za-z0-9_-]*)\s*:\s*(.*)$", line)
            if m_sub and current_block is not None:
                key = m_sub.group(1)
                val = m_sub.group(2).strip()
                if val and not val.startswith("{"):
                    current_block[key] = val.strip("'\"")
        if meta:
            doc["metadata"] = meta
        if spec:
            doc["spec"] = spec
        if doc.get("apiVersion") or doc.get("kind"):
            docs.append(doc)
    return docs


def _extract_sulis_workload_extras(spec: dict[str, Any]) -> dict[str, Any]:
    extras: dict[str, Any] = {}
    for key in ("image", "port", "replicas", "memory", "cpu"):
        if key in spec:
            extras[key] = spec[key]
    if "healthCheck" in spec and isinstance(spec["healthCheck"], dict):
        extras["health_check_path"] = spec["healthCheck"].get("path")
    elif "health_check_path" in spec:
        extras["health_check_path"] = spec["health_check_path"]
    env = spec.get("env") or spec.get("environment")
    env_names: list[str] = []
    if isinstance(env, list):
        for entry in env:
            if isinstance(entry, dict) and "name" in entry:
                env_names.append(str(entry["name"]))
            elif isinstance(entry, str):
                # KEY=value or KEY style
                env_names.append(entry.split("=", 1)[0])
    elif isinstance(env, dict):
        env_names = list(env.keys())
    if env_names:
        extras["env_var_names"] = env_names
    return extras


def _extract_application_extras(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        k: spec[k] for k in ("workloadType", "compute", "scaling", "type")
        if k in spec
    }


def _extract_business_manifest_extras(doc: dict[str, Any]) -> dict[str, Any]:
    extras: dict[str, Any] = {}
    spec = doc.get("spec", {})
    if isinstance(spec, dict):
        for k in ("businessType", "version", "schemaVersion", "iteration"):
            if k in spec:
                extras[k] = spec[k]
    return extras


# ─── Runner ────────────────────────────────────────────────────────────────


class DeploymentRunner:
    PHASE: str = "1.16"
    TOOL: str = "deployment-scan"

    def run_repo(self, inp: RepoInput) -> RunnerResult:
        started_iso = now_iso()
        started_mono = time.monotonic()
        warnings: list[str] = []

        root = Path(inp.repo_root).resolve()

        all_files, skipped_cap = _iter_repo_files(root, DEPLOYMENT_SCAN_MAX_FILES)

        artifacts: list[DeploymentArtifact] = []

        # Pass 1: per-file classification.
        for f in all_files:
            classification = _classify(f, root)
            if classification is None:
                continue
            kind, head = classification
            rel = str(f.relative_to(root))
            sub_kind: str | None = None
            name: str | None = None
            line: int | None = None
            extras: dict[str, Any] = {}
            secret_refs: list[str] = []

            if kind in ("k8s-manifest", "sulis-manifest", "argocd", "flux"):
                docs = _parse_yaml_docs(f)
                if not docs:
                    if head:
                        m_kind = _KIND_RE.search(head)
                        if m_kind:
                            sub_kind = m_kind.group(1).decode("utf-8", errors="ignore")
                    artifacts.append(DeploymentArtifact(
                        kind=kind, sub_kind=sub_kind, name=name, path=rel,
                        line=line, environment=_infer_env_from_path(rel),
                        target_platform=_platform_for_kind(kind),
                        secret_references=[], extras={},
                    ))
                    continue
                try:
                    text = f.read_text(encoding="utf-8", errors="replace")
                    secret_refs = _scan_secret_refs(text)
                except OSError:
                    secret_refs = []
                # Per-doc classification: a multi-doc YAML can mix
                # sulis/k8s/argocd/flux. Re-derive kind from each doc's apiVersion.
                for doc in docs:
                    api = (doc.get("apiVersion") or "").strip()
                    doc_kind = _classify_from_api_version(api) or kind
                    sk = (doc.get("kind") or "").strip() or None
                    meta = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
                    dname = meta.get("name") if isinstance(meta, dict) else None
                    spec = doc.get("spec") if isinstance(doc.get("spec"), dict) else {}
                    d_extras: dict[str, Any] = {}
                    if doc_kind == "sulis-manifest":
                        if sk == "Workload" and isinstance(spec, dict):
                            d_extras = _extract_sulis_workload_extras(spec)
                        elif sk == "Application" and isinstance(spec, dict):
                            d_extras = _extract_application_extras(spec)
                        elif sk in ("BusinessManifest", "BusinessManifestDelta"):
                            d_extras = _extract_business_manifest_extras(doc)
                        if sk and sk not in SULIS_KNOWN_KINDS:
                            warnings.append(
                                f"{rel}: sulis kind '{sk}' not in SULIS_KNOWN_KINDS"
                            )
                    artifacts.append(DeploymentArtifact(
                        kind=doc_kind, sub_kind=sk, name=dname, path=rel,
                        line=None,
                        environment=_infer_env_from_path(rel),
                        target_platform=_platform_for_kind(doc_kind),
                        secret_references=secret_refs,
                        extras=d_extras,
                    ))
                continue

            # Non-YAML or non-multi-doc kinds.
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                content = ""
            secret_refs = _scan_secret_refs(content) if content else []

            if kind == "dockerfile":
                # Extract base image, exposed port if available.
                m_from = re.search(
                    r"^\s*FROM\s+(\S+)", content, re.MULTILINE | re.IGNORECASE,
                )
                if m_from:
                    extras["base_image"] = m_from.group(1)
                m_expose = re.search(
                    r"^\s*EXPOSE\s+(\d+)", content, re.MULTILINE | re.IGNORECASE,
                )
                if m_expose:
                    extras["port"] = int(m_expose.group(1))

            artifacts.append(DeploymentArtifact(
                kind=kind, sub_kind=sub_kind, name=name, path=rel,
                line=line,
                environment=_infer_env_from_path(rel),
                target_platform=_platform_for_kind(kind),
                secret_references=secret_refs,
                extras=extras,
            ))

        # Pass 2: dir-level kinds (helm-chart).
        artifacts.extend(_scan_dirfile_kinds(root))

        # Aggregate.
        by_kind: dict[str, int] = {}
        by_env: dict[str, int] = {}
        sulis_kinds_seen: set[str] = set()
        platforms_seen: set[str] = set()
        for a in artifacts:
            by_kind[a.kind] = by_kind.get(a.kind, 0) + 1
            if a.environment:
                by_env[a.environment] = by_env.get(a.environment, 0) + 1
            if a.kind == "sulis-manifest" and a.sub_kind:
                sulis_kinds_seen.add(a.sub_kind)
            if a.target_platform:
                platforms_seen.add(a.target_platform)

        payload = DeploymentPayload(
            artifacts=artifacts,
            by_kind=dict(sorted(by_kind.items())),
            by_environment=dict(sorted(by_env.items())),
            sulis_kinds_present=sorted(sulis_kinds_seen),
            target_platforms=sorted(platforms_seen),
            files_scanned=len(all_files),
            files_skipped_cap=skipped_cap,
            yaml_parser="pyyaml" if _HAS_YAML else "regex-fallback",
        )

        if not _HAS_YAML:
            warnings.append(
                "PyYAML not installed; using regex fallback parser. "
                "Install via `pipx inject detect-secrets PyYAML` or `pip install pyyaml`."
            )

        from dataclasses import asdict
        return make_result(
            phase=self.PHASE,
            tool=self.TOOL,
            started_at=started_iso,
            started_monotonic=started_mono,
            payload=asdict(payload),
            raw_output_path=None,
            warnings=warnings,
        )
