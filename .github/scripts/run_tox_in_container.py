"""Run tox inside a Docker container for security isolation.

The agent can modify tox.ini, pyproject.toml, uv.lock, and test files.
Running tox directly on the runner would let injected commands execute with
GITHUB_TOKEN in the environment. This script runs tox inside a Docker container
based on a chiseled Ubuntu image (dotnet-deps) that has no shell, no Python,
and no coreutils — only the runtime libraries needed to run Python.

Python is bind-mounted from the host's uv-managed Python. A venv with tox and
tox-uv installed is bind-mounted as site-packages. The uv binary is bind-mounted
so tox-uv's runner can create venvs and install dependencies inside the container.

The charm directories are bind-mounted read-write so that ruff format changes
propagate back to the host automatically. libs/ is mounted read-only.

No secrets are passed into the container: no GITHUB_TOKEN, no OPENROUTER_API_KEY.
The container has no access to .git/ (only charm dirs and libs/ are mounted).
Even if the agent injected malicious commands into tox.ini, those commands run
inside the container without secrets and without access to the host filesystem.

Usage:
    uv run --script run_tox_in_container.py \
        --repo-root /path/to/repo \
        --charm-dir kepler \
        --tox-env format,lint,unit

Exit code is 0 if tox passed, 1 if it failed.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Chiseled Ubuntu image with only runtime libraries (glibc, libssl, libz,
# ca-certs). No shell, no coreutils, no Python — everything is bind-mounted.
# Borrowed from jjx (https://github.com/dwilding/jjx).
CONTAINER_IMAGE = "docker.io/ubuntu/dotnet-deps:8.0-24.04_stable"

CHARM_DIRS = ("kepler", "kosmos", "meteor", "micron")
LIBS_DIR = "libs"


# ---------------------------------------------------------------------------
# Host environment discovery
# ---------------------------------------------------------------------------


def find_uv_binary() -> str:
    """Find the uv binary on the host."""
    uv = shutil.which("uv")
    if uv is None:
        # Print PATH for debugging when uv isn't found.
        print(f"PATH={os.environ.get('PATH', '<not set>')}", file=sys.stderr)
        print(f"which docker: {shutil.which('docker')}", file=sys.stderr)
        raise RuntimeError("uv not found on PATH. Install uv first (setup-uv action).")
    return uv


def find_uv_python(version: str) -> Path:
    """Find the uv-managed Python directory for the given version.

    Installs the Python version first if it's not already available.
    """
    subprocess.run(
        ["uv", "python", "install", version],
        capture_output=True,
        text=True,
        check=False,
    )
    result = subprocess.run(
        ["uv", "python", "find", version],
        capture_output=True,
        text=True,
        check=True,
    )
    python_bin = Path(result.stdout.strip())
    if not python_bin.exists():
        raise RuntimeError(f"uv python find returned non-existent path: {python_bin}")
    python_dir = python_bin.parent.parent
    if not (python_dir / "bin").is_dir():
        raise RuntimeError(
            f"Could not find bin/ in uv Python installation: {python_dir}"
        )
    return python_dir


def python_bin_name(python_dir: Path) -> str:
    """Return the Python binary name (e.g. 'python3.10')."""
    for candidate in sorted((python_dir / "bin").iterdir()):
        if candidate.name.startswith("python3."):
            return candidate.name
    raise RuntimeError(f"Could not find python3.X binary in {python_dir / 'bin'}")


def create_tox_venv(*, uv_binary: str, python_version: str, venv_path: Path) -> Path:
    """Create a venv with tox and tox-uv. Return the site-packages path."""
    subprocess.run(
        [uv_binary, "venv", "--python", python_version, str(venv_path)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            uv_binary,
            "pip",
            "install",
            "--python",
            str(venv_path / "bin" / "python"),
            "tox",
            "tox-uv",
        ],
        check=True,
        capture_output=True,
    )
    site_packages = venv_path / "lib" / f"python{python_version}" / "site-packages"
    if not site_packages.is_dir():
        raise RuntimeError(f"site-packages not found at {site_packages}")
    return site_packages


# ---------------------------------------------------------------------------
# Container management
# ---------------------------------------------------------------------------


def start_container(
    *,
    container_name: str,
    python_dir: Path,
    py_bin_name: str,
    site_packages_dir: Path,
    uv_binary: str,
    repo_root: Path,
    libs_exists: bool,
) -> str:
    """Start the Docker container with bind mounts. Returns the container name."""
    # Check Docker is available before trying to use it.
    docker_check = subprocess.run(
        ["docker", "info"], capture_output=True, text=True, check=False
    )
    if docker_check.returncode != 0:
        docker_path = shutil.which("docker") or "<not found>"
        raise RuntimeError(
            f"Docker is not available (docker at {docker_path}, exit {docker_check.returncode}). "
            f"stderr: {docker_check.stderr.strip()}"
        )

    subprocess.run(
        ["docker", "rm", "-f", container_name], capture_output=True, check=False
    )

    mounts: list[str] = [
        f"{python_dir}:/python:ro",
        f"{site_packages_dir}:/venv:ro",
        f"{uv_binary}:/usr/local/bin/uv:ro",
    ]
    for charm_dir in CHARM_DIRS:
        host_path = repo_root / charm_dir
        if host_path.is_dir():
            mounts.append(f"{host_path}:/charm/{charm_dir}:rw")
    if libs_exists:
        mounts.append(f"{repo_root / LIBS_DIR}:/charm/{LIBS_DIR}:ro")

    cmd = [
        "docker",
        "run",
        "--rm",
        "--name",
        container_name,
        "-d",
        "--network",
        "bridge",
        "--tmpfs",
        "/tmp:mode=1777",
        "-e",
        "PYTHONPATH=/venv:/charm",
        "-e",
        "PATH=/usr/local/bin:/usr/bin:/bin",
        "-e",
        "UV_CACHE_DIR=/tmp/uv-cache",
        "-e",
        "UV_PYTHON_INSTALL_DIR=/tmp/uv-python",
        "-e",
        "TOX_WORK_DIR=/tmp/tox",
        "-e",
        "HOME=/tmp",
    ]
    for mount in mounts:
        cmd.extend(["-v", mount])
    cmd.append(CONTAINER_IMAGE)
    cmd.extend([f"/python/bin/{py_bin_name}", "-c", "import time; time.sleep(999999)"])

    subprocess.run(cmd, check=True, capture_output=True)
    return container_name


def exec_in_container(
    container_name: str,
    command: list[str],
    *,
    cwd: str | None = None,
    timeout: int = 600,
) -> tuple[int, str, str]:
    """Run a command inside the container via docker exec."""
    cmd = ["docker", "exec"]
    if cwd:
        cmd.extend(["-w", cwd])
    cmd.append(container_name)
    cmd.extend(command)
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"Command timed out after {timeout} seconds."


def stop_container(container_name: str) -> None:
    """Stop and remove the container."""
    subprocess.run(
        ["docker", "rm", "-f", container_name], capture_output=True, check=False
    )


# ---------------------------------------------------------------------------
# Tox execution
# ---------------------------------------------------------------------------


def run_tox_in_charm(
    *,
    container_name: str,
    charm_dir: str,
    tox_env: str,
    py_bin: str,
) -> tuple[int, str]:
    """Run uv lock + tox in one charm dir inside the container.

    Returns (exit_code, combined_output).
    """
    charm_path = f"/charm/{charm_dir}"
    all_output: list[str] = []
    failed = 0

    # uv lock regenerates the lockfile from pyproject.toml, overwriting any
    # tampering. Network is available (bridge) but no secrets are present.
    rc, stdout, stderr = exec_in_container(
        container_name, ["uv", "lock"], cwd=charm_path
    )
    all_output.append(f"=== uv lock in {charm_dir} ===")
    all_output.append(stdout)
    if stderr:
        all_output.append(stderr)
    if rc != 0:
        all_output.append(f"uv lock failed in {charm_dir} (exit {rc})")
        failed = 1
    else:
        all_output.append(f"uv lock succeeded in {charm_dir}")

    # tox runs format, lint, and/or unit tests using the locked dependencies.
    rc, stdout, stderr = exec_in_container(
        container_name, [py_bin, "-m", "tox", "-e", tox_env], cwd=charm_path
    )
    all_output.append(f"\n=== tox -e {tox_env} in {charm_dir} ===")
    all_output.append(stdout)
    if stderr:
        all_output.append(stderr)
    if rc != 0:
        all_output.append(f"tox -e {tox_env} failed in {charm_dir} (exit {rc})")
        failed = 1
    else:
        all_output.append(f"tox -e {tox_env} succeeded in {charm_dir}")

    return failed, "\n".join(all_output)


def run_tox(
    *,
    repo_root: Path,
    charm_dir: str,
    tox_env: str,
    container_suffix: str,
) -> int:
    """Run uv lock + tox for a single charm inside a container.

    Returns 0 if passed, 1 if failed.
    """
    try:
        uv_binary = find_uv_binary()
        py_dir = find_uv_python("3.10")
        py_name = python_bin_name(py_dir)

        with tempfile.TemporaryDirectory(prefix="tox-venv-") as venv_tmpdir:
            venv_path = Path(venv_tmpdir) / "venv"
            site_packages = create_tox_venv(
                uv_binary=uv_binary, python_version="3.10", venv_path=venv_path
            )

            libs_exists = (repo_root / LIBS_DIR).is_dir()
            container_name = f"probe-tox-{container_suffix}"

            try:
                start_container(
                    container_name=container_name,
                    python_dir=py_dir,
                    py_bin_name=py_name,
                    site_packages_dir=site_packages,
                    uv_binary=uv_binary,
                    repo_root=repo_root,
                    libs_exists=libs_exists,
                )
                failed, output = run_tox_in_charm(
                    container_name=container_name,
                    charm_dir=charm_dir,
                    tox_env=tox_env,
                    py_bin=f"/python/bin/{py_name}",
                )
            finally:
                stop_container(container_name)

        print(output)
        return failed
    except subprocess.CalledProcessError as e:
        detail = e.stderr or e.stdout or str(e)
        print(f"run_tox failed (exit {e.returncode}): {detail}", file=sys.stderr)
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"run_tox failed: {e}", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run tox inside a Docker container for security isolation."
    )
    parser.add_argument(
        "--repo-root", type=Path, required=True, help="Repository root path."
    )
    parser.add_argument("--charm-dir", required=True, help="Charm directory name.")
    parser.add_argument(
        "--tox-env", required=True, help="Tox environment(s), e.g. 'format,lint,unit'."
    )
    parser.add_argument(
        "--container-suffix", default="run", help="Suffix for the container name."
    )
    args = parser.parse_args(argv)

    if args.charm_dir not in CHARM_DIRS:
        print(
            f"Invalid charm dir: {args.charm_dir}. Must be one of: {', '.join(CHARM_DIRS)}"
        )
        return 1

    return run_tox(
        repo_root=args.repo_root,
        charm_dir=args.charm_dir,
        tox_env=args.tox_env,
        container_suffix=args.container_suffix,
    )


if __name__ == "__main__":
    sys.exit(main())
