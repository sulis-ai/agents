"""Tool availability detection — Docker preferred, native binary fallback.

Per the degradation policy: tools that have neither Docker nor a native binary
report NOT_ASSESSED in the calling skill's primitive coverage. There is no
silent regex fallback — the founder sees explicitly which primitives could not
be checked.
"""

from __future__ import annotations

import shutil
import subprocess
from enum import Enum
from functools import lru_cache


class ToolMode(Enum):
    """How a tool is invoked. Returned by `tool_available`."""

    DOCKER = "docker"
    NATIVE = "native"
    NOT_AVAILABLE = "not_available"


@lru_cache(maxsize=1)
def docker_available() -> bool:
    """Return True if `docker` is on PATH and the daemon responds.

    Cached because we may check repeatedly within one skill run. The cache is
    process-scoped so daemon-start during the run isn't detected — acceptable
    for the analysis-skill use case.
    """
    if shutil.which("docker") is None:
        return False
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=5,
            check=False,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def native_available(binary: str) -> bool:
    """Return True if `binary` is on PATH."""
    return shutil.which(binary) is not None


def tool_available(
    tool_name: str,
    *,
    native_binary: str | None = None,
    docker_image: str | None = None,
) -> ToolMode:
    """Resolve preferred invocation mode for a tool.

    Args:
        tool_name: logical name (used in REFERENCE.md catalogue)
        native_binary: PATH-discoverable binary name. If None, defaults to
            tool_name. Pass explicitly when the tool name differs from its
            binary (e.g., tool="testssl", native_binary="testssl.sh").
        docker_image: Docker image tag (e.g., "returntocorp/semgrep:latest").
            If None, Docker invocation is not considered — the caller has
            opted out of Docker for this tool.

    Returns:
        ToolMode.DOCKER if docker_image was specified AND Docker daemon is up
        (preferred — clean environment + version pinning), ToolMode.NATIVE if
        the native binary is on PATH and Docker is not preferred or available,
        ToolMode.NOT_AVAILABLE otherwise.
    """
    if docker_image is not None and docker_available():
        return ToolMode.DOCKER
    if native_available(native_binary or tool_name):
        return ToolMode.NATIVE
    return ToolMode.NOT_AVAILABLE
