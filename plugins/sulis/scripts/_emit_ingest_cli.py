"""Shared CLI body for the ingest emitters (Tool/Step/Workflow/Scenario).

Each `sulis-emit-{entity}` is a 3-line shim that calls `run_ingest_cli` with
its `entity_type` + `domain` + `list_key`. The argparse surface, repo-root
resolution, adapter construction, skip-reporting, and JSON envelope live here
once (EP-03) — the four CLIs were otherwise byte-identical bar three constants.

Envelope: `{"ok": true, "data": {...}}` on success (incl. an empty source),
`{"ok": false, "error": "..."}` on failure. Exit 0 / 1 respectively.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from _entity_adapter_local import LocalFileEntityAdapter  # noqa: E402
from _entity_repository import EntityValidationError  # noqa: E402
from _instance_ingest import ingest_instances, skipped_instances  # noqa: E402


def _resolve_repo_root(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True, timeout=10,
        )
        return Path(out.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return Path.cwd()


def run_ingest_cli(*, entity_type: str, domain: str, list_key: str) -> int:
    parser = argparse.ArgumentParser(
        description=f"Ingest authored {list_key}.jsonld into the brain ({entity_type})."
    )
    parser.add_argument("--from-instances", required=True,
                        help=f"path to an authored {list_key}.jsonld")
    parser.add_argument("--base-dir")
    parser.add_argument("--domain", default=domain)
    parser.add_argument("--repo-root")
    args = parser.parse_args()

    src = Path(args.from_instances).resolve()
    if not src.exists():
        print(json.dumps({"ok": False, "error": f"{list_key}.jsonld not found: {src}"}, indent=2))
        return 1

    repo_root = _resolve_repo_root(args.repo_root)
    base_dir = (
        Path(args.base_dir).resolve()
        if args.base_dir
        else repo_root / ".brain" / "instances"
    )
    adapter = LocalFileEntityAdapter(base_dir=base_dir, domain=args.domain)

    skipped = [s.get("name") or "(unnamed)"
               for s in skipped_instances(src.read_text(encoding="utf-8"), list_key=list_key)]

    try:
        entities = ingest_instances(src, adapter, entity_type=entity_type, list_key=list_key)
    except (EntityValidationError, FileNotFoundError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1

    entries = [
        {
            "id": e["id"],
            "name": e.get("name"),
            "path": str(base_dir / args.domain / entity_type / f"{e['id'].rsplit(':', 1)[-1]}.jsonld"),
        }
        for e in entities
    ]
    print(json.dumps({
        "ok": True,
        "data": {
            "from_instances": str(src),
            "count": len(entries),
            "entities": entries,
            # "no silent truncation": id-less stub entries are reported, not dropped quietly
            "skipped_incomplete": skipped,
        },
    }, indent=2))
    return 0
