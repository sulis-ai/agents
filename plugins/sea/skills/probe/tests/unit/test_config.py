"""Unit tests for probe/config.py — verify constants are consistent."""

from __future__ import annotations

from probe import config


def test_all_required_tools_have_versions():
    """Every TOOL_REQUIRED has an entry in TOOL_VERSION_MIN."""
    for tool in config.TOOL_REQUIRED:
        assert tool in config.TOOL_VERSION_MIN, f"{tool} missing from TOOL_VERSION_MIN"


def test_phase_files_keys_are_string_phase_ids():
    """PHASE_FILES keys are phase strings like '1.1'."""
    for phase in config.PHASE_FILES:
        assert "." in phase
        major, minor = phase.split(".")
        assert major.isdigit() and minor.isdigit()


def test_phase_files_all_distinct():
    """Each phase has a unique output filename."""
    names = list(config.PHASE_FILES.values())
    assert len(names) == len(set(names))


def test_astgrep_base_flags_include_no_ignore_hidden():
    """v0.7.2 fix — orchestrator must always pass --no-ignore hidden/dot."""
    flags = config.ASTGREP_BASE_FLAGS
    assert "--no-ignore" in flags
    assert "hidden" in flags
    assert "dot" in flags


def test_python_capability_patterns_are_bare_keywords():
    """v0.7.2 Bug 5 — Python uses bare keywords (class/def), not 'class $NAME:'."""
    patterns = config.ASTGREP_CAPABILITY_PATTERNS["python"]
    pattern_texts = [p for _, p in patterns]
    assert "class" in pattern_texts
    assert "def" in pattern_texts
    # Make sure we DON'T use the broken patterns
    for p in pattern_texts:
        assert ":" not in p, f"Python pattern {p!r} contains ':' — would AST-error"
        assert "$NAME" not in p, f"Python pattern {p!r} uses $NAME — would AST-error"


def test_lizard_exclude_globs_include_venv():
    """v0.7.2 Bug 6 — lizard exclusions must include .venv and site-packages."""
    globs = config.LIZARD_EXCLUDE_GLOBS
    assert any("venv" in g for g in globs)
    assert any("site-packages" in g for g in globs)
    assert any("node_modules" in g for g in globs)


def test_lizard_help_marker_distinguishes_compression_tool():
    """v0.7.1 Bug 1 — the McCabe lizard says 'Cyclomatic Complexity'."""
    assert "cyclomatic complexity" in config.LIZARD_HELP_MARKER.lower()


def test_monorepo_manifests_include_major_styles():
    """Cover the styles documented in the plan."""
    styles = {style for _, style in config.MONOREPO_MANIFESTS}
    for required in ("pnpm", "lerna", "nx", "turborepo", "cargo",
                     "maven", "gradle", "bazel", "rush", "go-workspaces"):
        assert required in styles, f"{required} not in MONOREPO_MANIFESTS"


def test_lizard_base_flags_use_correct_options():
    """v0.7.1 Bug 3 — verify --CCN and -L are used, NOT bogus -E flags."""
    flags = config.LIZARD_BASE_FLAGS
    assert "--CCN" in flags
    assert "-L" in flags
    assert "-w" in flags
    # Bogus flags MUST NOT be present
    for i, flag in enumerate(flags):
        if flag == "-E":
            # If -E is present, must not be followed by "sloc" or "maxcc"
            next_val = flags[i + 1] if i + 1 < len(flags) else ""
            assert next_val not in ("sloc", "maxcc"), f"Bogus lizard flag detected: -E {next_val}"
