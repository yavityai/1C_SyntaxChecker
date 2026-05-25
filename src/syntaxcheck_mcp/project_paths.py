from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULT_BSL_VERSION = "0.29.0"
DEFAULT_SYNTAXCHECK_PORT = 8010


def find_project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent
    for candidate in [current, *current.parents]:
        if (candidate / "pyproject.toml").exists() or (candidate / "bsl.version").exists():
            return candidate
    raise FileNotFoundError("Project root not found (expected pyproject.toml or bsl.version)")


def bsl_version_file(root: Path | None = None) -> Path:
    return find_project_root(root) / "bsl.version"


def env_file(root: Path | None = None) -> Path:
    return find_project_root(root) / ".env"


def env_example_file(root: Path | None = None) -> Path:
    return find_project_root(root) / ".env.example"


def vendor_jar_path(root: Path | None = None) -> Path:
    return find_project_root(root) / "vendor" / "bsl-language-server.jar"
