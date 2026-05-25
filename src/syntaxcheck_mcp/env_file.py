from pathlib import Path

from .project_paths import DEFAULT_SYNTAXCHECK_PORT, env_example_file, env_file


def read_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"')
        values[key] = value
    return values


def write_dotenv_key(path: Path, key: str, value: str, *, create_from_example: Path | None = None) -> None:
    if not path.exists():
        if create_from_example and create_from_example.exists():
            path.write_text(create_from_example.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            path.write_text("", encoding="utf-8")

    lines = path.read_text(encoding="utf-8").splitlines()
    updated = False
    result: list[str] = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            result.append(f"{key}={value}")
            updated = True
        else:
            result.append(line)
    if not updated:
        if result and result[-1].strip():
            result.append("")
        result.append(f"{key}={value}")
    path.write_text("\n".join(result) + "\n", encoding="utf-8")


def get_syntaxcheck_port(root: Path | None = None, override: int = 0) -> int:
    if override > 0:
        return override
    import os

    if os.environ.get("SYNTAXCHECK_PORT"):
        return int(os.environ["SYNTAXCHECK_PORT"])
    values = read_dotenv(env_file(root))
    if values.get("SYNTAXCHECK_PORT"):
        return int(values["SYNTAXCHECK_PORT"])
    return DEFAULT_SYNTAXCHECK_PORT


def get_mcp_url(root: Path | None = None, port_override: int = 0) -> str:
    port = get_syntaxcheck_port(root, override=port_override)
    return f"http://localhost:{port}/mcp"


def ensure_env_file(root: Path | None = None) -> Path:
    path = env_file(root)
    example = env_example_file(root)
    if not path.exists() and example.exists():
        path.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
    return path
