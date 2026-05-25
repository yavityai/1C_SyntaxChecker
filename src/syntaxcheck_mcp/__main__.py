from .config import MCP_HOST, MCP_PORT
from .server import mcp


def main() -> None:
    mcp.settings.host = MCP_HOST
    mcp.settings.port = MCP_PORT
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
