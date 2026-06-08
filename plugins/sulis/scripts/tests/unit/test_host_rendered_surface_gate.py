"""Host-rendered surface contract — the "wired + legible" gate is wired in.

Structural pins over the live reference + standard + skills: a surface a host
renders for us (MCP App / OpenAI App / figma-plugin / browser-extension) is not
"done" when its HTML merely serves — it must be bound on both sides of the seam
AND observed in the real host AND legible (title + description + icon, not a bare
technical name). This is the recurring "looks built, isn't wired" failure (the
Cowork MCP-App that narrated tool data as text). These pins stop the gate prose
from silently rotting out of the design-walk + the contract standard.
"""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[5]
_REF = _ROOT / "plugins" / "sulis" / "references" / "mcp-ui-surface-patterns.md"
_CF = _ROOT / "plugins" / "sulis" / "references" / "standards" / "CONTRACT_FIRST_STANDARD.md"
_DRAFT = _ROOT / "plugins" / "sulis" / "skills" / "draft-architecture" / "SKILL.md"
_AUDIT = _ROOT / "plugins" / "sulis" / "skills" / "audit" / "SKILL.md"


def _text(p: Path) -> str:
    assert p.is_file(), f"missing {p}"
    return p.read_text(encoding="utf-8")


def test_reference_has_the_wired_and_legible_gate() -> None:
    t = _text(_REF)
    low = t.lower()
    assert "done = wired + legible" in low, "the reference must carry the fail-closed gate"
    # both sides of the seam + real-host observation
    assert "both" in low and ("real host" in low or "real-host" in low)
    # generalised beyond MCP-Apps (named instances)
    assert "openai" in low and ("figma" in low or "browser-extension" in low)
    # the MIME fix (host's actual value, not only the one we wrote down)
    assert "text/html+skybridge" in t or "text/html+mcp" in t
    # the legibility metadata bar
    assert "title" in low and "description" in low and "icon" in low


def test_contract_first_cf08_is_must_with_realhost_conformance() -> None:
    t = _text(_CF)
    low = t.lower()
    assert "host-rendered surface" in low
    assert "must when building" in low, "the host-render binding must be MUST-when-building"
    assert "real-host round-trip" in low, "CF-07 conformance named as the real-host round-trip"


def test_design_walk_sharpens_exists_for_host_rendered_hops() -> None:
    for p in (_DRAFT, _AUDIT):
        low = _text(p).lower()
        assert "host-rendered" in low and "integration hop" in low, f"{p} missing the sharper exists"
        assert "both" in low and "real host" in low
        # serving HTML alone is explicitly NOT exists
        assert "serv" in low and "gap" in low
