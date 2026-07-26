from mcp.server.fastmcp import FastMCP

from .bsl_runner import (
    AnalyzeResult,
    BslAnalyzeError,
    analyze_code,
    analyze_file,
    analyze_files,
    read_source_file,
)
from .report_parser import filter_diagnostics, format_response

mcp = FastMCP(
    "1C BSL Syntax Checker",
    stateless_http=True,
    json_response=True,
)


def _error_report(exc: Exception) -> dict:
    return {
        "status": "error",
        "error": str(exc),
        "summary": {"ERROR": 0, "WARNING": 0, "INFORMATION": 0, "HINT": 0},
        "diagnostics": [],
    }


def _build_report(result: AnalyzeResult, min_severity: str) -> dict:
    report = filter_diagnostics(result.summary, min_severity)
    report["summary_text"] = format_response(report, include_json=False)
    if result.stderr:
        report["stderr"] = result.stderr
    return report


@mcp.tool()
def syntaxcheck(code: str, min_severity: str = "HINT") -> dict:
    """Check a 1C (BSL) code snippet for syntax and style using BSL Language Server.

    Best for a standalone fragment. To get module-type-aware rules (naming
    conventions differ by module kind), prefer ``syntaxcheck_file``.

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
        return _error_report(exc)
    return _build_report(result, min_severity)


@mcp.tool()
def syntaxcheck_file(path: str, content: str | None = None, min_severity: str = "HINT") -> dict:
    """Check a single 1C (BSL) file, using its PATH for context.

    The path lets BSL Language Server infer the module type, so filename- and
    module-kind-aware rules apply correctly (e.g. naming conventions differ for
    a CommonModule vs an ObjectModule vs a ManagerModule).

    Args:
        path: File path inside your 1C configuration, e.g.
            'CommonModules/ОбщегоНазначения/Ext/Module.bsl'. May be relative;
            drive letters and '..' are stripped/rejected for safety.
        content: File source. If omitted, the server reads the file from ``path``
            on its own filesystem (works for local installs / mounted volumes;
            fails inside Docker — pass content explicitly there).
        min_severity: Lowest severity to report (ERROR, WARNING, INFORMATION,
            HINT). Default HINT reports everything.

    Returns:
        A structured report (see ``syntaxcheck``).
    """
    try:
        code = content if content is not None else read_source_file(path)
        result = analyze_file(path, code)
    except BslAnalyzeError as exc:
        return _error_report(exc)
    return _build_report(result, min_severity)


@mcp.tool()
def syntaxcheck_project(files: dict[str, str], min_severity: str = "HINT") -> dict:
    """Check several 1C (BSL) files together for cross-module diagnostics.

    Analyzing files as a set (rather than one at a time) lets BSL Language Server
    see the wider picture — useful for checking naming consistency and structure
    across a configuration.

    Args:
        files: Mapping of file path -> BSL source content. Paths should mirror
            your configuration layout, e.g.
            {'CommonModules/Util/Ext/Module.bsl': '<code>', ...}.
        min_severity: Lowest severity to report (ERROR, WARNING, INFORMATION,
            HINT). Default HINT reports everything.

    Returns:
        An aggregated structured report across all files. Each diagnostic keeps
        its ``file`` so you can map issues back to the source.
    """
    try:
        result = analyze_files(files)
    except BslAnalyzeError as exc:
        return _error_report(exc)
    return _build_report(result, min_severity)
