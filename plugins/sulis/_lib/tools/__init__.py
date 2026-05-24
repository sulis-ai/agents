"""Shared tool-integration layer for sulis check-* skills.

Per SPIRAL_TEMPLATES.md Codebase Referential Integrity dimension: every tool
declared in a skill's `verification_spiral.custom_dimensions` must trace to a
wrapper here. NEW entities must be explicitly flagged in VERIFICATION_REPORT.md.

Wrappers follow the contract:

- Detection: `is_available() -> ToolMode` returns DOCKER / NATIVE / NOT_AVAILABLE
- Invocation: `run(...) -> ToolResult` with stdout / stderr / exit_code /
  mode_used / version
- Degradation: never silent regex fallback. NOT_AVAILABLE means NOT_ASSESSED
  in the skill's primitive coverage; the founder sees this in their
  VERIFICATION_REPORT.md and code-health output.
"""

from ._detection import ToolMode, docker_available, native_available, tool_available
from ._runner import ToolResult, run_tool

__all__ = [
    "ToolMode",
    "ToolResult",
    "docker_available",
    "native_available",
    "run_tool",
    "tool_available",
]
