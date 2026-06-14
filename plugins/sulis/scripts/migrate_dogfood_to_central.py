#!/usr/bin/env python3
"""migrate_dogfood_to_central — move the repo's dogfood Brain records into the
central brain, merge the two products into one (ADR-002), and report the files
to remove from the repo (WP-005 / HD-004).

The repo carries its own dogfood Brain captures under `.brain/instances/
product-development/*` plus a `foundation/tenant` and a `labels/roadmap.jsonld`
sidecar. Those belong in the **central** brain (the user-level installed-user
home), not committed to the repo. This one-shot tool moves them there, then
hands back the list of files for the caller to `git rm`.

Two products, one survivor (ADR-002, `--two-products=merge`)
-----------------------------------------------------------
Central already holds the canonical product (the "survivor"); the repo holds a
second product entity (the "retiree") with the requirements attached. Merging
means: keep the survivor untouched, re-point every migrated record's
`for_product` edge from the retiree id onto the survivor id, merge any
retiree-only product metadata ONTO the survivor, and never write the retiree as
a second product. The result is exactly one product centrally with all the
requirements attached.

Design (hexagonal-lite, stdlib-only per the plugin script contract)
-------------------------------------------------------------------
- Pure core: `compute_migration_set` (what moves), `_repoint` (edge rewrite),
  `_merge_product_metadata` (retiree → survivor). No I/O.
- `build_manifest` (the `--dry-run` path): computes the plan + writes the
  reversibility manifest; mutates nothing.
- `migrate` (the `--execute` path): copies records, rewrites edges, merges the
  product, returns a `MigrationResult` carrying the manifest + the git-rm set.
- `reverse_record`: restores one record (and its original edge) from a manifest
  entry — the manifest is the single reversibility source.

Idempotency. Records are keyed on the ULID filename, edge rewrites on the stable
record id: a second run copies nothing new and re-points nothing (the edge
already names the survivor). Merge-not-collide: an id already present centrally
is not duplicated; central's existing records (its lifecycleruns, its
foundation/project) are preserved untouched.

Safety. The destination is resolved via `brain_base_dir` — no hard-coded path —
and NO product ULID is hard-coded: the survivor and retiree ids are arguments
(resolved at runtime by the caller). `--dry-run` is the default; the tool only
mutates when `--execute` is passed explicitly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

# The roadmap sidecar's on-disk contract lives in _brain_labels (single source).
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
from _brain_labels import roadmap_sidecar_path  # noqa: E402

# Product-development is the domain that moves wholesale (minus the retired
# product file); from foundation only `tenant` moves — workflow/step/tool are
# the shared library and STAY in the repo.
_PRODUCT_DEV = "product-development"
_FOUNDATION = "foundation"
_FOUNDATION_MIGRATES = ("tenant",)  # everything else under foundation stays
_PRODUCT_TYPE = "product"
#: Record types whose product back-reference is the `for_product` edge we rewrite.
_EDGE_FIELD = "for_product"


@dataclass(frozen=True)
class MigrationEntry:
    """One record in the migration set, relative to the instances root."""

    rel_path: str  # e.g. "product-development/requirement/<ULID>.jsonld"
    src: Path
    entity_id: str


@dataclass
class MigrationResult:
    """Outcome of an `--execute` run."""

    manifest: list[dict] = field(default_factory=list)
    git_rm: list[str] = field(default_factory=list)
    copied_count: int = 0
    repointed_count: int = 0


# ─── pure core ────────────────────────────────────────────────────────────────


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_bytes(record: dict) -> bytes:
    """The single on-disk serialisation used for every write + every sha256, so
    a record's hash is stable across copy and reverse."""
    return json.dumps(record, indent=2).encode("utf-8")


def _sha256(record: dict) -> str:
    return hashlib.sha256(_canonical_bytes(record)).hexdigest()


def _ulid_of(entity_id: str) -> str:
    return entity_id.rsplit(":", 1)[-1]


def _write_if_changed(dest: Path, payload: bytes) -> bool:
    """Write `payload` to `dest` only when absent or its bytes differ.

    Returns True iff a write happened. This is the merge-not-collide /
    idempotent-write primitive shared by the record copy, the product merge, and
    the label move — a second run is a no-op because the bytes already match.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.read_bytes() == payload:
        return False
    dest.write_bytes(payload)
    return True


def _edge_rewrite_row(*, from_id: str, to_id: str) -> dict:
    """The manifest's edge-rewrite descriptor (single shape for plan + execute)."""
    return {"field": _EDGE_FIELD, "from": from_id, "to": to_id}


def compute_migration_set(
    src_instances: Path, *, retiree_product_id: str
) -> list[MigrationEntry]:
    """The records that move, relative to `src_instances`.

    All of `product-development/*` EXCEPT the retired product file (it is merged
    onto the survivor, not copied), plus `foundation/tenant`. The shared library
    (`foundation/workflow|step|tool`) is never included.
    """
    entries: list[MigrationEntry] = []
    retiree_ulid = _ulid_of(retiree_product_id)

    pd_root = src_instances / _PRODUCT_DEV
    if pd_root.is_dir():
        for f in sorted(pd_root.rglob("*.jsonld")):
            # skip the retired product file
            if f.parent.name == _PRODUCT_TYPE and f.stem == retiree_ulid:
                continue
            entries.append(_entry(src_instances, f))

    for etype in _FOUNDATION_MIGRATES:
        d = src_instances / _FOUNDATION / etype
        if d.is_dir():
            for f in sorted(d.glob("*.jsonld")):
                entries.append(_entry(src_instances, f))

    return entries


def _entry(src_instances: Path, f: Path) -> MigrationEntry:
    rel = f.relative_to(src_instances).as_posix()
    entity_id = _read_json(f).get("id", "")
    return MigrationEntry(rel_path=rel, src=f, entity_id=str(entity_id))


def _repoint(record: dict, *, retiree_id: str, survivor_id: str) -> tuple[dict, bool]:
    """Rewrite the record's `for_product` edge retiree→survivor.

    Returns `(record, rewritten)`. Idempotent: a record already pointing at the
    survivor (or carrying no such edge) is returned unchanged with
    `rewritten=False`.
    """
    if record.get(_EDGE_FIELD) == retiree_id:
        out = dict(record)
        out[_EDGE_FIELD] = survivor_id
        return out, True
    return record, False


def _merge_product_metadata(survivor: dict, retiree: dict) -> dict:
    """Carry retiree-only fields ONTO the survivor without overwriting any field
    the survivor already defines (the survivor's identity wins). ADR-002 step 3.
    """
    out = dict(survivor)
    for k, v in retiree.items():
        if k == "id":
            continue  # never adopt the retiree's identity
        if k not in out:
            out[k] = v
    return out


# ─── manifest (dry-run) ──────────────────────────────────────────────────────


def _plan_records(
    src_instances: Path,
    dest_instances: Path,
    *,
    survivor_id: str,
    retiree_id: str,
) -> list[dict]:
    """Per-record manifest rows: source path, dest path, id, src sha256, and the
    planned edge rewrite (None when the record carries no retiree edge)."""
    rows: list[dict] = []
    for e in compute_migration_set(src_instances, retiree_product_id=retiree_id):
        record = _read_json(e.src)
        _, will_rewrite = _repoint(record, retiree_id=retiree_id, survivor_id=survivor_id)
        rows.append(
            {
                "id": e.entity_id,
                "rel_path": e.rel_path,
                "src": str(e.src),
                "dest": str(dest_instances / e.rel_path),
                "src_sha256": _sha256(record),
                "edge_rewrite": (
                    _edge_rewrite_row(from_id=retiree_id, to_id=survivor_id)
                    if will_rewrite
                    else None
                ),
            }
        )
    return rows


def build_manifest(
    *,
    src_brain_root: Path,
    dest_brain_root: Path,
    survivor_product_id: str,
    retiree_product_id: str,
    manifest_path: Path | None = None,
) -> list[dict]:
    """Compute the migration plan + reversibility manifest. Mutates NOTHING.

    Returns the per-record manifest rows. When `manifest_path` is given, writes
    the full manifest (records + product merge + label move) to that path.
    """
    src_instances = src_brain_root / "instances"
    dest_instances = dest_brain_root / "instances"
    rows = _plan_records(
        src_instances, dest_instances,
        survivor_id=survivor_product_id, retiree_id=retiree_product_id,
    )

    if manifest_path is not None:
        label_src = roadmap_sidecar_path(src_brain_root)
        manifest = {
            "two_products": "merge",
            "survivor": survivor_product_id,
            "retiree": retiree_product_id,
            "records": rows,
            "product_merge": {
                "survivor": survivor_product_id,
                "retiree": retiree_product_id,
                "retiree_src": str(
                    src_instances / _PRODUCT_DEV / _PRODUCT_TYPE
                    / f"{_ulid_of(retiree_product_id)}.jsonld"
                ),
            },
            "label_move": (
                {
                    "src": str(label_src),
                    "dest": str(roadmap_sidecar_path(dest_brain_root)),
                }
                if label_src.exists()
                else None
            ),
        }
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return rows


# ─── execute ──────────────────────────────────────────────────────────────────


def migrate(
    *,
    src_brain_root: Path,
    dest_brain_root: Path,
    survivor_product_id: str,
    retiree_product_id: str,
    two_products: str,
) -> MigrationResult:
    """Copy the migration set into central, re-point edges onto the survivor,
    merge the retiree product metadata onto the survivor, and return the result
    (manifest + git-rm set). The `--execute` path.

    `two_products` MUST be the explicit policy string `"merge"` (ADR-002); any
    other value raises — the policy is never guessed.
    """
    if two_products != "merge":
        raise ValueError(
            f"unsupported --two-products policy {two_products!r}; only 'merge' "
            "is implemented (ADR-002)"
        )

    src_instances = src_brain_root / "instances"
    dest_instances = dest_brain_root / "instances"
    result = MigrationResult()

    for e in compute_migration_set(src_instances, retiree_product_id=retiree_product_id):
        record = _read_json(e.src)
        src_sha = _sha256(record)
        rewritten, did_rewrite = _repoint(
            record, retiree_id=retiree_product_id, survivor_id=survivor_product_id
        )
        dest = dest_instances / e.rel_path

        copied_now = not dest.exists()
        _write_if_changed(dest, _canonical_bytes(rewritten))
        if copied_now:
            result.copied_count += 1
        if did_rewrite and copied_now:
            result.repointed_count += 1

        result.manifest.append(
            {
                "id": e.entity_id,
                "rel_path": e.rel_path,
                "src": str(e.src),
                "dest": str(dest),
                "src_sha256": src_sha,
                "edge_rewrite": (
                    _edge_rewrite_row(
                        from_id=retiree_product_id, to_id=survivor_product_id
                    )
                    if did_rewrite
                    else None
                ),
            }
        )
        result.git_rm.append(str(e.src))

    # merge retiree product metadata onto the survivor (no second product written)
    _execute_product_merge(
        src_instances, dest_instances,
        survivor_id=survivor_product_id, retiree_id=retiree_product_id,
        result=result,
    )

    # move the roadmap label sidecar (idempotent overwrite)
    _execute_label_move(src_brain_root, dest_brain_root, result=result)

    return result


def _execute_product_merge(
    src_instances: Path,
    dest_instances: Path,
    *,
    survivor_id: str,
    retiree_id: str,
    result: MigrationResult,
) -> None:
    retiree_file = (
        src_instances / _PRODUCT_DEV / _PRODUCT_TYPE
        / f"{_ulid_of(retiree_id)}.jsonld"
    )
    survivor_file = (
        dest_instances / _PRODUCT_DEV / _PRODUCT_TYPE
        / f"{_ulid_of(survivor_id)}.jsonld"
    )
    if not retiree_file.exists():
        return
    retiree = _read_json(retiree_file)
    survivor = _read_json(survivor_file) if survivor_file.exists() else {"id": survivor_id}
    merged = _merge_product_metadata(survivor, retiree)
    _write_if_changed(survivor_file, _canonical_bytes(merged))
    # the retiree product file is removed from the repo (never written centrally)
    result.git_rm.append(str(retiree_file))


def _execute_label_move(
    src_brain_root: Path, dest_brain_root: Path, *, result: MigrationResult
) -> None:
    src = roadmap_sidecar_path(src_brain_root)
    if not src.exists():
        return
    dest = roadmap_sidecar_path(dest_brain_root)
    _write_if_changed(dest, src.read_bytes())
    result.git_rm.append(str(src))


# ─── reverse (by manifest entry) ─────────────────────────────────────────────


def reverse_record(entry: dict) -> dict:
    """Reconstruct one record from a manifest entry, restoring its ORIGINAL
    `for_product` edge (the retiree id). The dest record currently points at the
    survivor; reversing un-does the rewrite so the bytes match `src_sha256`.
    """
    dest = Path(entry["dest"])
    record = _read_json(dest)
    rewrite = entry.get("edge_rewrite")
    if rewrite:
        record = dict(record)
        record[rewrite["field"]] = rewrite["from"]
    return record


# ─── CLI ──────────────────────────────────────────────────────────────────────


def _resolve_brain_root(repo_root: Path) -> Path:
    """The `.brain/` root for `repo_root` (parent of the instances dir resolved
    by `brain_base_dir`). Imported lazily so the pure core has no dependency on
    the location resolver."""
    from _brain_location import brain_base_dir

    return brain_base_dir(repo_root).parent


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="migrate_dogfood_to_central.py",
        description=(
            "Move the repo's dogfood Brain records into the central brain, merge "
            "the two products into one (ADR-002), and report files to git rm."
        ),
    )
    parser.add_argument(
        "--repo-root", type=Path, default=Path.cwd(),
        help="repo root whose .brain/ holds the records to migrate (default: cwd)",
    )
    parser.add_argument(
        "--two-products", required=True, choices=["merge"],
        help="two-products resolution policy (ADR-002). No default; never guessed.",
    )
    parser.add_argument(
        "--survivor-product-id", required=True,
        help="the canonical CENTRAL product id that survives (e.g. dna:product:...)",
    )
    parser.add_argument(
        "--retiree-product-id", required=True,
        help="the REPO product id that is retired (merged onto the survivor)",
    )
    parser.add_argument(
        "--manifest", type=Path, default=None,
        help="where to write the reversibility manifest (dry-run default: stdout summary)",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run", dest="execute", action="store_false",
        help="compute the set + write the manifest; mutate nothing (DEFAULT)",
    )
    mode.add_argument(
        "--execute", dest="execute", action="store_true",
        help="perform the copy + edge rewrites; print the git-rm set",
    )
    parser.set_defaults(execute=False)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    repo_root = Path(args.repo_root).resolve()
    src_brain_root = repo_root / ".brain"
    dest_brain_root = _resolve_brain_root(repo_root)

    if not args.execute:
        rows = build_manifest(
            src_brain_root=src_brain_root,
            dest_brain_root=dest_brain_root,
            survivor_product_id=args.survivor_product_id,
            retiree_product_id=args.retiree_product_id,
            manifest_path=args.manifest,
        )
        rewrites = sum(1 for r in rows if r.get("edge_rewrite"))
        print(json.dumps(
            {
                "mode": "dry-run",
                "records": len(rows),
                "edge_rewrites": rewrites,
                "manifest": str(args.manifest) if args.manifest else None,
                "dest_brain_root": str(dest_brain_root),
            },
            indent=2,
        ))
        return 0

    result = migrate(
        src_brain_root=src_brain_root,
        dest_brain_root=dest_brain_root,
        survivor_product_id=args.survivor_product_id,
        retiree_product_id=args.retiree_product_id,
        two_products=args.two_products,
    )
    if args.manifest is not None:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(result.manifest, indent=2), encoding="utf-8")
    print(json.dumps(
        {
            "mode": "execute",
            "copied": result.copied_count,
            "repointed": result.repointed_count,
            "git_rm": result.git_rm,
        },
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
