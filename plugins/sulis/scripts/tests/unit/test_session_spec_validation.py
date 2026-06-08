"""SessionSpec.resume_ref validation (SEC CONCERN-1, defence-in-depth).

resume_ref is an opaque caller-supplied provider handle that flows into argv
(Claude: ``--resume <ref>``). Argv-list construction already blocks shell /
separate-flag injection; this central seam guard rejects a leading ``-`` and
control characters so every adapter — current and future — inherits the
protection.
"""

from __future__ import annotations

import pytest

from _session_manager.adapter import SessionSpec


def test_resume_ref_none_is_allowed() -> None:
    spec = SessionSpec(provider="claude", cwd="/tmp", resume_ref=None)
    assert spec.resume_ref is None


def test_normal_resume_ref_is_allowed() -> None:
    spec = SessionSpec(
        provider="claude", cwd="/tmp", resume_ref="01JABCDEF0123456789SESSION"
    )
    assert spec.resume_ref == "01JABCDEF0123456789SESSION"


def test_resume_ref_leading_dash_is_rejected() -> None:
    with pytest.raises(ValueError, match="must not start with '-'"):
        SessionSpec(provider="claude", cwd="/tmp", resume_ref="--dangerous-flag")


def test_resume_ref_newline_is_rejected() -> None:
    with pytest.raises(ValueError, match="control characters"):
        SessionSpec(provider="claude", cwd="/tmp", resume_ref="abc\ndef")


def test_resume_ref_other_control_char_is_rejected() -> None:
    with pytest.raises(ValueError, match="control characters"):
        SessionSpec(provider="claude", cwd="/tmp", resume_ref="abc\x00def")
