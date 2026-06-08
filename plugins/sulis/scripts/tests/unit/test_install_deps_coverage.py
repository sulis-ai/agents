"""The installer covers Sulis's OWN tool dependencies.

A skill that shells out to an external binary (e.g. `/sulis:index-specifications`
→ `yq`) is a Sulis-own dependency: if it isn't in the installer's audit/install
path, a user hits a hard runtime failure with no setup route. These tests pin the
two gaps the dependency audit found:

- `yq` (mikefarah's) — REQUIRED by index-specifications; the Debian-`apt` `yq` is a
  DIFFERENT tool with incompatible syntax, so the installer must NOT apt-install it.
- `testssl.sh` — used by the security review (DAT-02); optional + Docker-fallback,
  so it's audited (visible when missing) but never blocks.

Conditional toolchains of the project-under-test (node/pytest/eslint/go/cargo) are
deliberately NOT the installer's job — the plugin detects + degrades — so they're
not pinned here.
"""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[5]
_PLUGIN = _ROOT / "plugins" / "sulis"
_INSTALL = _PLUGIN / "scripts" / "install-sulis.sh"
_INDEX_SKILL = _PLUGIN / "skills" / "index-specifications" / "generate-index.sh"


def test_index_specifications_still_hard_requires_yq() -> None:
    # Guard: if this skill stops needing yq, the installer coverage below is moot.
    t = _INDEX_SKILL.read_text(encoding="utf-8")
    assert "command -v yq" in t, "index-specifications hard-requires yq; coverage must track it"


def test_installer_audits_yq() -> None:
    t = _INSTALL.read_text(encoding="utf-8")
    assert "yq" in t, "yq must be in the installer's audit list (index-specifications needs it)"


def test_installer_installs_mikefarah_yq_not_apt_yq() -> None:
    t = _INSTALL.read_text(encoding="utf-8")
    # macOS: brew's yq IS mikefarah's — correct to install.
    assert "brew install yq" in t, "macOS should install yq via brew (mikefarah's)"
    # Debian trap: `apt-get install -y yq` is the WRONG tool — must not be used.
    assert "apt-get install -y yq" not in t, "apt yq is a different tool; must not apt-install it"
    # And the right source is pointed to for non-brew platforms.
    assert "mikefarah/yq" in t, "non-brew platforms must point at the correct yq release"


def test_installer_audits_testssl() -> None:
    t = _INSTALL.read_text(encoding="utf-8")
    assert "testssl" in t, "testssl.sh should be audited in the code-health layer"


def test_yq_is_optional_not_blocking() -> None:
    # yq backs a niche skill; absence must not fail the whole install (audit-only block).
    t = _INSTALL.read_text(encoding="utf-8")
    assert "yq|optional|" in t, "yq must be optional (audited, never blocks the install)"
