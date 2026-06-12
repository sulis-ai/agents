"""Change-manifest → Change-entity emission (#128, DR-031).

A change already carries its identity in the manifest (`.changes/*.yaml` +
the local change record): change_id (ULID), handle, slug, primitive, intent,
branch, base_sha, started_at, and — when spawned from a parent — parent_change
+ relationship. This turns that manifest into the canonical **Change** entity
(a prov:Activity, sibling to LifecycleRun) and writes it through the
`EntityRepository` port, so a change becomes a first-class node in the brain
rather than a file beside it.

The entity id REUSES the manifest ULID (`dna:change:{change_id}`) — same change,
same id, idempotent (a re-emit overwrites in place; never a duplicate). Pure
`compose_change` (no I/O) + `emit_change` (saves via the repo). `for_product`
resolves from the repo's Product instance.

Deliberately NOT carried onto the entity (machine-local session state, per the
FIELD-SPEC §3 / JT-6 portability gate): worktree_path, pid, tty, session.json.
"""

from __future__ import annotations

import json
from pathlib import Path

from _entity_repository import EntityRepository


def compose_change(
    *,
    change_id: str,
    handle: str,
    slug: str,
    intent: str,
    primitive: str,
    started_at: str,
    for_product: str | None = None,
    state: str = "in-flight",
    parent_change: str | None = None,
    relationship: str | None = None,
    base_sha: str | None = None,
    branch: str | None = None,
    by_actor: str | None = None,
    shipped_at: str | None = None,
    confidence: float | None = None,
) -> dict:
    """Pure transform: manifest fields → a Change entity dict. No I/O.

    `change_id` is the bare ULID from the manifest; the entity id is
    `dna:change:{change_id}`. Optional fields are OMITTED when None (never set
    to null) to keep `unevaluatedProperties:false` clean — mirrors
    `_opportunity_emission._opportunity_dict`.
    """
    change: dict = {
        "id": f"dna:change:{change_id}",
        "handle": handle,
        "slug": slug,
        "intent": " ".join(str(intent).split()),
        "primitive": primitive,
        "state": state,
        "started_at": started_at,
        "sys_status": "active",
    }
    # for_product is an OPTIONAL link — a change can precede or sit outside a
    # product (infra / methodology work, or the change that creates the first
    # product). Omitted when absent, never set to null.
    if for_product:
        change["for_product"] = for_product
    # parent_change + relationship travel together (the #123/#124 carry); a
    # relationship without a parent is meaningless, so gate it on the parent.
    if parent_change:
        change["parent_change"] = parent_change
        change["relationship"] = relationship or "builds_on"
    if base_sha:
        change["base_sha"] = base_sha
    if branch:
        change["branch"] = branch
    if by_actor:
        change["by_actor"] = by_actor
    # Invariant: an in-flight change has NOT shipped — never carry shipped_at on
    # it (a shipped_at + state=in-flight is a semantic contradiction, even though
    # the schema would accept both fields). Enforced here for every caller.
    if shipped_at and state != "in-flight":
        change["shipped_at"] = shipped_at
    if confidence is not None:
        change["confidence"] = confidence
    return change


def resolve_for_product(repo_root: Path) -> str | None:
    """The Product id this repo's changes contribute to.

    Reads `.brain/instances/product-development/product/*.jsonld`. Returns the
    single product's id when exactly one exists (the common case — one repo,
    one product); None when zero or many (the caller decides — never guess
    between several products). Best-effort: any read error → None.
    """
    product_dir = repo_root / ".brain" / "instances" / "product-development" / "product"
    if not product_dir.is_dir():
        return None
    ids: list[str] = []
    for f in sorted(product_dir.glob("*.jsonld")):
        try:
            pid = json.loads(f.read_text(encoding="utf-8")).get("id")
        except (ValueError, OSError):
            continue
        if isinstance(pid, str) and pid:
            ids.append(pid)
    return ids[0] if len(ids) == 1 else None


def emit_change(
    record: dict,
    repo: EntityRepository,
    *,
    for_product: str | None = None,
) -> dict:
    """Compose a Change entity from a change manifest/record dict and save it.

    `for_product` is taken from the argument when given, else the record's
    `for_product`, else omitted — it is an OPTIONAL link, so a product-less
    change still becomes a Change entity (just without the product edge).
    Returns the saved entity dict.
    """
    fp = for_product or record.get("for_product")
    # Derive state when the record doesn't carry one (manifests don't today):
    # a record with a shipped_at is a shipped change, else in-flight. This keeps
    # a backfilled historical (shipped) change consistent instead of emitting it
    # as in-flight. The fresh-start wiring passes state="in-flight" explicitly.
    state = record.get("state") or ("shipped" if record.get("shipped_at") else "in-flight")
    # started_at is required; fall back through the record's other timestamps so
    # an older record (null started_at) still emits a real time rather than "".
    started_at = (record.get("started_at") or record.get("created_at")
                  or record.get("shipped_at") or "")
    change = compose_change(
        change_id=str(record["change_id"]),
        handle=str(record.get("handle") or ""),
        slug=str(record.get("slug") or ""),
        intent=str(record.get("intent") or ""),
        primitive=str(record.get("primitive") or ""),
        for_product=fp,
        started_at=str(started_at),
        state=str(state),
        parent_change=record.get("parent_change"),
        relationship=record.get("relationship"),
        base_sha=record.get("base_sha"),
        branch=record.get("branch"),
        by_actor=record.get("by_actor"),
        shipped_at=record.get("shipped_at"),
    )
    repo.save("change", change)
    return change
