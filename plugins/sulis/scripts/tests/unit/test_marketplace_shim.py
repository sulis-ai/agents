"""Structural assertion: the marketplace's own release-on-merge workflow is
now a thin shim that calls the plugin's reusable workflow (the n=1 dogfood).

WP-005 (SUBSTITUTE-Replace) turns the marketplace's ~280-line
`.github/workflows/release-on-merge.yml` into a thin shim. Unlike the
canonical *consumer* shim template
(`plugins/sulis/templates/shims/release-on-merge.yml`), which pins a
cross-repo reference at a SemVer tag
(`uses: sulis-ai/agents/.../release-on-merge.yml@sulis-vN.M.K`), the
marketplace's OWN shim uses a **local path reference**:

    uses: ./plugins/sulis/templates/workflows/release-on-merge.yml

Reason (TDD §4.2 comp-marketplace-shim; §6.5 n=1 dogfood): the
marketplace is the repo that OWNS the reusable workflow. A local-path
`uses:` reference always tracks the current commit's copy of the
workflow — there is no version-pin lag for the owning repo, and no tag
that must pre-exist before the shim is valid. Consumers pin a tag; the
owner references locally. The header comment in the shim documents this
distinction.

Load-bearing invariant — the LOOP-GUARD must survive the
shim -> reusable indirection. The original 280-line workflow carried a
job-level `if:` that SKIPS the bot's own `release: sulis` commits
(matched on author = github-actions[bot]) so the release push-back does
not re-trigger an infinite release loop. When the workflow becomes a
shim calling the reusable workflow, the guard lives in the reusable
workflow's job-level `if:`. GitHub Actions propagates the triggering
`push` event's context (`github.event.head_commit.*`, `github.actor`)
into a workflow called via `workflow_call`, so the guard still fires.
These tests assert the guard is preserved — either at the shim level OR
in the reusable workflow the shim calls (one MUST hold).

CI YAML is not unit-testable the way Python is, so this is a structural
assertion over the workflow text (parsed with PyYAML where safe; read as
raw text for the `on:`/trigger check, which PyYAML 1.1 normalises to the
boolean key `True` — the "Norway problem").

Stdlib + pyyaml + pytest, Python 3.11-safe.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

# tests/unit/ -> tests/ -> scripts/ -> sulis/ -> plugins/ -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[5]
_SHIM = _REPO_ROOT / ".github" / "workflows" / "release-on-merge.yml"
# The reusable workflow the shim is expected to call (local path).
_REUSABLE = (
    _REPO_ROOT
    / "plugins"
    / "sulis"
    / "templates"
    / "workflows"
    / "release-on-merge.yml"
)

# The local-path `uses:` reference the marketplace shim must carry. NOT the
# cross-repo `sulis-ai/agents/...@sulis-vN.M.K` form (that is the *consumer*
# template's shape) — the owning repo references its workflow locally.
_LOCAL_USES = "./plugins/sulis/templates/workflows/release-on-merge.yml"

# The loop-guard's distinguishing token. The guard skips the bot's own
# release commits by matching the commit author / actor against the bot
# login. Either spelling of the bot login is acceptable evidence the
# guard is present.
_BOT_LOGIN = "github-actions[bot]"

# A shim is thin. The thinness signal is the count of EXECUTABLE
# (non-comment, non-blank) YAML lines — NOT total lines, because the
# header comment legitimately documents the local-ref-vs-tag distinction,
# the n=1 dogfood framing, and the loop-guard-survives-indirection
# invariant (all required by the WP's Definition of Done). The original
# workflow had 200+ executable lines; the shim has ~12. A ceiling of 20
# executable lines catches a regression to the full body while tolerating
# the documentation header.
_MAX_SHIM_EXEC_LINES = 20


def _executable_lines(text: str) -> list[str]:
    """Lines that are neither blank nor pure-comment — the YAML that runs."""
    out = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        out.append(raw)
    return out


def _load_shim() -> dict:
    """Parse the marketplace shim. Reused by the structural assertions."""
    return yaml.safe_load(_SHIM.read_text(encoding="utf-8"))


def _shim_text() -> str:
    return _SHIM.read_text(encoding="utf-8")


def test_shim_file_exists():
    """Guard: the marketplace workflow resolves to a real file."""
    assert _SHIM.is_file(), f"missing workflow {_SHIM}"


def test_yaml_parses():
    """The shim is valid YAML and parses to a mapping with a jobs block.

    This is the structural smoke check — if Green breaks the file, every
    other assertion's parse fails here first with a clear message.
    """
    doc = _load_shim()
    assert isinstance(doc, dict), "release-on-merge.yml did not parse to a mapping"
    assert "jobs" in doc, "release-on-merge.yml missing top-level 'jobs' key"


def test_shim_is_thin():
    """The file is now a shim, not the 280-line workflow.

    An executable-line ceiling is the cheapest regression guard: if a
    future edit accidentally restores the full workflow body inline
    (instead of calling the reusable workflow), this fails immediately.
    Comment lines are excluded so the required documentation header does
    not count against the budget.
    """
    exec_lines = _executable_lines(_shim_text())
    assert len(exec_lines) <= _MAX_SHIM_EXEC_LINES, (
        f"shim has {len(exec_lines)} executable lines "
        f"(> {_MAX_SHIM_EXEC_LINES}); a thin shim should call the reusable "
        "workflow, not inline the full body"
    )
    # Positive evidence it is genuinely a caller: the bump/tag step bodies
    # of the original workflow must NOT be present.
    text = _shim_text()
    assert "Apply the version bump" not in text, (
        "shim still contains the inline bump step — it must delegate to "
        "the reusable workflow instead"
    )


def test_uses_local_reusable_workflow_path():
    """The single job calls the reusable workflow via the LOCAL path ref.

    The marketplace owns the reusable workflow, so it references it by
    local path (always tracks the current commit) — NOT the cross-repo
    `sulis-ai/agents/...@sulis-vN.M.K` tag form used by external consumer
    shims.
    """
    doc = _load_shim()
    jobs = doc.get("jobs", {})
    assert jobs, "shim declares no jobs"
    uses_values = [
        job.get("uses", "")
        for job in jobs.values()
        if isinstance(job, dict)
    ]
    assert any(u == _LOCAL_USES for u in uses_values), (
        f"no job has `uses: {_LOCAL_USES}`; job uses values: {uses_values}"
    )
    # Negative: the cross-repo @tag consumer form must NOT be used here.
    text = _shim_text()
    assert "sulis-ai/agents/plugins/sulis/templates/workflows" not in text, (
        "marketplace shim uses the cross-repo @tag consumer form; the "
        "owning repo must use the local path ref instead"
    )


def test_trigger_is_push_main():
    """Trigger preserved exactly: on: push: branches: [main].

    PyYAML 1.1 normalises the bare `on` key to the boolean True (the
    Norway problem), so the parsed-doc lookup keys on both `True` and
    `"on"` defensively; a raw-text assertion backs it up.
    """
    doc = _load_shim()
    on_block = doc.get(True, doc.get("on"))
    assert isinstance(on_block, dict), (
        f"`on:` block missing or not a mapping; got {on_block!r}"
    )
    push = on_block.get("push")
    assert isinstance(push, dict), f"`on.push` missing; got {push!r}"
    branches = push.get("branches")
    assert branches == ["main"], (
        f"trigger must be `push: branches: [main]`; got branches={branches!r}"
    )
    # Raw-text backstop — the exact trigger shape survives any parser quirk.
    text = _shim_text()
    assert re.search(r"push:\s*\n\s*branches:\s*\[main\]", text), (
        "raw `on: push: branches: [main]` trigger shape not found in shim text"
    )


def test_secrets_inherit_present():
    """The job forwards caller secrets to the reusable workflow.

    `secrets: inherit` is required so the reusable workflow can use
    GITHUB_TOKEN for the bump push, tag push, and back-merge PR ops.
    """
    doc = _load_shim()
    jobs = doc.get("jobs", {})
    inherits = [
        job.get("secrets")
        for job in jobs.values()
        if isinstance(job, dict)
    ]
    assert any(s == "inherit" for s in inherits), (
        f"no job declares `secrets: inherit`; got secrets values: {inherits}"
    )


def test_loop_guard_preserved():
    """The loop-guard survives the shim -> reusable indirection.

    The guard SKIPS the bot's own `release: sulis` commits (matched on
    author/actor == github-actions[bot]) so the release push-back does
    not re-trigger an infinite release loop. After the Replace, the guard
    lives in the reusable workflow the shim calls (GitHub propagates the
    push event's `github.event.head_commit.*` / `github.actor` context
    into a `workflow_call`-invoked reusable workflow, so a job-level `if:`
    there still fires).

    This test is deliberately tolerant of WHERE the guard lives: it
    passes if the guard token appears in a job-level `if:` of EITHER the
    shim itself OR the reusable workflow the shim references by local
    path. One MUST hold — a broken loop-guard means infinite release
    commits, which is the single most load-bearing risk in this WP.
    """
    guard_in_shim = _BOT_LOGIN in _shim_text()

    assert _REUSABLE.is_file(), (
        f"reusable workflow not found at {_REUSABLE}; the shim's local "
        "`uses:` path must resolve to a real file"
    )
    reusable_doc = yaml.safe_load(_REUSABLE.read_text(encoding="utf-8"))
    reusable_jobs = reusable_doc.get("jobs", {})
    guard_in_reusable = any(
        _BOT_LOGIN in str(job.get("if", ""))
        for job in reusable_jobs.values()
        if isinstance(job, dict)
    )

    assert guard_in_shim or guard_in_reusable, (
        "loop-guard not found: neither the shim nor the reusable workflow "
        f"it calls carries a job-level `if:` matching {_BOT_LOGIN!r}. "
        "Without the guard the release push-back re-triggers the workflow "
        "in an infinite loop."
    )


def test_shim_references_resolvable_reusable_workflow():
    """The local `uses:` path resolves to a file that exists in the tree.

    A dangling local reference would make the workflow invalid at run
    time. Because the shim references the reusable workflow by local
    path, the target must physically exist in the same checkout.
    """
    assert _REUSABLE.is_file(), (
        f"shim references {_LOCAL_USES} but {_REUSABLE} does not exist"
    )
