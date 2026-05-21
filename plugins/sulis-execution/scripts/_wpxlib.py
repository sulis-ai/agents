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
                   dev_sha_at_creation: str) -> tuple[bool, str]:
    """If dev advanced past dev_sha_at_creation, rebase. Return (rebased, new_sha)."""
    current_dev = _gh_ref_sha(repo, "dev")
    if current_dev == dev_sha_at_creation:
        return False, ""
    _log(f"dev advanced from {dev_sha_at_creation[:8]} to {current_dev[:8]}; rebasing")
    rc, _, err = _run(["git", "fetch", "origin", "dev"], cwd=worktree)
    if rc != 0:
        raise RuntimeError(f"git fetch failed: {err}")
    rc, _, err = _run(["git", "rebase", "origin/dev"], cwd=worktree)
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


def _merge_squash(repo: str, branch: str, wp: str) -> str:
    """Squash-merge branch into dev. Return merge SHA on dev."""
    msg = f"feat({wp.lower()}): squash-merge from {branch}"
    sha = _gh_merge(repo, base="dev", head=branch, commit_message=msg)
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
