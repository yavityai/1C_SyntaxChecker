from mcp.server.fastmcp import FastMCP

from .bsl_runner import BslAnalyzeError, analyze_code
from .report_parser import filter_diagnostics, format_response

mcp = FastMCP(
    "1C BSL Syntax Checker",
    stateless_http=True,
    json_response=True,
)


@mcp.tool()
def syntaxcheck(code: str, min_severity: str = "HINT") -> dict:
    """Check 1C (BSL) code syntax and style using BSL Language Server.

    Args:
        code: BSL source code to analyze.
        min_severity: Lowest severity to report. One of ERROR, WARNING,
            INFORMATION, HINT (default HINT reports everything). Pass WARNING or
            ERROR to suppress stylistic noise for AI-generated code.

    Returns:
        A structured report with ``status``, per-severity ``summary`` counts,
        the filtered ``diagnostics`` list, and a human-readable ``summary_text``.
    """
    try:
        result = analyze_code(code)
    except BslAnalyzeError as exc:
        return {
            "status": "error",
            "error": str(exc),
            "summary": {"ERROR": 0, "WARNING": 0, "INFORMATION": 0, "HINT": 0},
            "diagnostics": [],
        }

    report = filter_diagnostics(result.summary, min_severity)
    report["summary_text"] = format_response(report, include_json=False)
    if result.stderr:
        report["stderr"] = result.stderr
    return report
