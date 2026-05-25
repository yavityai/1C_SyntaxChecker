import os
from pathlib import Path


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


BSL_JAR = Path(os.environ.get("BSL_JAR", "/app/bsl-language-server.jar"))
BSL_CONFIG = Path(os.environ.get("BSL_CONFIG", "/app/bsl-language-server.json"))
BSL_MEMORY_MB = _int_env("BSL_MEMORY_MB", 2048)
BSL_ANALYZE_TIMEOUT_SEC = _int_env("BSL_ANALYZE_TIMEOUT_SEC", 120)

MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")
MCP_PORT = _int_env("MCP_PORT", 8002)
