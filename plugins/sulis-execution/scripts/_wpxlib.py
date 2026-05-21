"""Shared helpers for the wpx-* CLI tools.

Stdlib only. Provides:
- Path resolution for project-relative artifacts.
- Markdown frontmatter parsing (tiny, no pyyaml dependency).
- JSON output helpers (consistent shape).
- Markdown table parsing/writing (for journal + INDEX manipulation).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────
# Path resolution
# ─────────────────────────────────────────────────────────────────────────


@dataclass
class WpxPaths:
    """Project-relative paths for executor artifacts."""

    repo_root: Path
    project: str

    @property
    def arch_root(self) -> Path:
        return self.repo_root / ".architecture" / self.project

    @property
    def wp_dir(self) -> Path:
        return self.arch_root / "work-packages"

    @property
    def index_md(self) -> Path:
        return self.wp_dir / "INDEX.md"

    @property
    def security_dir(self) -> Path:
        return self.repo_root / ".security" / self.project

    @property
    def findings_dir(self) -> Path:
        return self.security_dir / "findings"

    @property
    def findings_register(self) -> Path:
        return self.security_dir / "findings-register.md"

    def journal(self, wp: str) -> Path:
        return self.wp_dir / f".executor-{wp}.md"

    @property
    def train_overrides(self) -> Path:
        return self.arch_root / "train-overrides.yaml"

    @property
    def train_runs_dir(self) -> Path:
        return self.arch_root / "train-runs"

    def blocker(self, wp: str) -> Path:
        return self.wp_dir / f"BLOCKER-{wp}.md"

    def wp_file(self, wp: str) -> Path:
        # Look for WP-NNN-*.md (the file's name includes a slug)
        matches = list(self.wp_dir.glob(f"{wp}-*.md"))
        # Filter out journal/blocker/auto-draft files
        matches = [
            m for m in matches
            if not m.name.startswith(".")
            and not m.name.startswith("BLOCKER-")
        ]
        if not matches:
            raise FileNotFoundError(
                f"No WP file matching {wp}-*.md in {self.wp_dir}"
            )
        if len(matches) > 1:
            raise ValueError(
                f"Multiple WP files match {wp}-*.md: {matches}"
            )
        return matches[0]


def add_common_args(parser: argparse.ArgumentParser) -> None:
    """Add --project and --repo-root to a parser."""
    parser.add_argument(
        "--project",
        required=True,
        help="Project slug (used to resolve .architecture/<project>/ paths)",
    )
    parser.add_argument(
        "--repo-root",
        default=os.getcwd(),
        help="Repo root directory (defaults to cwd)",
    )


def paths_from_args(args: argparse.Namespace) -> WpxPaths:
    return WpxPaths(repo_root=Path(args.repo_root).resolve(), project=args.project)


# ─────────────────────────────────────────────────────────────────────────
# JSON output
# ─────────────────────────────────────────────────────────────────────────


def emit_ok(
    data: dict | None = None,
    warnings: list[str] | None = None,
    exit_code: int = 0,
) -> None:
    """Print success JSON to stdout and exit with the given code (default 0).

    The `exit_code` parameter exists for tools that emit a
    structured-JSON result alongside a non-zero exit semantic.
    Concrete use case: `wpx-pipeline` emits a fully-formed result
    object with `outcome="blocker"` and `exit_code=1` so the calling
    session's `Bash(run_in_background)` notification can distinguish
    a clean pipeline-blocker (exit 1, structured JSON readable from
    the stdout file) from a successful pipeline (exit 0) or an
    internal-error crash (exit 2 via emit_internal_error).

    For normal success in every other wpx-* tool, the default
    exit_code=0 preserves the prior contract.
    """
    payload = {"ok": True}
    if data is not None:
        payload["data"] = data
    if warnings:
        payload["warnings"] = warnings
    print(json.dumps(payload, indent=2, sort_keys=True))
    sys.exit(exit_code)


def emit_error(message: str, context: dict | None = None) -> None:
    """Print error JSON to stdout, error to stderr, exit 1 (expected failure)."""
    payload = {"ok": False, "error": message}
    if context is not None:
        payload["context"] = context
    print(json.dumps(payload, indent=2, sort_keys=True))
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def emit_internal_error(exc: BaseException) -> None:
    """Print traceback to stderr, exit 2 (bug)."""
    traceback.print_exception(type(exc), exc, exc.__traceback__, file=sys.stderr)
    sys.exit(2)


def cli_main(parser: argparse.ArgumentParser, handlers: dict) -> None:
    """Run a CLI tool with subcommand dispatch."""
    args = parser.parse_args()
    handler = handlers.get(args.subcommand)
    if handler is None:
        emit_error(f"Unknown subcommand: {args.subcommand}")
    try:
        handler(args)
    except FileNotFoundError as e:
        emit_error(str(e))
    except ValueError as e:
        emit_error(str(e))
    except SystemExit:
        raise
    except BaseException as e:  # noqa: BLE001
        emit_internal_error(e)


# ─────────────────────────────────────────────────────────────────────────
# Markdown frontmatter (YAML-like, tiny inline parser)
# ─────────────────────────────────────────────────────────────────────────


_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def parse_frontmatter(text: str) -> tuple[dict[str, str | list[str]], str]:
    """Parse a Markdown file's YAML-like frontmatter.

    Supports:
      key: value          (scalar)
      key:                (start of list)
        - item1
        - item2
      key: [a, b, c]      (inline list)

    Returns (frontmatter_dict, body_after_frontmatter).
    """
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    fm_text = match.group(1)
    body = text[match.end():]
    fm: dict[str, str | list[str]] = {}
    current_list_key: str | None = None
    for raw_line in fm_text.splitlines():
        line = raw_line.rstrip()
        if not line or line.startswith("#"):
            continue
        if current_list_key is not None and line.startswith("  - "):
            # Continue list
            item = line[4:].strip().strip("'\"")
            assert isinstance(fm[current_list_key], list)
            fm[current_list_key].append(item)  # type: ignore[union-attr]
            continue
        # New key
        current_list_key = None
        if ":" not in line:
            continue
        key, _, rest = line.partition(":")
        key = key.strip()
        rest = rest.strip()
        if rest == "":
            # Start of a list
            fm[key] = []
            current_list_key = key
        elif rest.startswith("[") and rest.endswith("]"):
            # Inline list
            inner = rest[1:-1]
            items = [i.strip().strip("'\"") for i in inner.split(",") if i.strip()]
            fm[key] = items
        else:
            # Scalar
            value = rest.strip("'\"")
            fm[key] = value
    return fm, body


def read_frontmatter(path: Path) -> dict[str, str | list[str]]:
    text = path.read_text(encoding="utf-8")
    fm, _ = parse_frontmatter(text)
    return fm


# ─────────────────────────────────────────────────────────────────────────
# Markdown table helpers
# ─────────────────────────────────────────────────────────────────────────


@dataclass
class MdTable:
    """Lightweight Markdown table representation."""

    headers: list[str] = field(default_factory=list)
    alignments: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)

    def render(self) -> str:
        lines = []
        lines.append("| " + " | ".join(self.headers) + " |")
        lines.append("|" + "|".join(self.alignments or ["---"] * len(self.headers)) + "|")
        for row in self.rows:
            # Pad / truncate to headers length
            padded = list(row) + [""] * (len(self.headers) - len(row))
            padded = padded[: len(self.headers)]
            lines.append("| " + " | ".join(padded) + " |")
        return "\n".join(lines)


def parse_md_table(table_text: str) -> MdTable:
    """Parse a Markdown table block (starting with | header |)."""
    lines = [ln for ln in table_text.strip().splitlines() if ln.strip()]
    if len(lines) < 2:
        return MdTable()
    headers = [c.strip() for c in lines[0].strip("|").split("|")]
    alignments = [c.strip() for c in lines[1].strip("|").split("|")]
    rows = []
    for line in lines[2:]:
        if not line.startswith("|"):
            break
        cells = [c.strip() for c in line.strip("|").split("|")]
        rows.append(cells)
    return MdTable(headers=headers, alignments=alignments, rows=rows)


def find_section(text: str, heading: str) -> tuple[int, int]:
    """Find the byte range of a Markdown section by heading.

    Returns (start, end) where start is the first char of the section's
    heading line and end is one past the last char before the next heading
    of equal-or-higher level (or EOF).

    Raises ValueError if the heading is not found.
    """
    # Match "## Heading" or "# Heading" — derive level from input
    level = 0
    for ch in heading:
        if ch == "#":
            level += 1
        else:
            break
    title = heading[level:].strip()
    pattern = re.compile(
        rf"^(#{{{level}}}) {re.escape(title)}\s*$",
        re.MULTILINE,
    )
    match = pattern.search(text)
    if not match:
        raise ValueError(f"Section not found: {heading}")
    start = match.start()
    # Find next heading of equal or higher level
    next_pattern = re.compile(
        rf"^#{{1,{level}}} \S",
        re.MULTILINE,
    )
    next_match = next_pattern.search(text, pos=match.end())
    end = next_match.start() if next_match else len(text)
    return start, end


def replace_section(text: str, heading: str, new_content: str) -> str:
    """Replace a section's content (everything after the heading line, up to next heading).

    new_content should NOT include the heading itself.
    """
    start, end = find_section(text, heading)
    # Find end of heading line
    nl = text.index("\n", start) + 1
    return text[:nl] + new_content + (text[end:] if end < len(text) else "")


# ─────────────────────────────────────────────────────────────────────────
# Pipeline helpers (shell, gh API, CI poll, rebase, merge, deploy, health, smoke)
# ─────────────────────────────────────────────────────────────────────────
#
# Shared between wpx-pipeline (per-WP path) and wpx-train (per-batch path).
# Both CLIs import these so the gh / git / polling primitives stay in
# one place. The CLI scripts themselves contain only state-machine logic
# specific to their dispatch shape.
#


# --- Constants -----------------------------------------------------------

CI_DEFAULT_INTERVAL = 300     # 5 min
CI_DEFAULT_CAP = 45 * 60      # 45 min

DEPLOY_DEFAULT_INTERVAL = 300  # 5 min
DEPLOY_DEFAULT_CAP = 30 * 60   # 30 min

HEALTH_MIN_INTERVAL = 60       # 1 min initial
HEALTH_MAX_INTERVAL = 300      # 5 min cap (exponential backoff)
HEALTH_DEFAULT_CAP = 10 * 60   # 10 min total

REBASE_BUDGET = 2              # GIT-05 step-4

# Conventional Commits branch prefixes that branch-CI workflows
# typically gate on. Used by _has_branch_ci_trigger to decide whether
# a `branches:` list item in a workflow YAML targets feature branches.
_BRANCH_CI_PREFIXES = (
    "feat/", "fix/", "chore/", "refactor/", "docs/",
    "test/", "perf/", "build/", "ci/", "style/", "revert/",
)

_URL_RE = re.compile(r"https?://[^\s'\"`]+")


# --- Branch-CI detection -------------------------------------------------

def _matches_cc_prefix(value: str) -> bool:
    """True if a `branches:` list entry targets a Conventional Commits
    feature prefix (feat/**, fix/*, chore/foo, etc.).
    """
    v = value.strip().strip("'\"")
    return any(v.startswith(p) for p in _BRANCH_CI_PREFIXES)


def _has_branch_ci_trigger(text: str) -> bool:
    """Inspect a GitHub Actions workflow YAML for a real branch-CI trigger.

    Looks specifically for `branches:` declarations under `on.push` or
    `on.pull_request`, and checks whether ANY listed branch glob matches
    a Conventional Commits prefix. Rejects `branches-ignore:`, `paths:`,
    `paths-ignore:`, `tags:`, comments, and any other location where a
    substring like `docs/` might legitimately appear without indicating
    branch CI.

    The v0.10.5 version used a naked substring grep, which produced
    false positives on workflows like:

        on:
          push:
            branches: [dev]
            paths-ignore:
              - 'docs/**'        # ← `docs/` matched the substring grep

    Now we walk the YAML line-by-line. When we hit a `branches:` line,
    we either:
      - parse the inline list (`branches: ['feat/**', 'main']`), or
      - scan the following lines at deeper indent for `- 'feat/**'`
        style list items.

    `branches-ignore:` is explicitly excluded (an "ignore" list means
    the workflow does NOT run on those branches — opposite of branch CI).

    Returns True iff at least one workflow has a `branches:` (under
    `on.push` or `on.pull_request`) listing a Conventional Commits
    prefix glob.
    """
    lines = text.splitlines()
    n = len(lines)
    i = 0
    while i < n:
        line = lines[i]
        # Match `<indent>branches:` (NOT branches-ignore, paths, tags)
        m = re.match(r"^(\s*)branches\s*:\s*(.*?)\s*$", line)
        # Skip `branches-ignore:` / commented lines
        if not m or line.lstrip().startswith("#"):
            i += 1
            continue
        indent = m.group(1)
        rest = m.group(2).rstrip()

        # Inline list: `branches: ['feat/**', 'main']` or `branches: [feat/**]`
        if rest.startswith("[") and rest.endswith("]"):
            inner = rest[1:-1]
            items = [it.strip() for it in inner.split(",") if it.strip()]
            if any(_matches_cc_prefix(it) for it in items):
                return True
            i += 1
            continue

        # Single inline value: `branches: feat/**`
        if rest and not rest.startswith("#"):
            if _matches_cc_prefix(rest):
                return True
            i += 1
            continue

        # Block list: scan following indented lines for list items
        j = i + 1
        base_indent = len(indent)
        while j < n:
            nl = lines[j]
            if not nl.strip():
                j += 1
                continue
            nl_indent = len(nl) - len(nl.lstrip())
            if nl_indent <= base_indent:
                break  # dedented out of the list
            # Match `<indent>- '<value>'` or `<indent>- <value>`
            lm = re.match(r"^\s*-\s*(.+?)\s*$", nl)
            if lm and _matches_cc_prefix(lm.group(1)):
                return True
            j += 1
        i = j

    return False


def _detect_branch_ci(worktree: Path) -> bool:
    """Detect whether the project has branch CI configured.

    For GitHub Actions: inspects `.github/workflows/*.y[a]ml` for
    structural `branches:` declarations under `on.push` /
    `on.pull_request` (NOT `branches-ignore`, `paths`, `paths-ignore`).
    Returns True iff at least one such declaration lists a Conventional
    Commits prefix glob (`feat/**`, `fix/**`, etc.).

    For GitLab CI: falls back to a coarser substring grep on
    `.gitlab-ci.yml` since GitLab's rule syntax varies. May produce
    false positives on GitLab; refine when needed.

    Used by wpx-pipeline / wpx-train to decide whether to skip CI
    polling (no branch CI → poll would hang waiting for check-runs
    that never appear).
    """
    gh = worktree / ".github" / "workflows"
    if gh.exists() and gh.is_dir():
        for yml in list(gh.glob("*.yml")) + list(gh.glob("*.yaml")):
            try:
                text = yml.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if _has_branch_ci_trigger(text):
                return True
    gitlab = worktree / ".gitlab-ci.yml"
    if gitlab.exists() and gitlab.is_file():
        try:
            text = gitlab.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            text = ""
        # GitLab fallback: coarser check; refine with proper rule parsing
        # if GitLab false-positives become a problem.
        if any(p in text for p in _BRANCH_CI_PREFIXES):
            return True
    return False


# --- Logging + shell -----------------------------------------------------

def _log(msg: str) -> None:
    """Progress log to stderr so the calling session can tail it if desired."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{ts}] {msg}", file=sys.stderr, flush=True)


def _run(cmd: list[str], cwd: Path | None = None,
         timeout: int = 60) -> tuple[int, str, str]:
    """Run a shell command; return (rc, stdout, stderr). 124 on timeout."""
    try:
        proc = subprocess.run(  # noqa: S603
            cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"Timeout after {timeout}s"


# --- gh API helpers ------------------------------------------------------

def _gh_check_runs(repo: str, branch: str) -> dict:
    """Return list of latest check-runs for the branch's HEAD commit."""
    rc, out, err = _run(
        ["gh", "api", f"repos/{repo}/commits/{branch}/check-runs",
         "--paginate"],
        timeout=30,
    )
    if rc != 0:
        raise RuntimeError(f"gh check-runs failed: {err}")
    return json.loads(out) if out.strip() else {"check_runs": []}


def _gh_branch_sha(repo: str, branch: str) -> str:
    rc, out, err = _run(
        ["gh", "api", f"repos/{repo}/git/refs/heads/{branch}"], timeout=30,
    )
    if rc != 0:
        raise RuntimeError(f"gh branch-sha failed for {branch}: {err}")
    return json.loads(out)["object"]["sha"]


def _gh_ref_sha(repo: str, ref: str) -> str:
    """Get SHA for any ref (e.g., dev)."""
    rc, out, err = _run(
        ["gh", "api", f"repos/{repo}/git/refs/heads/{ref}"], timeout=30,
    )
    if rc != 0:
        raise RuntimeError(f"gh ref-sha failed for {ref}: {err}")
    return json.loads(out)["object"]["sha"]


def _gh_branch_already_merged(repo: str, branch: str, base: str = "dev") -> tuple[bool, str]:
    """Check whether `branch` is already fully merged into `base`.

    Uses GitHub's compare API: `gh api repos/{repo}/compare/{base}...{branch}`
    which returns a `status` field with one of:

      - `"identical"` — branch HEAD == base HEAD; already merged (squash or ff)
      - `"behind"`   — base has commits beyond branch; branch has no commits to merge
      - `"ahead"`    — branch has commits beyond base; needs merge (normal case)
      - `"diverged"` — both have unique commits; needs rebase before merge

    Returns (already_merged, base_sha). When already_merged, the caller
    should skip _gh_merge and proceed using base_sha as the merge SHA
    (no new commit is needed; the work is already on dev).

    Returns (False, "") for `ahead` / `diverged` / errors — the caller
    should proceed with the normal merge path.

    v0.10.5 — fixes the pre-existing bug where re-running wpx-pipeline
    on an already-merged branch would crash with RuntimeError from
    _gh_merge (POST /merges returns 409 when base already contains head).
    """
    rc, out, err = _run(
        ["gh", "api", f"repos/{repo}/compare/{base}...{branch}"],
        timeout=30,
    )
    if rc != 0:
        _log(f"compare API failed (rc={rc}); falling through to normal merge path. err: {err}")
        return False, ""
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        _log(f"compare API returned non-JSON; falling through. out: {out!r}")
        return False, ""
    status = data.get("status", "")
    if status in ("identical", "behind"):
        # Already merged. Fetch the current base HEAD as the merge SHA.
        try:
            base_sha = _gh_ref_sha(repo, base)
        except RuntimeError:
            base_sha = ""
        return True, base_sha
    return False, ""


def _gh_merge(repo: str, base: str, head: str, commit_message: str) -> str:
    """Squash-merge head into base via the merges endpoint. Returns merge SHA."""
    rc, out, err = _run(
        ["gh", "api", "-X", "POST", f"repos/{repo}/merges",
         "-f", f"base={base}", "-f", f"head={head}",
         "-f", f"commit_message={commit_message}",
         "-F", "merge_method=squash"],
        timeout=60,
    )
    if rc != 0:
        # Some hosts use PUTs against /pulls/N/merge. The /merges endpoint
        # returns 409 if no PR is required; fall back gracefully.
        raise RuntimeError(f"gh merges failed: {err}\nstdout={out}")
    return json.loads(out)["sha"]


def _gh_deploy_runs(repo: str, workflow: str, commit: str) -> list[dict]:
    rc, out, err = _run(
        ["gh", "run", "list", "--workflow", workflow, "--commit", commit,
         "--json", "databaseId,status,conclusion,createdAt,url",
         "--limit", "5"],
        timeout=30,
    )
    if rc != 0:
        raise RuntimeError(f"gh run list failed: {err}")
    return json.loads(out) if out.strip() else []


# --- Phase implementations ----------------------------------------------

def _poll_ci(repo: str, branch: str, interval: int, cap: int) -> str:
    """Poll CI on branch HEAD; return verdict 'green'|'failed'|'timeout'."""
    elapsed = 0
    last_status = "unknown"
    while elapsed < cap:
        runs = _gh_check_runs(repo, branch)["check_runs"]
        if not runs:
            _log(f"CI poll: no check-runs yet for {branch} (elapsed {elapsed}s)")
        else:
            statuses = [(r["name"], r["status"], r["conclusion"]) for r in runs]
            all_done = all(s[1] == "completed" for s in statuses)
            if all_done:
                if all(s[2] == "success" or s[2] == "neutral"
                       or s[2] == "skipped" for s in statuses):
                    _log(f"CI poll: all checks green ({len(statuses)} runs)")
                    return "green"
                failed = [s for s in statuses if s[2] not in
                          ("success", "neutral", "skipped")]
                _log(f"CI poll: failed checks: {failed}")
                return "failed"
            in_flight = [s[0] for s in statuses if s[1] != "completed"]
            last_status = f"in_flight={in_flight}"
            _log(f"CI poll: {last_status} (elapsed {elapsed}s)")
        time.sleep(interval)
        elapsed += interval
    _log(f"CI poll: TIMEOUT after {cap}s; last status: {last_status}")
    return "timeout"


def _rebase_on_dev(repo: str, branch: str, worktree: Path,
                   dev_sha_at_creation: str,
                   base_branch: str = "dev") -> tuple[bool, str]:
    """If base_branch advanced past dev_sha_at_creation, rebase. Return (rebased, new_sha).

    `base_branch` parameterises the rebase target — defaults to "dev" for
    backward compatibility, but per CW-04 the executor inside a change
    worktree passes the change branch name here so the rebase target is
    the change branch's HEAD, not origin/dev.
    """
    current_base = _gh_ref_sha(repo, base_branch)
    if current_base == dev_sha_at_creation:
        return False, ""
    _log(f"{base_branch} advanced from {dev_sha_at_creation[:8]} to {current_base[:8]}; rebasing")
    rc, _, err = _run(["git", "fetch", "origin", base_branch], cwd=worktree)
    if rc != 0:
        raise RuntimeError(f"git fetch failed: {err}")
    rc, _, err = _run(["git", "rebase", f"origin/{base_branch}"], cwd=worktree)
    if rc != 0:
        _run(["git", "rebase", "--abort"], cwd=worktree)
        raise RuntimeError(f"git rebase failed: {err}")
    rc, _, err = _run(
        ["git", "push", "--force-with-lease", "origin", branch],
        cwd=worktree,
    )
    if rc != 0:
        raise RuntimeError(f"git push --force-with-lease failed: {err}")
    rc, out, _ = _run(["git", "rev-parse", "HEAD"], cwd=worktree)
    return True, out.strip()


def _merge_squash(repo: str, branch: str, wp: str,
                  base_branch: str = "dev") -> str:
    """Squash-merge branch into base_branch. Return merge SHA on base_branch.

    `base_branch` defaults to "dev" for backward compatibility, but per
    CW-04 the executor inside a change worktree passes the change branch
    name here so the merge target is the change branch, not dev.
    """
    msg = f"feat({wp.lower()}): squash-merge from {branch}"
    sha = _gh_merge(repo, base=base_branch, head=branch, commit_message=msg)
    # Delete remote branch
    _run(["gh", "api", "-X", "DELETE", f"repos/{repo}/git/refs/heads/{branch}"],
         timeout=30)
    return sha


def _poll_deploy(repo: str, workflow: str, merge_sha: str,
                 interval: int, cap: int) -> tuple[str, str]:
    """Poll deploy workflow for merge_sha. Return (verdict, deploy_url)."""
    elapsed = 0
    while elapsed < cap:
        runs = _gh_deploy_runs(repo, workflow, merge_sha)
        if runs:
            r = runs[0]
            url = r.get("url", "")
            status = r.get("status")
            conclusion = r.get("conclusion")
            _log(f"Deploy poll: status={status} conclusion={conclusion} (elapsed {elapsed}s)")
            if status == "completed":
                if conclusion == "success":
                    return "green", url
                return f"failed({conclusion})", url
        else:
            _log(f"Deploy poll: no run yet for {merge_sha[:8]} (elapsed {elapsed}s)")
        time.sleep(interval)
        elapsed += interval
    _log(f"Deploy poll: TIMEOUT after {cap}s")
    return "timeout", ""


# --- Health path resolution ---------------------------------------------

def _extract_health_path_from_smoke(smoke_cmd: str) -> str:
    """Return the path component of the first URL in the smoke command.

    Used to auto-detect the health endpoint when the project's
    smoke_test already encodes the right path
    (e.g. `curl -sf https://staging.example.com/health`).

    Returns "" if no URL is found, or "/" if the URL has no path
    beyond the root.

    v0.10.7 — added to fix Step 10a hitting bare staging URL for APIs
    whose root returns 404 (e.g. APIs that only serve health at /health).
    """
    if not smoke_cmd:
        return ""
    # urlparse imported lazily to keep top-of-file imports tight
    from urllib.parse import urlparse

    match = _URL_RE.search(smoke_cmd)
    if not match:
        return ""
    parsed = urlparse(match.group(0))
    return parsed.path or ""


def _join_health_url(base: str, path: str) -> str:
    """Join staging URL + health path; tolerate trailing slashes.

    Examples:
        _join_health_url("https://x.com",  "/health") → "https://x.com/health"
        _join_health_url("https://x.com/", "/health") → "https://x.com/health"
        _join_health_url("https://x.com",  "health")  → "https://x.com/health"
        _join_health_url("https://x.com/", "")        → "https://x.com/"
    """
    if not path:
        return base.rstrip("/") + "/"
    return base.rstrip("/") + ("" if path.startswith("/") else "/") + path


def _poll_health(url: str, cap: int) -> str:
    """Poll health endpoint with exponential backoff (1m → 5m, capped at cap)."""
    elapsed = 0
    interval = HEALTH_MIN_INTERVAL
    while elapsed < cap:
        rc, out, err = _run(
            ["curl", "-sf", "-o", "/dev/null", "-w", "%{http_code}", url],
            timeout=30,
        )
        if rc == 0 and out.strip() == "200":
            _log(f"Health check: OK at {url} (elapsed {elapsed}s)")
            return "healthy"
        _log(f"Health check: rc={rc} http={out.strip() or '?'} (elapsed {elapsed}s)")
        time.sleep(interval)
        elapsed += interval
        interval = min(interval * 2, HEALTH_MAX_INTERVAL)
    return "unhealthy"


def _run_smoke(cmd: str, cwd: Path) -> tuple[str, str]:
    """Run smoke command (shell). Return (verdict, output_or_reason)."""
    if not cmd or cmd.strip() in ("—", "-", "none", "None"):
        return "PASS", "(no smoke command configured)"
    rc, out, err = _run(["bash", "-lc", cmd], cwd=cwd, timeout=300)
    if rc == 0:
        return "PASS", (out or "").strip()[:500]
    return f"FAIL — exit {rc}", ((err or out) or "").strip()[:500]


# --- Structured result helper -------------------------------------------

def emit_result(result: dict, exit_code: int = 0) -> None:
    """Emit final result line with completed_at timestamp + structured wrapper, then exit.

    Used by wpx-pipeline (per-WP run result) and wpx-train (per-train
    run result). The `result` dict is wrapped under `{"result": ...}`
    so the calling session reads `data.result` consistently across both
    tools.
    """
    if "completed_at" not in result:
        result["completed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    emit_ok(data={"result": result}, exit_code=exit_code)


# ─────────────────────────────────────────────────────────────────────────
# wpx-train helpers — INDEX parsing, eligibility, batching, overrides
# ─────────────────────────────────────────────────────────────────────────
#
# Used by wpx-train (per-batch path). The eligibility algorithm reads
# state that already exists (INDEX.md + origin branches + per-WP CI
# status) rather than maintaining a separate queue file. See ADR-212
# D6 (amended) for the rationale.
#


# Status values that indicate a WP has finished coding (Steps 1-7) and
# is waiting for batched integration (Steps 8-11).
TRAIN_ELIGIBLE_STATUS = "step-7-complete"
TRAIN_HELD_STATUS = "step-7-held"
TRAIN_BLOCKED_STATUS = "step-7-blocked"
TRAIN_DONE_STATUS = "done"  # Steps 8-11 complete; on dev


# WP table header signature. parse_index_md uses this to find tables.
# We match loosely — the WP table is any markdown table whose header
# row begins with `| ID | Title |`.
_WP_TABLE_HEADER_RE = re.compile(
    r"^\|\s*ID\s*\|\s*Title\s*\|", re.MULTILINE
)


@dataclass
class WPRow:
    """One Work Package row parsed from an INDEX.md table."""

    id: str
    title: str
    primitive: str = ""
    status: str = ""
    depends_on: list[str] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)
    # Extra columns the parser tolerates without using:
    extras: dict[str, str] = field(default_factory=dict)


def _split_csv_or_dash(cell: str) -> list[str]:
    """Parse a comma-separated list cell. Empty / dash → []."""
    s = cell.strip()
    if not s or s in ("—", "-", "none", "None"):
        return []
    return [item.strip() for item in s.split(",") if item.strip()]


def parse_index_md(index_path: Path) -> list[WPRow]:
    """Parse all WP tables in an INDEX.md file. Returns flat list of rows.

    INDEX.md typically contains multiple WP tables — one per section
    (Cross-cutting Armor, Slice 1, Migration track, etc.). This walks
    the document, finds every table whose header begins with `| ID | Title |`,
    and concatenates their rows.

    Recognises the standard columns: ID, Title, Primitive, Status,
    Depends On (or "Depends on"), Blocks. Other columns (Token, TDD §,
    ADR) are tolerated and stored under `extras`.

    Raises FileNotFoundError if the path doesn't exist.
    """
    text = index_path.read_text(encoding="utf-8")
    rows: list[WPRow] = []

    # Find every WP table header position
    for match in _WP_TABLE_HEADER_RE.finditer(text):
        start = match.start()
        # Extract the table block: from header to first blank line or EOF
        end = text.find("\n\n", start)
        if end == -1:
            end = len(text)
        table_text = text[start:end]

        table = parse_md_table(table_text)
        if not table.headers:
            continue

        # Map column names to indices (case-insensitive, strip whitespace)
        col_index: dict[str, int] = {}
        for i, h in enumerate(table.headers):
            key = h.strip().lower().replace("on", "on").rstrip(" *")
            col_index[key] = i

        def get(row: list[str], name: str, default: str = "") -> str:
            key = name.lower()
            i = col_index.get(key)
            if i is None or i >= len(row):
                return default
            return row[i].strip()

        for row in table.rows:
            if not row or not row[0].strip():
                continue
            wp_id = row[0].strip()
            # Skip rows that aren't actually WPs (e.g. summary rows)
            if not wp_id.startswith("WP-"):
                continue

            extras: dict[str, str] = {}
            standard_keys = {"id", "title", "primitive", "status",
                             "depends on", "blocks"}
            for i, h in enumerate(table.headers):
                key = h.strip().lower()
                if key in standard_keys or i >= len(row):
                    continue
                extras[h.strip()] = row[i].strip()

            rows.append(WPRow(
                id=wp_id,
                title=get(row, "title"),
                primitive=get(row, "primitive"),
                status=get(row, "status"),
                depends_on=_split_csv_or_dash(get(row, "depends on")),
                blocks=_split_csv_or_dash(get(row, "blocks")),
                extras=extras,
            ))

    return rows


# --- Overrides (force-include / hold) -----------------------------------

@dataclass
class TrainOverrides:
    """Force-include and hold-back markers for the next train run."""

    includes: list[str] = field(default_factory=list)
    holds: list[str] = field(default_factory=list)


def read_overrides(overrides_path: Path) -> TrainOverrides:
    """Read .architecture/{project}/train-overrides.yaml; tolerate absence.

    File format (YAML-lite, no pyyaml needed):

        includes:
          - WP-X
          - WP-Y
        holds:
          - WP-Z

    Missing file → empty overrides (the common case).
    """
    if not overrides_path.exists():
        return TrainOverrides()
    text = overrides_path.read_text(encoding="utf-8")
    includes: list[str] = []
    holds: list[str] = []
    current: list[str] | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.startswith("#"):
            continue
        if line == "includes:":
            current = includes
            continue
        if line == "holds:":
            current = holds
            continue
        if current is not None and line.startswith("  - "):
            value = line[4:].strip().strip("'\"")
            # Cells may be objects like `{wp: WP-X, reason: "..."}`. Pull the WP.
            if value.startswith("{") and "wp:" in value:
                # Tiny inline-object extraction
                m = re.search(r"wp\s*:\s*([A-Za-z0-9-]+)", value)
                if m:
                    current.append(m.group(1))
            else:
                current.append(value)
    return TrainOverrides(includes=includes, holds=holds)


def write_overrides(overrides_path: Path, overrides: TrainOverrides) -> None:
    """Write the overrides file. Creates parent directory if needed."""
    overrides_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = [
        "# wpx-train overrides — force-include / hold-back markers",
        "# Managed by wpx-train queue-add / queue-remove subcommands.",
        "# Eligibility derives from INDEX.md + origin branches + CI status;",
        "# overrides here are the explicit founder layer on top.",
        "",
    ]
    if overrides.includes:
        lines.append("includes:")
        for wp in overrides.includes:
            lines.append(f"  - {wp}")
        lines.append("")
    if overrides.holds:
        lines.append("holds:")
        for wp in overrides.holds:
            lines.append(f"  - {wp}")
        lines.append("")
    overrides_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --- Eligibility --------------------------------------------------------

@dataclass
class EligibilityResult:
    """One WP's eligibility verdict + reason."""

    wp: str
    branch: str
    eligible: bool
    reason: str
    primitive: str = ""
    forced: bool = False


def _wp_slug_from_file(wp_dir: Path, wp_id: str) -> str | None:
    """Derive the WP's branch slug from its WP file name.

    File convention: `WP-{ID}-{slug}.md`. Returns the slug, or None if
    no matching file exists.
    """
    matches = list(wp_dir.glob(f"{wp_id}-*.md"))
    matches = [
        m for m in matches
        if not m.name.startswith(".")
        and not m.name.startswith("BLOCKER-")
    ]
    if not matches:
        return None
    # Strip "WP-{ID}-" prefix and ".md" suffix
    name = matches[0].stem  # WP-AUTO-018-observability-adapter
    prefix = f"{wp_id}-"
    if not name.startswith(prefix):
        return None
    return name[len(prefix):]


def _branch_name(wp_id: str, slug: str) -> str:
    """Compose the feature-branch name from WP id + slug.

    Convention: `feat/wp-{id-lower}-{slug}`.
    """
    return f"feat/wp-{wp_id.lower().removeprefix('wp-')}-{slug}"


def _gh_branch_exists(repo: str, branch: str) -> bool:
    """True if origin/{branch} exists. Best-effort; returns False on gh error."""
    rc, out, _ = _run(
        ["gh", "api", f"repos/{repo}/git/refs/heads/{branch}"],
        timeout=30,
    )
    return rc == 0 and bool(out.strip())


def _gh_branch_ci_green(repo: str, branch: str) -> bool:
    """True if the branch's most recent CI run is green / completed-success.

    Returns False if checks are pending, failed, or absent. Pending checks
    are treated as "not green" — the train waits for them to complete on a
    future invocation.
    """
    try:
        data = _gh_check_runs(repo, branch)
    except RuntimeError:
        return False
    runs = data.get("check_runs", [])
    if not runs:
        # No CI configured → degenerate "green" (matches wpx-pipeline behaviour)
        return True
    all_done = all(r.get("status") == "completed" for r in runs)
    if not all_done:
        return False
    return all(
        r.get("conclusion") in ("success", "neutral", "skipped")
        for r in runs
    )


def _all_deps_merged(wp: WPRow, by_id: dict[str, WPRow]) -> bool:
    """True if every WP in wp.depends_on has status TRAIN_DONE_STATUS.

    A missing dependency (not in INDEX.md) is treated as a soft failure —
    we cannot prove it's merged, so we conservatively block. Surface this
    via doctor.
    """
    for dep_id in wp.depends_on:
        dep = by_id.get(dep_id)
        if dep is None:
            return False
        if dep.status != TRAIN_DONE_STATUS:
            return False
    return True


def find_eligible_branches(
    wps: list[WPRow],
    repo: str,
    wp_dir: Path,
    overrides: TrainOverrides | None = None,
) -> list[EligibilityResult]:
    """Discover which WPs are eligible for the next train.

    Per the amended ADR-212 D6:

      1. status == step-7-complete (or force-include override)
      2. branch exists on origin
      3. branch CI is green (or force-include override)
      4. all dependencies have status == done
      5. WP is not hold-overridden

    Returns one EligibilityResult per WP — both eligible and ineligible
    are returned so the caller (queue-list / status / doctor) can show
    the founder the full picture.
    """
    overrides = overrides or TrainOverrides()
    by_id = {wp.id: wp for wp in wps}
    results: list[EligibilityResult] = []

    for wp in wps:
        # Skip WPs that aren't candidates at all (done, cancelled, blocked).
        if wp.status in (TRAIN_DONE_STATUS, "cancelled"):
            continue

        is_held = wp.id in overrides.holds
        is_forced = wp.id in overrides.includes

        # Derive branch
        slug = _wp_slug_from_file(wp_dir, wp.id)
        if slug is None:
            results.append(EligibilityResult(
                wp=wp.id, branch="", eligible=False,
                reason=f"no WP file found at {wp_dir}/{wp.id}-*.md",
                primitive=wp.primitive,
            ))
            continue
        branch = _branch_name(wp.id, slug)

        if is_held:
            results.append(EligibilityResult(
                wp=wp.id, branch=branch, eligible=False,
                reason="held by override (train-overrides.yaml)",
                primitive=wp.primitive,
            ))
            continue

        # Status check
        if wp.status != TRAIN_ELIGIBLE_STATUS and not is_forced:
            results.append(EligibilityResult(
                wp=wp.id, branch=branch, eligible=False,
                reason=f"status is '{wp.status}', not '{TRAIN_ELIGIBLE_STATUS}'",
                primitive=wp.primitive,
            ))
            continue

        # Branch existence
        if not _gh_branch_exists(repo, branch):
            results.append(EligibilityResult(
                wp=wp.id, branch=branch, eligible=False,
                reason="status step-7-complete but origin branch missing",
                primitive=wp.primitive,
            ))
            continue

        # CI check (skipped when forced)
        if not is_forced and not _gh_branch_ci_green(repo, branch):
            results.append(EligibilityResult(
                wp=wp.id, branch=branch, eligible=False,
                reason="branch CI not green (pending or failed)",
                primitive=wp.primitive,
            ))
            continue

        # Dependency check
        if not _all_deps_merged(wp, by_id):
            unmet = [
                d for d in wp.depends_on
                if by_id.get(d) is None or by_id[d].status != TRAIN_DONE_STATUS
            ]
            results.append(EligibilityResult(
                wp=wp.id, branch=branch, eligible=False,
                reason=f"dependencies not merged: {', '.join(unmet)}",
                primitive=wp.primitive,
            ))
            continue

        results.append(EligibilityResult(
            wp=wp.id, branch=branch, eligible=True,
            reason="ready" + (" (force-included)" if is_forced else ""),
            primitive=wp.primitive,
            forced=is_forced,
        ))

    return results


# --- Batch packing ------------------------------------------------------

def pack_batches(
    eligible: list[EligibilityResult],
    max_per_batch: int = 5,
) -> list[list[EligibilityResult]]:
    """Pack eligible WPs into batches respecting the max_per_batch ceiling.

    For Phase 2: batches honour the order in `eligible` (which is INDEX.md
    order — already topologically sorted by SEA's decompose).

    Phase 5 (deferred) will refine this to use per-primitive batch_hint
    ceilings (CONTRACT-Delete=1, REORGANISE=2-3, EXPAND=5-8). For now,
    flat max_per_batch.
    """
    ready = [e for e in eligible if e.eligible]
    batches: list[list[EligibilityResult]] = []
    current: list[EligibilityResult] = []
    for e in ready:
        if len(current) >= max_per_batch:
            batches.append(current)
            current = []
        current.append(e)
    if current:
        batches.append(current)
    return batches


# --- Train run helpers (Phase 2) ---------------------------------------

# Trigger thresholds. Documented in ADR-212 D1. The amendment notes
# these should be revisited once the DAG-level batch unit is in
# (PH-research follow-up item 6).
TRAIN_TRIGGER_MIN_SIZE = 3
TRAIN_TRIGGER_STALENESS_SECONDS = 4 * 60 * 60  # 4 hours


def check_train_trigger(
    eligible: list[EligibilityResult],
    force: bool = False,
    queued_at_lookup: dict[str, str] | None = None,
    now: datetime | None = None,
) -> tuple[bool, str]:
    """Decide whether the train should fire.

    Triggers (any one is sufficient):
      - force:        --force flag passed
      - size:         >= TRAIN_TRIGGER_MIN_SIZE eligible WPs
      - staleness:    >= 1 eligible WP older than TRAIN_TRIGGER_STALENESS_SECONDS

    Returns (should_fire, reason).

    `queued_at_lookup` maps wp_id → ISO 8601 UTC timestamp string.
    Missing entries are treated as "just queued" (no staleness pressure).

    `now` is for testability — defaults to datetime.now(UTC).
    """
    if force:
        return True, "force"
    if not eligible:
        return False, "no eligible WPs"
    if len(eligible) >= TRAIN_TRIGGER_MIN_SIZE:
        return True, f"size trigger: {len(eligible)} >= {TRAIN_TRIGGER_MIN_SIZE}"
    # Staleness check
    now = now or datetime.now(timezone.utc)
    queued_at_lookup = queued_at_lookup or {}
    for e in eligible:
        ts_str = queued_at_lookup.get(e.wp)
        if not ts_str:
            continue
        try:
            ts = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc,
            )
        except (ValueError, TypeError):
            continue
        age = (now - ts).total_seconds()
        if age >= TRAIN_TRIGGER_STALENESS_SECONDS:
            return True, (
                f"staleness trigger: {e.wp} queued "
                f"{int(age // 60)}m ago "
                f"(>= {TRAIN_TRIGGER_STALENESS_SECONDS // 60}m)"
            )
    return False, (
        f"{len(eligible)} eligible (need {TRAIN_TRIGGER_MIN_SIZE} for size "
        f"or >={TRAIN_TRIGGER_STALENESS_SECONDS // 60}m staleness on one WP)"
    )


def clone_repo_to_temp(repo: str, dest: Path) -> None:
    """Clone the repo to `dest` for the duration of a train run.

    Uses `gh repo clone` (preferred — handles auth) with a fallback to
    `git clone` from origin via the GITHUB_TOKEN env var if available.

    Raises RuntimeError on failure.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    rc, _, err = _run(
        ["gh", "repo", "clone", repo, str(dest), "--", "--depth", "100"],
        timeout=120,
    )
    if rc == 0:
        return
    # Fallback: direct git clone using GITHUB_TOKEN if present
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        url = f"https://x-access-token:{token}@github.com/{repo}.git"
    else:
        url = f"https://github.com/{repo}.git"
    rc, _, err = _run(["git", "clone", "--depth", "100", url, str(dest)],
                     timeout=120)
    if rc != 0:
        raise RuntimeError(f"clone failed for {repo}: {err}")


def rebase_branch_in_clone(
    clone_dir: Path,
    branch: str,
    onto: str,
) -> str:
    """Within an existing clone: fetch, checkout, rebase, push --force-with-lease.

    `onto` is a SHA or ref the branch should be rebased on top of.
    Returns the new HEAD SHA after rebase + push.

    Raises RuntimeError on rebase conflict; the caller (Phase 3) catches
    this and removes the offending WP from the batch.
    """
    # Fetch latest of both
    rc, _, err = _run(["git", "fetch", "origin", branch], cwd=clone_dir,
                     timeout=60)
    if rc != 0:
        raise RuntimeError(f"git fetch {branch} failed: {err}")
    rc, _, err = _run(["git", "fetch", "origin", "dev"], cwd=clone_dir,
                     timeout=60)
    if rc != 0:
        raise RuntimeError(f"git fetch dev failed: {err}")

    # Checkout the branch (creating a local tracking branch if needed)
    rc, _, err = _run(["git", "checkout", "-B", branch,
                       f"origin/{branch}"], cwd=clone_dir, timeout=30)
    if rc != 0:
        raise RuntimeError(f"git checkout {branch} failed: {err}")

    # Rebase onto the target SHA / ref
    rc, _, err = _run(["git", "rebase", onto], cwd=clone_dir, timeout=120)
    if rc != 0:
        _run(["git", "rebase", "--abort"], cwd=clone_dir, timeout=30)
        raise RuntimeError(f"git rebase {branch} onto {onto[:8]} failed: {err}")

    # Push --force-with-lease (safe: only force if remote matches what we fetched)
    rc, _, err = _run(["git", "push", "--force-with-lease", "origin", branch],
                     cwd=clone_dir, timeout=60)
    if rc != 0:
        raise RuntimeError(f"git push --force-with-lease {branch} failed: {err}")

    # Read the new HEAD SHA
    rc, out, _ = _run(["git", "rev-parse", "HEAD"], cwd=clone_dir, timeout=10)
    if rc != 0:
        raise RuntimeError(f"git rev-parse HEAD failed in {clone_dir}")
    return out.strip()


def write_train_run_record(record_path: Path, record: dict) -> None:
    """Write a train run record to .architecture/{project}/train-runs/train-{ts}.yaml.

    Uses a YAML-lite emitter (no pyyaml dep). The record schema:

        train_id: train-{TIMESTAMP}
        started_at: ISO 8601 UTC
        completed_at: ISO 8601 UTC
        outcome: success | blocker | error
        outcome_reason: str (when not success)
        batch_size: N
        bundle:
          - wp: WP-X
            branch: feat/wp-x-slug
            pre_train_sha: <sha>
            rebased_to_sha: <sha>
            merge_sha_on_dev: <sha or null>
        deploy_url: str | null
        deploy_workflow_run: str | null
        health_status: str | null
        smoke_verdict: str | null
    """
    record_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for k in ("train_id", "started_at", "completed_at", "outcome",
              "outcome_reason", "batch_size", "deploy_url",
              "deploy_workflow_run", "health_status", "smoke_verdict"):
        if k in record:
            value = record[k]
            if value is None:
                lines.append(f"{k}: null")
            elif isinstance(value, (int, float)):
                lines.append(f"{k}: {value}")
            else:
                # Quote strings to be safe
                escaped = str(value).replace('"', '\\"')
                lines.append(f'{k}: "{escaped}"')
    bundle = record.get("bundle", [])
    if bundle:
        lines.append("bundle:")
        for item in bundle:
            lines.append(f"  - wp: {item.get('wp', '')}")
            for k in ("branch", "pre_train_sha", "rebased_to_sha",
                      "merge_sha_on_dev"):
                v = item.get(k)
                if v is None:
                    lines.append(f"    {k}: null")
                else:
                    lines.append(f"    {k}: {v}")
    record_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --- Phase 3: failure handling helpers ----------------------------------

def flip_index_status_via_cli(
    scripts_dir: Path,
    paths: WpxPaths,
    wp_id: str,
    to_status: str,
    expected: str | None = None,
) -> tuple[bool, str]:
    """Shell out to wpx-index flip-status. Returns (success, message).

    Doesn't raise — the caller (failure-path code in wpx-train) wants
    to keep going even if one INDEX flip fails. The error is returned
    so the caller can surface it in the train BLOCKER record.
    """
    args = [
        str(scripts_dir / "wpx-index"), "flip-status",
        "--project", paths.project,
        "--repo-root", str(paths.repo_root),
        "--wp", wp_id,
        "--to", to_status,
    ]
    if expected:
        args.extend(["--expected", expected])
    rc, out, err = _run(args, timeout=30)
    if rc == 0:
        return True, ""
    return False, err or out or f"wpx-index flip-status rc={rc}"


def write_wp_blocker_via_cli(
    scripts_dir: Path,
    paths: WpxPaths,
    wp_id: str,
    title: str,
    observation: str,
    root_cause: str,
    plain_english: str,
    suggested_next: str,
    step: str = "Step 8 (train run)",
    trigger: str = "wpx-train",
) -> tuple[bool, str]:
    """Shell out to wpx-blocker write. Returns (success, message)."""
    args = [
        str(scripts_dir / "wpx-blocker"), "write",
        "--project", paths.project,
        "--repo-root", str(paths.repo_root),
        "--wp", wp_id,
        "--title", title,
        "--step", step,
        "--trigger", trigger,
        "--observation", observation,
        "--root-cause", root_cause,
        "--scope", "indeterminate",
        "--scope-reason", "Identified by train failure-path; needs human triage",
        "--plain-english", plain_english,
        "--suggested-next", suggested_next,
        "--force",
    ]
    rc, out, err = _run(args, timeout=30)
    if rc == 0:
        return True, ""
    return False, err or out or f"wpx-blocker write rc={rc}"


def write_train_blocker(
    paths: WpxPaths,
    train_id: str,
    reason: str,
    bundle: list[dict],
    suspected_wp_id: str | None = None,
    evidence: str = "",
) -> Path:
    """Write a train-level BLOCKER-train-{ts}.md.

    Distinct from per-WP BLOCKER files: this records the train as a
    whole, lists all bundled WPs and which (if any) was flagged as the
    likely culprit by the file-overlap heuristic.
    """
    blocker_path = paths.wp_dir / f"BLOCKER-{train_id}.md"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines = [
        f"# BLOCKER-{train_id}",
        "",
        f"> Created: {now} by sulis-execution wpx-train",
        f"> Scope: train run {train_id}",
        f"> Reason: {reason}",
        "",
        "## What happened",
        "",
        reason,
        "",
        "## Bundled Work Packages",
        "",
        "| WP | Branch | Pre-train SHA | Merged? |",
        "|---|---|---|---|",
    ]
    for entry in bundle:
        merge_sha = entry.get("merge_sha_on_dev") or "—"
        lines.append(
            f"| {entry.get('wp', '?')} | {entry.get('branch', '?')} | "
            f"{(entry.get('pre_train_sha') or '?')[:8]} | {merge_sha[:8] if merge_sha != '—' else '—'} |"
        )

    lines.extend(["", "## Suggested culprit (file-overlap heuristic)", ""])
    if suspected_wp_id:
        lines.append(f"**Most likely culprit: {suspected_wp_id}**")
        lines.append("")
        lines.append(
            "The file-overlap heuristic compared each WP's changed-file set "
            "to file names mentioned in the failure output. The WP with the "
            "most overlap is named above. This is a starting point — verify "
            "before holding the WP back from the next train."
        )
    else:
        lines.append(
            "The file-overlap heuristic could not identify a specific "
            "culprit. Investigate each WP in the bundle individually."
        )

    if evidence:
        lines.extend(["", "## Evidence", "", "```", evidence[:4000], "```"])

    lines.extend([
        "",
        "## Plain-English summary (for the founder)",
        "",
        f"The train run {train_id} did not complete. {reason}. "
        f"All {len(bundle)} WPs in the batch have been moved to "
        f"`step-7-blocked` status. Investigate the suspected culprit "
        f"first, then re-queue the rest for the next train.",
        "",
        "## Suggested next step",
        "",
        "1. Read the evidence above to confirm the suspected culprit",
        "2. Investigate that WP's branch locally if needed",
        "3. Flip its status back to `step-7-complete` (or fix and re-push) "
        "when ready",
        "4. The next `wpx-train run` will pick up the remaining WPs",
        "",
    ])
    blocker_path.parent.mkdir(parents=True, exist_ok=True)
    blocker_path.write_text("\n".join(lines), encoding="utf-8")
    return blocker_path


def compute_culprit_heuristic(
    bundle: list[dict],
    clone_dir: Path,
    failure_text: str,
) -> str | None:
    """Best-effort: which WP in the bundle most likely caused the failure?

    For each WP, lists files changed by its branch (via git diff against
    its pre_train_sha base). Counts overlap with file names mentioned in
    failure_text. The WP with the most overlap wins.

    Returns the WP id, or None if no overlap detected.

    This is heuristic — it's right often enough to save investigation
    time; not right enough to auto-eject a WP silently. The train
    BLOCKER surfaces it as a "suggested" culprit only.
    """
    if not bundle or not failure_text:
        return None
    best_wp: str | None = None
    best_score = 0
    for entry in bundle:
        branch = entry.get("branch")
        pre_sha = entry.get("pre_train_sha")
        if not branch or not pre_sha:
            continue
        rc, out, _ = _run(
            ["git", "diff", "--name-only", pre_sha, "HEAD"],
            cwd=clone_dir, timeout=30,
        )
        if rc != 0:
            continue
        files = [f.strip() for f in out.splitlines() if f.strip()]
        score = sum(1 for f in files if f and f in failure_text)
        if score > best_score:
            best_score = score
            best_wp = entry.get("wp")
    return best_wp


def revert_train_on_dev(
    repo: str,
    clone_dir: Path,
    bundle: list[dict],
    reason: str,
    train_id: str,
) -> tuple[bool, str]:
    """Revert all merged WPs in the bundle in reverse order, push to dev.

    Produces a single wrapper commit
    `revert(train-{ts}): rollback {WPs} — {reason}` on `dev`.

    Returns (success, message). On failure, the caller should NOT
    attempt branch restoration — investigate manually.
    """
    merged = [e for e in bundle if e.get("merge_sha_on_dev")]
    if not merged:
        return True, "no merged WPs to revert"

    # Checkout dev, fetch latest
    rc, _, err = _run(["git", "fetch", "origin", "dev"], cwd=clone_dir,
                     timeout=60)
    if rc != 0:
        return False, f"git fetch dev failed: {err}"
    rc, _, err = _run(["git", "checkout", "-B", "dev", "origin/dev"],
                     cwd=clone_dir, timeout=30)
    if rc != 0:
        return False, f"git checkout dev failed: {err}"

    # Revert each merge SHA in reverse order; --no-commit to stage all
    # changes into a single wrapper commit
    for entry in reversed(merged):
        sha = entry["merge_sha_on_dev"]
        rc, _, err = _run(
            ["git", "revert", "--no-commit", "-m", "1", sha],
            cwd=clone_dir, timeout=60,
        )
        if rc != 0:
            # If it's not a merge commit (-m fails), try plain revert
            rc, _, err = _run(["git", "revert", "--no-commit", sha],
                             cwd=clone_dir, timeout=60)
            if rc != 0:
                return False, f"git revert {sha[:8]} failed: {err}"

    wp_list = ", ".join(e.get("wp", "?") for e in merged)
    msg = f"revert({train_id}): rollback {wp_list} — {reason}"
    rc, _, err = _run(["git", "commit", "-m", msg], cwd=clone_dir, timeout=30)
    if rc != 0:
        return False, f"git commit (revert wrapper) failed: {err}"
    rc, _, err = _run(["git", "push", "origin", "dev"], cwd=clone_dir,
                     timeout=60)
    if rc != 0:
        return False, f"git push dev (revert) failed: {err}"
    return True, f"reverted {len(merged)} merges under wrapper commit"


def restore_branch_with_guard(
    repo: str,
    clone_dir: Path,
    branch: str,
    pre_train_sha: str,
    rebased_to_sha: str,
) -> tuple[bool, str]:
    """Restore a branch to its pre_train_sha — but only if no new push happened.

    Force-push guard: fetch origin/{branch}'s current SHA; if it matches
    rebased_to_sha (what the train left), force-push pre_train_sha.
    If it differs, the founder (or another agent) pushed in the
    meantime — abort the restore with a warning.

    Returns (success, message). Success=False with message="newer push"
    is the guard firing; the caller surfaces this in the BLOCKER.
    """
    rc, _, err = _run(["git", "fetch", "origin", branch], cwd=clone_dir,
                     timeout=60)
    if rc != 0:
        return False, f"git fetch {branch} failed: {err}"
    rc, out, _ = _run(
        ["git", "rev-parse", f"origin/{branch}"],
        cwd=clone_dir, timeout=10,
    )
    if rc != 0:
        return False, f"git rev-parse origin/{branch} failed"
    current = out.strip()

    if current != rebased_to_sha:
        return False, (
            f"newer push detected: origin/{branch} is at {current[:8]}, "
            f"train left {rebased_to_sha[:8]}. Skipping force-reset to "
            f"avoid overwriting unrelated work."
        )

    # Safe to restore
    rc, _, err = _run(
        ["git", "push", "--force-with-lease="
         f"{branch}:{rebased_to_sha}",
         "origin", f"+{pre_train_sha}:refs/heads/{branch}"],
        cwd=clone_dir, timeout=60,
    )
    if rc != 0:
        return False, f"git push --force-with-lease failed: {err}"
    return True, "restored"


# ─────────────────────────────────────────────────────────────────────────
# sulis-change helpers (CW-01..CW-08)
# ─────────────────────────────────────────────────────────────────────────
#
# The Change Work Standard at plugins/srd/references/change-work-standard.md
# defines a change as the unit of work — every piece of work that evolves
# the system is bounded by a change/{primitive}-{slug} branch with a
# dedicated git worktree. The helpers below support the sulis-change CLI.
#


# CW-02: allowed primitives. Full 22 from change-primitives.md +
# Conventional Commits fallbacks for unclassified work.
_CHANGE_PRIMITIVES_EXPAND = ("create", "extend", "reuse", "compose", "generate")
_CHANGE_PRIMITIVES_REORGANISE = ("move", "refactor", "inline", "merge",
                                  "decompose", "abstract")
_CHANGE_PRIMITIVES_SUBSTITUTE = ("replace", "strangle", "wrap")
_CHANGE_PRIMITIVES_CONTRACT = ("deprecate", "delete")
_CHANGE_PRIMITIVES_REINFORCE = ("test", "instrument", "secure", "harden",
                                 "gate", "document")
_CHANGE_PRIMITIVES_CC_FALLBACK = ("feat", "fix", "chore")

ALLOWED_CHANGE_PRIMITIVES = (
    _CHANGE_PRIMITIVES_EXPAND
    + _CHANGE_PRIMITIVES_REORGANISE
    + _CHANGE_PRIMITIVES_SUBSTITUTE
    + _CHANGE_PRIMITIVES_CONTRACT
    + _CHANGE_PRIMITIVES_REINFORCE
    + _CHANGE_PRIMITIVES_CC_FALLBACK
)

# CW-02 slug rule: 2-5 kebab-case words. First word must start with a
# letter; subsequent words may be alphanumeric (so `wp-001` is valid).
_CHANGE_SLUG_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+){1,4}$")


def validate_change_slug(slug: str) -> tuple[bool, str]:
    """Return (ok, reason). Slug must be 2-5 kebab-case words."""
    if not slug:
        return False, "slug is empty"
    if not _CHANGE_SLUG_RE.match(slug):
        return False, (
            f"slug '{slug}' is not 2-5 kebab-case words "
            f"(e.g. 'introduce-payments', 'extract-http-client')"
        )
    return True, ""


def validate_change_primitive(primitive: str) -> tuple[bool, str]:
    """Return (ok, reason). Primitive must be one of ALLOWED_CHANGE_PRIMITIVES."""
    if not primitive:
        return False, "primitive is empty"
    if primitive.lower() not in ALLOWED_CHANGE_PRIMITIVES:
        return False, (
            f"primitive '{primitive}' not in allowed set: "
            f"{', '.join(ALLOWED_CHANGE_PRIMITIVES)}"
        )
    return True, ""


def compose_change_branch(primitive: str, slug: str) -> str:
    """Compose a CW-02 branch name: change/{primitive}-{slug}.

    Raises ValueError on invalid primitive or slug.
    """
    ok, reason = validate_change_primitive(primitive)
    if not ok:
        raise ValueError(reason)
    ok, reason = validate_change_slug(slug)
    if not ok:
        raise ValueError(reason)
    return f"change/{primitive.lower()}-{slug.lower()}"


def parse_change_branch(branch: str) -> tuple[str, str] | None:
    """Inverse of compose_change_branch. Returns (primitive, slug) or None."""
    if not branch.startswith("change/"):
        return None
    rest = branch[len("change/"):]
    # The primitive is the first dash-separated token; the slug is the rest.
    if "-" not in rest:
        return None
    first, _, slug = rest.partition("-")
    if first not in ALLOWED_CHANGE_PRIMITIVES:
        return None
    return (first, slug)


def change_worktree_path(repo_root: Path, primitive: str, slug: str) -> Path:
    """Compose the worktree path for a change.

    Convention: sibling of the main repo at
    `<repo-parent>/<repo-name>-change-<primitive>-<slug>/`.
    """
    return repo_root.parent / f"{repo_root.name}-change-{primitive}-{slug}"


def write_change_metadata(metadata_path: Path, data: dict) -> None:
    """Write a .changes/{primitive}-{slug}.yaml metadata file.

    Uses the same YAML-lite emitter pattern as write_train_run_record.
    Schema fields:
      slug: str
      primitive: str
      branch: str
      worktree_path: str
      base_branch: str
      base_sha: str
      started_at: ISO 8601 UTC
      adopted_from_sha: str | null   (only present for adopt)
      adopt_mode: str | null         (forward | rewrite)
    """
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for k in ("slug", "primitive", "branch", "worktree_path", "base_branch",
              "base_sha", "started_at", "adopted_from_sha", "adopt_mode"):
        if k not in data:
            continue
        v = data[k]
        if v is None:
            lines.append(f"{k}: null")
        elif isinstance(v, (int, float)):
            lines.append(f"{k}: {v}")
        else:
            escaped = str(v).replace('"', '\\"')
            lines.append(f'{k}: "{escaped}"')
    metadata_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_change_metadata(metadata_path: Path) -> dict:
    """Read a metadata file written by write_change_metadata. Returns {} if missing."""
    if not metadata_path.exists():
        return {}
    out: dict = {}
    for raw in metadata_path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, rest = line.partition(":")
        key = key.strip()
        rest = rest.strip()
        if rest == "null":
            out[key] = None
        elif rest.startswith('"') and rest.endswith('"'):
            out[key] = rest[1:-1]
        else:
            try:
                out[key] = int(rest)
            except ValueError:
                out[key] = rest
    return out


def git_worktree_add(repo_root: Path, branch: str, dest: Path,
                     base_ref: str = "dev") -> tuple[bool, str]:
    """Create a worktree at `dest` for a new branch off `base_ref`.

    If the branch already exists, the worktree is added on the existing
    branch. If `dest` already exists, returns (False, "destination exists").

    Returns (ok, message_or_error).
    """
    if dest.exists():
        return False, f"destination already exists: {dest}"

    # Check if branch already exists locally
    rc, out, _ = _run(["git", "rev-parse", "--verify", f"refs/heads/{branch}"],
                     cwd=repo_root, timeout=10)
    branch_exists = rc == 0

    if branch_exists:
        rc, _, err = _run(["git", "worktree", "add", str(dest), branch],
                         cwd=repo_root, timeout=60)
    else:
        rc, _, err = _run(["git", "worktree", "add", "-b", branch,
                          str(dest), base_ref],
                         cwd=repo_root, timeout=60)
    if rc != 0:
        return False, f"git worktree add failed: {err}"
    return True, str(dest)


def git_worktree_remove(repo_root: Path, dest: Path,
                        force: bool = False) -> tuple[bool, str]:
    """Remove a worktree at `dest`. Tolerates a missing worktree.

    Returns (ok, message).
    """
    if not dest.exists():
        # Try `git worktree prune` in case the worktree was deleted manually
        _run(["git", "worktree", "prune"], cwd=repo_root, timeout=10)
        return True, "worktree already absent (pruned)"
    args = ["git", "worktree", "remove", str(dest)]
    if force:
        args.append("--force")
    rc, _, err = _run(args, cwd=repo_root, timeout=30)
    if rc != 0:
        return False, f"git worktree remove failed: {err}"
    return True, "removed"


def detect_adopt_state(repo_root: Path,
                      remote_ref: str = "origin/dev") -> dict:
    """Inspect the current repo state for `sulis-change adopt`.

    Returns a dict:
      {
        "current_branch": str,
        "has_uncommitted": bool,
        "uncommitted_files": list[str],
        "local_commits_ahead": list[str],   # commit SHAs
        "pushed_commits_can_rewrite": bool, # only true when current branch = remote tracking branch and there's no work upstream
        "base_sha": str,                     # remote_ref's SHA
      }

    Used by sulis-change adopt to pick the right retrofit flavour.
    """
    out: dict = {
        "current_branch": "",
        "has_uncommitted": False,
        "uncommitted_files": [],
        "local_commits_ahead": [],
        "pushed_commits_can_rewrite": False,
        "base_sha": "",
    }

    # Current branch
    rc, branch_out, _ = _run(["git", "branch", "--show-current"],
                             cwd=repo_root, timeout=10)
    if rc == 0:
        out["current_branch"] = branch_out.strip()

    # Uncommitted changes
    rc, status_out, _ = _run(["git", "status", "--porcelain"],
                             cwd=repo_root, timeout=10)
    if rc == 0 and status_out.strip():
        out["has_uncommitted"] = True
        out["uncommitted_files"] = [
            line[3:].strip() for line in status_out.splitlines()
            if line.strip()
        ]

    # Fetch the remote ref's SHA (best-effort)
    rc, remote_sha_out, _ = _run(["git", "rev-parse", remote_ref],
                                 cwd=repo_root, timeout=10)
    if rc == 0:
        out["base_sha"] = remote_sha_out.strip()

    # Commits ahead of remote
    rc, ahead_out, _ = _run(
        ["git", "rev-list", f"{remote_ref}..HEAD"],
        cwd=repo_root, timeout=10,
    )
    if rc == 0 and ahead_out.strip():
        out["local_commits_ahead"] = [
            sha.strip() for sha in ahead_out.splitlines() if sha.strip()
        ]

    # "Pushed commits to retrofit" requires --mode rewrite; we don't auto-detect
    # this state because it's ambiguous without intent. The caller passes
    # --mode rewrite to enter that path.

    return out


def adopt_uncommitted_into_change(
    repo_root: Path,
    branch: str,
    base_ref: str,
    worktree_dest: Path,
    uncommitted_files: list[str],
) -> tuple[bool, str]:
    """Retrofit case 1: stash uncommitted changes, create change branch +
    worktree, unstash into the worktree.

    Returns (ok, message).
    """
    if not uncommitted_files:
        # Nothing to move — caller should not call this
        return True, "no uncommitted changes; nothing to adopt"

    # Stash the uncommitted work
    rc, _, err = _run(["git", "stash", "push", "-u", "-m",
                       f"sulis-change adopt {branch}"],
                     cwd=repo_root, timeout=30)
    if rc != 0:
        return False, f"git stash push failed: {err}"

    # Create the change branch + worktree
    ok, msg = git_worktree_add(repo_root, branch, worktree_dest, base_ref)
    if not ok:
        # Try to restore the stash before returning the error
        _run(["git", "stash", "pop"], cwd=repo_root, timeout=30)
        return False, f"worktree creation failed: {msg}; stash restored"

    # Pop the stash into the new worktree (git stash pop in the worktree
    # restores the changes there)
    rc, _, err = _run(["git", "stash", "pop"], cwd=worktree_dest, timeout=30)
    if rc != 0:
        return False, f"git stash pop in worktree failed: {err}"

    return True, f"adopted {len(uncommitted_files)} uncommitted change(s) into {branch}"


def adopt_local_commits_into_change(
    repo_root: Path,
    branch: str,
    base_ref: str,
    worktree_dest: Path,
    local_commits: list[str],
) -> tuple[bool, str]:
    """Retrofit case 2: cherry-pick local-only commits onto the change
    branch, then reset local dev to the remote.

    Returns (ok, message).
    """
    if not local_commits:
        return True, "no local commits to retrofit"

    current_branch = ""
    rc, branch_out, _ = _run(["git", "branch", "--show-current"],
                             cwd=repo_root, timeout=10)
    if rc == 0:
        current_branch = branch_out.strip()

    # Create change branch + worktree (off the base ref, which is the
    # remote tip — the place we want to relocate FROM)
    ok, msg = git_worktree_add(repo_root, branch, worktree_dest, base_ref)
    if not ok:
        return False, f"worktree creation failed: {msg}"

    # Cherry-pick the local commits (in chronological order) into the worktree.
    # local_commits is newest-first from rev-list, so reverse for cherry-pick order.
    for sha in reversed(local_commits):
        rc, _, err = _run(["git", "cherry-pick", sha],
                         cwd=worktree_dest, timeout=60)
        if rc != 0:
            # Abort + return; user can investigate
            _run(["git", "cherry-pick", "--abort"], cwd=worktree_dest, timeout=10)
            return False, f"cherry-pick {sha[:8]} failed: {err}"

    # Reset local current_branch (the place we relocated FROM) to the remote tip
    if current_branch:
        rc, _, err = _run(
            ["git", "reset", "--hard", base_ref],
            cwd=repo_root, timeout=30,
        )
        if rc != 0:
            return False, (
                f"reset {current_branch} to {base_ref} failed: {err}. "
                f"Change branch was created; you may need to manually reset "
                f"{current_branch}."
            )

    return True, (
        f"retrofitted {len(local_commits)} commit(s) from "
        f"{current_branch} onto {branch}; {current_branch} reset to {base_ref}"
    )


def find_change_branches(repo_root: Path) -> list[dict]:
    """List all change/* branches in the local repo with basic state.

    Returns a list of dicts:
      [{"branch": str, "primitive": str, "slug": str, "current": bool}, ...]
    """
    rc, out, _ = _run(["git", "branch", "--list", "change/*"],
                     cwd=repo_root, timeout=10)
    if rc != 0:
        return []

    result: list[dict] = []
    for raw in out.splitlines():
        line = raw.rstrip()
        if not line:
            continue
        # git branch output: "* branch" (current), "+ branch" (other
        # worktree), "  branch" (uncheckout). Strip the marker.
        is_current = line.startswith("* ")
        branch = line.lstrip("*+ \t").strip()
        if not branch:
            continue
        parsed = parse_change_branch(branch)
        if parsed is None:
            continue
        primitive, slug = parsed
        result.append({
            "branch": branch,
            "primitive": primitive,
            "slug": slug,
            "current": is_current,
        })
    return result
