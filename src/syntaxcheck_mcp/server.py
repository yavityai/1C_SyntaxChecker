from mcp.server.fastmcp import FastMCP

from .bsl_runner import BslAnalyzeError, analyze_code_text

mcp = FastMCP(
    "1C BSL Syntax Checker",
    stateless_http=True,
    json_response=True,
)


@mcp.tool()
def syntaxcheck(code: str) -> str:
    """Check 1C (BSL) code syntax and style using BSL Language Server.

    Args:
        code: BSL source code to analyze.

    Returns:
        Human-readable summary and JSON diagnostics report.
    """
    try:
        return analyze_code_text(code)
    except BslAnalyzeError as exc:
        return f"error: {exc}"
