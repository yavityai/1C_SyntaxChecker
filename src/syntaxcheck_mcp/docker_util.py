import platform
import shutil
import subprocess


def docker_engine_ready() -> bool:
    if not shutil.which("docker"):
        return False
    result = subprocess.run(
        ["docker", "info"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def assert_docker_ready() -> None:
    if not shutil.which("docker"):
        raise RuntimeError(
            "Docker CLI not found.\n"
            "Install Docker Desktop: https://www.docker.com/products/docker-desktop/"
        )
    if docker_engine_ready():
        return

    system = platform.system().lower()
    if system == "windows":
        raise RuntimeError(
            "Docker Desktop is not running.\n"
            "Start Docker Desktop and wait until it reports Running, then retry."
        )
    raise RuntimeError(
        "Docker engine is not responding.\n"
        "Start Docker and verify with: docker info"
    )


def run_compose(args: list[str], *, cwd: str | None = None) -> None:
    assert_docker_ready()
    compose = shutil.which("docker")
    if compose is None:
        raise RuntimeError("docker not found")
    command = ["docker", "compose", *args]
    result = subprocess.run(command, cwd=cwd, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(command)}")
