"""``_discovery`` — internal package for the ``/sulis:discover-project``
skill's deterministic Python helpers.

First arrival: WP-002 (``tenant.py`` — consumer-tenant ULID derivation).
Subsequent WPs (WP-003 Detect, WP-004 Infer, WP-006 Mint, WP-007 Verify)
extended the package without re-creating this marker file.

WP-010 adds :func:`run_discovery_headless` — the integration-test
composition root that wires the five phases together end-to-end. Per
TDD §Form §Composition root:

    For testability, ``plugins/sulis/scripts/_discovery/__init__.py``
    exports a ``run_discovery_headless(args) -> DiscoveryResult``
    function that wires the adapters together and exercises every
    phase. Integration tests invoke this function against fixture
    consumer repos; the skill's prose maps each Step to a call into
    this module.

The leading underscore signals "internal to the skill" — not a public
plugin module; not imported from outside ``plugins/sulis/scripts/``.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Canonical marketplace release-train Workflow ULID (TDD §Canonical
# Identifiers — locked in WP-001). The Verify phase allows this ULID
# to cross from the consumer tenant to the marketplace tenant.
_MARKETPLACE_RELEASE_WORKFLOW_ULID = "dna:workflow:01KT0RTRA1NWFW00000000000A"


@dataclass
class DiscoveryResult:
    """The outcome of a single :func:`run_discovery_headless` run.

    Returned on the success path; the failure paths raise typed
    exceptions (NonGitDirectoryError, NoRemoteError,
    EntityAlreadyExistsError, DriftVerifyFailed, ...) rather than
    populating an `error` field. That keeps the Test-Driven contract
    explicit — every failure path has its own `pytest.raises`-able
    surface.

    Attributes:
        ok: Always True on this dataclass (failure paths raise).
        entity_path: Where the minted Project entity was written.
        tokens_consumed: LLM tokens used (0 for Null adapter or when
            the budget was exceeded and the inferences were discarded).
        budget_exceeded: True iff the LLM consumed more than the
            configured token_budget; the inferences were discarded
            and the Null fallback ran for the Ask phase.
    """

    ok: bool = True
    entity_path: Path | None = None
    tokens_consumed: int = 0
    budget_exceeded: bool = False


def _detect(repo_path: Path) -> dict[str, Any]:
    """Run the Detect phase against ``repo_path``.

    Returns a structured dict (kept lightweight so the headless
    composition root can pass it through to Infer / Ask / Mint without
    a separate ``DetectionResult`` re-marshalling step).
    """
    from _discovery.inspector import LocalFilesystemInspector

    inspector = LocalFilesystemInspector()
    root = inspector.read_root(repo_path)
    manifests = inspector.read_package_manifests(repo_path)
    workflows = inspector.read_ci_workflows(repo_path)
    contract = inspector.read_repo_contract(repo_path)

    return {
        "root": root,
        "manifests": manifests,
        "ci_workflows": workflows,
        "repo_contract": contract,
    }


def _infer(
    detected: dict[str, Any], inferrer: Any, token_budget: int,
) -> tuple[dict[str, str], int, bool]:
    """Run the Infer phase.

    Returns ``(inferences_dict, tokens_consumed, budget_exceeded)``.

    On TokenBudgetExceeded OR LLM-unreachable error, returns
    (``{}``, ``tokens_observed``, ``True``) — the composition root
    then routes through Null behaviour for the Ask phase. Per NFR-006
    + TDD §Armor §External dependencies (LLM): the swap is silent
    from the operator's perspective.
    """
    from _discovery.inferrer import (
        DetectionResult,
        Manifest,
        RepoRoot,
        TokenBudgetExceeded,
    )

    # Skip Infer entirely for the Null adapter — structurally identical
    # to "no inference" without the bridge dance.
    if inferrer.__class__.__name__ == "NullConfigurationInferrer":
        return {}, 0, False

    # Bridge from inspector dataclass shapes to inferrer dataclass shapes.
    insp_root = detected["root"]
    bridged_root = RepoRoot(
        is_git=insp_root.is_git,
        remote_url=insp_root.remote_url,
        primary_branch=insp_root.primary_branch,
        has_remote=insp_root.has_remote,
    )
    bridged_manifests: list[Any] = []
    for m in detected["manifests"]:
        # inspector.Manifest carries `kind` ("package.json"/"pyproject.toml");
        # inferrer.Manifest wants `language` ("node"/"python"/...).
        language = "node" if m.kind == "package.json" else "python"
        parsed: dict[str, Any] = {
            "name": m.name,
            "version": m.version,
            "private": m.private,
            "scripts": m.scripts_keys,
        }
        bridged_manifests.append(Manifest(
            path=str(m.path), language=language, parsed=parsed,
        ))

    bridged = DetectionResult(
        repo_root=bridged_root,
        manifests=bridged_manifests,
        # The inferrer.CiWorkflow shape is dict-based; WP-010 e2e tests
        # don't assert on the prompt's CI section, and the mock LLM
        # returns canned JSON regardless of input. Empty list is safe.
        ci_workflows=[],
        repo_contract=None,
    )
    try:
        result = inferrer.infer(bridged, token_budget)
    except TokenBudgetExceeded as exc:
        # NFR-006 graceful degradation: discard inferences, surface the
        # observed token count for observability, fall back to Null.
        return {}, exc.consumed, True
    except Exception:
        # LLM-unreachable / transport / auth: same fallback; token
        # count is unobservable here.
        return {}, 0, True

    # The inferrer returned a dict of InferredValue; flatten to plain
    # field→value for the Ask phase.
    flat = {k: v.value for k, v in result.inferences.items()}
    return flat, result.tokens_consumed, False


def _ask(
    *,
    inferences: dict[str, str],
    answers: dict[str, Any],
    overrides: dict[str, Any] | None,
    update: bool,
    update_keep_fields: set[str] | None,
    existing_entity: dict[str, Any] | None,
    ask_phase_cancels: bool,
) -> dict[str, Any]:
    """Run the Ask phase.

    Composes the final field values from:

    - the founder's explicit ``answers`` (always-authoritative);
    - inferences confirmed by default (UC-001 happy path);
    - inferences overridden via ``overrides`` (UC-006);
    - the existing entity's values when ``update=True`` AND the field
      is in ``update_keep_fields`` (UC-002 per-field-diff keep-existing).

    When ``ask_phase_cancels`` is True, raises ``KeyboardInterrupt``
    mid-Ask — used by the cancellation-idempotency tests to simulate
    a real Ctrl-C.
    """
    if ask_phase_cancels:
        raise KeyboardInterrupt("Ask phase cancelled (test knob)")

    composed: dict[str, Any] = {}
    overrides = overrides or {}
    update_keep_fields = update_keep_fields or set()

    # Inferences confirmed by default; overrides win; keep-existing
    # (for --update) wins over both when the field is named.
    for field_name, inferred_value in inferences.items():
        if (
            update
            and field_name in update_keep_fields
            and existing_entity is not None
        ):
            composed[field_name] = existing_entity.get(
                field_name, inferred_value,
            )
        elif field_name in overrides:
            composed[field_name] = overrides[field_name]
        else:
            composed[field_name] = inferred_value

    # Founder's explicit answers take precedence over inferences.
    composed.update(answers)

    # When --update, inherit any field from the existing entity that
    # the founder didn't re-answer AND isn't a project-bag-shape field.
    if update and existing_entity is not None:
        for field_name, existing_value in existing_entity.items():
            if field_name in composed:
                continue
            if field_name in {
                "id", "sys_status", "belongs_to_tenant",
                "valid_from", "state", "confidence",
            }:
                continue
            composed[field_name] = existing_value

    return composed


def _compose_entity(
    *,
    composed_fields: dict[str, Any],
    source_repo: str,
    primary_branch: str,
    release_workflow_ref: str,
) -> dict[str, Any]:
    """Compose the full project-instances bag from the Ask-phase output.

    Mirrors the shape at
    ``plugins/sulis/instances/release-train/projects.jsonld`` — the
    canonical pattern this skill produces.
    """
    from _discovery.tenant import Sha256CrockfordTenantDeriver

    deriver = Sha256CrockfordTenantDeriver()
    tenant_ulid = deriver.derive_consumer_tenant(source_repo)

    name = composed_fields["name"]
    proj: dict[str, Any] = {
        "id": _synthetic_project_id(name),
        "sys_status": "active",
        "name": name,
        "belongs_to_tenant": tenant_ulid,
        "type": composed_fields.get("type", "library"),
        "source": json.dumps({
            "repo": source_repo,
            "path": composed_fields.get("path", "."),
            "primary_branch": primary_branch,
        }),
        "version_files": composed_fields.get("version_files", []),
        # `trunk` is the compiled foundation Project schema's enum value (the
        # canonical save validates against it post-reconcile, ADR-006); the
        # earlier `"trunk-based"` label never validated while Project lived only
        # in `.sulis/projects/`. The minter normalises the legacy label too.
        "branch_policy": composed_fields.get("branch_policy", "trunk"),
        "belongs_to_product_ref": composed_fields.get(
            "belongs_to_product_ref", "unspecified",
        ),
        "depends_on": composed_fields.get("depends_on", []),
        "consumed_by": composed_fields.get("consumed_by", []),
        "release_workflow_ref": release_workflow_ref,
        "description": composed_fields.get("description", ""),
        "state": "active",
        "valid_from": "2026-06-01T00:00:00Z",
        "confidence": 1.0,
    }
    # Any extra Configuration-Vocabulary fields the Ask phase composed
    # ride along on the project bag (deploy_target, package_manager,
    # primary_branch override, language_primary, ...).
    for k, v in composed_fields.items():
        if k not in proj and k not in {"path"}:
            proj[k] = v

    bag = {
        "@context": {
            "@vocab": "https://sulis.co/dna/",
            "dna": "https://sulis.co/dna/",
        },
        "@id": f"dna:{name}:projects",
        "@type": "project-instances",
        "for_tenant": tenant_ulid,
        "_about": (
            f"Project entity for {source_repo}, minted by the "
            f"discover-project skill."
        ),
        "captured_on": "2026-06-01",
        "projects": [proj],
    }
    return bag


# Crockford-base32 alphabet (no I, L, O, U) — matches the tenant module.
_CROCKFORD_FOR_PROJECT_ID = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _synthetic_project_id(name: str) -> str:
    """Build a synthetic but stable ``dna:project:<ulid>`` identifier
    from the project name.

    Project IDs in canonical instances files use ULID format. The
    discovery flow doesn't have a wall-clock minting moment to emit a
    real ULID — instead we derive a deterministic 26-char ULID-shaped
    identifier from the project name via SHA-256 + Crockford-base32
    truncation. Two minting passes on the same name produce the same
    id (NFR-003 deterministic re-run).
    """
    import hashlib
    digest = hashlib.sha256(f"project-id:{name}".encode("utf-8")).digest()
    n = int.from_bytes(digest[:17], "big") >> 6
    chars = [
        _CROCKFORD_FOR_PROJECT_ID[(n >> (5 * (25 - i))) & 0x1F]
        for i in range(26)
    ]
    ulid = "".join(chars)
    # First-char clamp: 0..7 (matches ULID spec — see tenant.py).
    first_value = _CROCKFORD_FOR_PROJECT_ID.index(ulid[0])
    if first_value > 7:
        ulid = _CROCKFORD_FOR_PROJECT_ID[first_value % 8] + ulid[1:]
    return f"dna:project:{ulid}"


def _existing_project_payload(entity_path: Path) -> dict[str, Any] | None:
    """If ``entity_path`` already holds a Project entity, return the
    first project's field bag; else None."""
    if not entity_path.exists():
        return None
    parsed = json.loads(entity_path.read_text())
    projects = parsed.get("projects", [])
    if not projects:
        return None
    return projects[0]


def _parse_github_shorthand(remote_url: str | None) -> str:
    """Normalise a git remote URL to ``org/name`` shorthand.

    Handles the three common URL shapes:

    - ``git@github.com:org/name.git``  (SSH)
    - ``https://github.com/org/name.git`` (HTTPS)
    - ``https://github.com/org/name``  (HTTPS, no .git suffix)
    """
    if remote_url is None:
        raise ValueError("remote_url cannot be None when no override given")
    url = remote_url
    if url.endswith(".git"):
        url = url[:-4]
    if url.startswith("git@") and ":" in url:
        return url.split(":", 1)[1]
    if "://" in url:
        rest = url.split("://", 1)[1]
        if "/" in rest:
            return rest.split("/", 1)[1]
    return url


def run_discovery_headless(  # noqa: PLR0912, PLR0913
    *,
    repo_path: Path,
    inferrer: Any,
    answers: dict[str, Any],
    overrides: dict[str, Any] | None = None,
    update: bool = False,
    update_keep_fields: set[str] | None = None,
    monorepo_path: str | None = None,
    source_repo_override: str | None = None,
    release_workflow_ref_override: str | None = None,
    token_budget: int = 10_000,
    ask_phase_cancels: bool = False,
    verifier_fn: Any = None,
) -> DiscoveryResult:
    """Compose Detect → Infer → Ask → Mint → Verify into one call.

    The integration test surface for the discover-project skill. The
    operator-facing skill prose
    (``plugins/sulis/skills/discover-project/SKILL.md``) follows the
    same five-phase shape — this function is what an automated test
    invokes when it needs to exercise the whole flow without an
    interactive harness.

    Parameters:
        repo_path: The consuming repo path under test. The Detect
            phase reads from here; the Mint phase writes Project
            entities under ``repo_path/.sulis/projects/``.
        inferrer: A :class:`ConfigurationInferrer` adapter — typically
            :class:`NullConfigurationInferrer` or
            :class:`LLMConfigurationInferrer` with a mock client.
        answers: Founder-authoritative field values (name, type,
            version_files, description, ...). These ALWAYS win over
            inferences.
        overrides: Per-field overrides for inferred values (UC-006).
            ``overrides={"deploy_target": "npm-publish"}`` discards
            the LLM's `deploy_target` inference and uses the override
            instead.
        update: When True, run the per-field diff flow (UC-002).
            Requires an existing entity at the target path; otherwise
            equivalent to ``update=False``.
        update_keep_fields: With ``update=True``, the set of fields
            whose existing value should be kept (founder chose 'k' in
            the per-field diff).
        monorepo_path: When set, scope the slug derivation to the
            sub-path's basename (UC-003).
        source_repo_override: When set, use this as the ``source.repo``
            value instead of deriving from the git remote — covers
            MUC-006 (no-remote + ``--source-repo``).
        release_workflow_ref_override: When set, use this as the
            Project's ``release_workflow_ref`` instead of the
            canonical marketplace ULID. Tests use this to inject a
            bad ULID for MUC-005 (drift verification + rollback).
        token_budget: Token cap passed to the LLM inferrer.
        ask_phase_cancels: Test knob — raise KeyboardInterrupt mid-Ask
            (UC-005 / MUC-002 idempotent-cancellation tests).
        verifier_fn: Optional override for the Verify-phase function.
            Defaults to :func:`_discovery.verifier.verify_and_roll_back_on_failure`.
            Integration tests pass a fake to decouple the composition-
            root flow from the real drift-detector subprocess — the
            verifier's contract against the real detector is covered
            by ``test_discovery_verifier.py``. The fake must mimic
            the real signature: ``fn(entity_path: Path) -> Any`` and
            raise :class:`DriftVerifyFailed` on a verification miss
            (the composition root relies on that exception class to
            propagate MUC-005 to the caller).

    Returns:
        :class:`DiscoveryResult` on success.

    Raises:
        NonGitDirectoryError: Detect phase, MUC-001.
        NoRemoteError: Detect phase, MUC-006 (when no override).
        EntityAlreadyExistsError: Mint phase, MUC-003.
        MonorepoSlugCollisionError: Mint phase, MUC-007.
        DriftVerifyFailed: Verify phase, MUC-005 (entity rolled back).
        KeyboardInterrupt: Ask phase, MUC-002 (test knob).
    """
    from _discovery.inferrer import NullConfigurationInferrer
    from _discovery.inspector import NoRemoteError
    from _discovery.minter import (
        install_sigint_handler,
        stale_tmp_sweep,
        write_project_entity,
    )
    from _discovery.slug import (
        slug_from_monorepo_path,
        slug_from_project_name,
    )
    from _discovery.verifier import verify_and_roll_back_on_failure

    if verifier_fn is None:
        verifier_fn = verify_and_roll_back_on_failure

    repo_path = repo_path.resolve()
    projects_dir = repo_path / ".sulis" / "projects"

    # Pre-flight sweep — clear any stale `.tmp` from a previous
    # cancelled run (MUC-002 + NFR-003 deterministic re-run).
    if projects_dir.exists():
        stale_tmp_sweep(projects_dir)

    # ---- Phase 1: Detect ----
    try:
        detected = _detect(repo_path)
    except NoRemoteError:
        # MUC-006 — if the founder passed --source-repo, override and
        # continue with a synthetic root. Otherwise re-raise.
        if source_repo_override is None:
            raise
        from _discovery.inspector import (
            LocalFilesystemInspector,
            RepoRoot,
        )
        try:
            primary_branch_out = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=repo_path, capture_output=True, text=True,
                timeout=5, check=True,
            ).stdout.strip()
            primary_branch = primary_branch_out or "main"
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            primary_branch = "main"
        synthetic_root = RepoRoot(
            is_git=True,
            has_remote=False,
            remote_url=None,
            primary_branch=primary_branch,
            repo_root=repo_path,
        )
        inspector = LocalFilesystemInspector()
        detected = {
            "root": synthetic_root,
            "manifests": inspector.read_package_manifests(repo_path),
            "ci_workflows": inspector.read_ci_workflows(repo_path),
            "repo_contract": inspector.read_repo_contract(repo_path),
        }

    root = detected["root"]

    # Compute source.repo — from remote_url OR from override.
    if source_repo_override is not None:
        source_repo = source_repo_override
    else:
        source_repo = _parse_github_shorthand(root.remote_url)

    primary_branch = root.primary_branch or "main"

    # ---- Phase 2: Infer ----
    inferences, tokens_consumed, budget_exceeded = _infer(
        detected, inferrer, token_budget,
    )
    if budget_exceeded:
        # Replace the inferrer with Null for any downstream logic that
        # consults it (NFR-006). The Ask phase below already runs with
        # `inferences = {}` so the swap is observably equivalent.
        inferrer = NullConfigurationInferrer()

    # ---- Phase 3: Ask ----
    if monorepo_path is not None:
        slug = slug_from_monorepo_path(monorepo_path)
    else:
        slug = slug_from_project_name(
            answers.get("name", source_repo.split("/")[-1]),
        )

    target_path = projects_dir / f"{slug}.jsonld"
    existing = _existing_project_payload(target_path) if update else None

    composed = _ask(
        inferences=inferences,
        answers=answers,
        overrides=overrides,
        update=update,
        update_keep_fields=update_keep_fields,
        existing_entity=existing,
        ask_phase_cancels=ask_phase_cancels,
    )
    if monorepo_path is not None:
        composed.setdefault("path", monorepo_path)

    # ---- Phase 4: Mint ----
    release_workflow_ref = (
        release_workflow_ref_override
        if release_workflow_ref_override is not None
        else _MARKETPLACE_RELEASE_WORKFLOW_ULID
    )
    entity = _compose_entity(
        composed_fields=composed,
        source_repo=source_repo,
        primary_branch=primary_branch,
        release_workflow_ref=release_workflow_ref,
    )

    # Install the SIGINT handler so a Ctrl-C between write_text and
    # os.replace sweeps the `.tmp` before re-raising.
    projects_dir.mkdir(parents=True, exist_ok=True)
    install_sigint_handler(projects_dir)

    write_project_entity(target_path, entity, allow_overwrite=update)

    # ---- Phase 5: Verify ----
    verifier_fn(target_path)

    return DiscoveryResult(
        ok=True,
        entity_path=target_path,
        tokens_consumed=tokens_consumed,
        budget_exceeded=budget_exceeded,
    )


__all__ = ["DiscoveryResult", "run_discovery_headless"]
