"""Subprocess and container execution helpers.

All collectors are executed through :func:`run_command` so that stdout/stderr,
exit status, duration and timeouts are captured uniformly and never raise into
the orchestrator (modules must fail gracefully).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Sequence

DEFAULT_TIMEOUT = 600

DOCKER_VOLUME_ROOTS = (
    ("RAF_CONTAINER_OUTPUT_ROOT", "RAF_HOST_OUTPUT_ROOT"),
    ("RAF_CONTAINER_IMAGE_ROOT", "RAF_HOST_IMAGE_ROOT"),
)


@dataclass(slots=True)
class CommandResult:
    """Outcome of a single subprocess/container invocation."""

    command: List[str]
    returncode: int
    stdout: str = ""
    stderr: str = ""
    duration: float = 0.0
    timed_out: bool = False
    error: Optional[str] = None
    env_notes: Dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        """True when the process exited cleanly and did not time out."""
        return self.returncode == 0 and not self.timed_out and self.error is None

    @property
    def printable(self) -> str:
        """Shell-ish rendering of the command for the audit log."""
        return " ".join(self.command)


@lru_cache(maxsize=None)
def binary_available(name: str) -> bool:
    """Return True when ``name`` is an executable on PATH."""
    return shutil.which(name) is not None


@lru_cache(maxsize=1)
def docker_available() -> bool:
    """Return True when a usable Docker daemon is reachable."""
    if not binary_available("docker"):
        return False
    try:
        proc = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        return proc.returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


@lru_cache(maxsize=None)
def docker_image_available(image: str) -> bool:
    """Return True when an exact configured image is present locally."""
    if not image or not docker_available():
        return False
    try:
        proc = subprocess.run(
            ["docker", "image", "inspect", image],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        return proc.returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


def run_command(
    command: Sequence[str],
    timeout: int = DEFAULT_TIMEOUT,
    cwd: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
    stdin_data: Optional[str] = None,
) -> CommandResult:
    """Execute ``command`` capturing output; never raises.

    Args:
        command: Argument vector (never a shell string — no shell injection).
        timeout: Wall-clock limit in seconds.
        cwd: Working directory.
        env: Extra environment variables merged over ``os.environ``.
        stdin_data: Optional stdin payload.

    Returns:
        A :class:`CommandResult` describing the invocation.
    """
    argv = [str(part) for part in command]
    merged_env = {**os.environ, **(env or {})}
    started = time.monotonic()
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd) if cwd else None,
            env=merged_env,
            input=stdin_data,
            check=False,
        )
        return CommandResult(
            command=argv,
            returncode=proc.returncode,
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
            duration=round(time.monotonic() - started, 2),
        )
    except subprocess.TimeoutExpired as exc:
        return CommandResult(
            command=argv,
            returncode=124,
            stdout=_decode(exc.stdout),
            stderr=_decode(exc.stderr),
            duration=round(time.monotonic() - started, 2),
            timed_out=True,
            error=f"timed out after {timeout}s",
        )
    except FileNotFoundError:
        return CommandResult(
            command=argv,
            returncode=127,
            duration=round(time.monotonic() - started, 2),
            error=f"executable not found: {argv[0]}",
        )
    except OSError as exc:  # pragma: no cover - platform specific
        return CommandResult(
            command=argv,
            returncode=126,
            duration=round(time.monotonic() - started, 2),
            error=f"execution error: {exc}",
        )


def build_docker_command(
    image: str,
    args: Sequence[str],
    volumes: Optional[Dict[Path, str]] = None,
    workdir: Optional[str] = None,
    entrypoint: Optional[str] = None,
    network: str = "bridge",
    user: Optional[str] = None,
    read_only_root: bool = False,
    environment: Optional[Sequence[str]] = None,
) -> List[str]:
    """Compose a ``docker run`` argument vector for a collector container.

    Containers are ephemeral (``--rm``) and receive only the volumes needed to
    read inputs and write evidence.

    Args:
        image: Container image reference.
        args: Arguments passed to the container entrypoint.
        volumes: Mapping of host path -> container mount spec (``/data`` or ``/data:ro``).
        workdir: Container working directory.
        entrypoint: Override the image entrypoint.
        network: Docker network mode.
        user: ``uid:gid`` to avoid root-owned evidence files.
        read_only_root: Mount the container root filesystem read-only.
        environment: Environment variable names to forward without exposing values.

    Returns:
        The full ``docker run ...`` argument vector.
    """
    cmd: List[str] = ["docker", "run", "--rm", f"--network={network}"]
    if read_only_root:
        cmd.append("--read-only")
    if user:
        cmd += ["--user", user]
    for name in environment or ():
        if not name or not str(name).replace("_", "").isalnum():
            raise ValueError(f"invalid environment variable name: {name!r}")
        cmd += ["--env", str(name)]
    for host, target in (volumes or {}).items():
        host_path = Path(host)
        if not host_path.exists() and not host_path.suffix:
            host_path.mkdir(parents=True, exist_ok=True)
        source_path = docker_host_path(host_path)
        cmd += ["-v", f"{source_path}:{target}"]
    if workdir:
        cmd += ["-w", workdir]
    if entrypoint:
        cmd += ["--entrypoint", entrypoint]
    cmd.append(image)
    cmd += [str(a) for a in args]
    return cmd


def docker_host_path(path: Path) -> Path:
    """Translate an in-container bind path to the Docker daemon's host path.

    Mounting ``/var/run/docker.sock`` gives this application access to the host
    daemon, but that daemon cannot see paths such as ``/app/output`` inside the
    audit container. Compose supplies explicit container/host root pairs so
    sibling collectors write into the real engagement workspace.
    """
    resolved = Path(path).resolve()
    for container_env, host_env in DOCKER_VOLUME_ROOTS:
        container_value = os.environ.get(container_env)
        host_value = os.environ.get(host_env)
        if not container_value or not host_value:
            continue
        try:
            relative = resolved.relative_to(Path(container_value).resolve())
        except ValueError:
            continue
        return Path(host_value).resolve() / relative
    return resolved


def current_user_spec() -> Optional[str]:
    """Return ``uid:gid`` on POSIX so container output stays operator-owned."""
    if os.name != "posix":
        return None
    try:
        return f"{os.getuid()}:{os.getgid()}"
    except AttributeError:  # pragma: no cover - non-posix
        return None


def _decode(value: object) -> str:
    """Coerce subprocess buffers (bytes/str/None) into text."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)
