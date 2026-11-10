from mcp.server.fastmcp import FastMCP

from .bsl_runner import (
    AnalyzeResult,
    BslAnalyzeError,
    analyze_code,
    analyze_file,
    analyze_files,
    format_code,
    list_rules,
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
    """Check several 1C (BSL) files together, preserving their source paths.

    Only source contents are supplied, without configuration XML metadata.
    This does not guarantee resolution of metadata objects or module calls.

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


@mcp.tool()
def bsl_list_rules(language: str = "en", filter: str | None = None) -> dict:
    """List the BSL Language Server diagnostics (rules) this server can report.

    Useful for discovering rule codes to tune ``min_severity`` expectations or to
    look up what a diagnostic code means. Reads metadata from the bundled engine,
    so no analysis run is needed.

    Args:
        language: Display language for rule names/messages: 'en' or 'ru'.
        filter: Optional case-insensitive substring matched against a rule's code
            or name (e.g. 'naming', 'transaction', 'Query').

    Returns:
        ``{"status", "count", "rules"}`` where each rule is
        ``{"code", "name", "message"}``.
    """
    try:
        rules = list_rules(language=language, filter=filter)
    except BslAnalyzeError as exc:
        return {"status": "error", "error": str(exc), "count": 0, "rules": []}
    return {"status": "ok", "count": len(rules), "rules": rules}


@mcp.tool()
def bsl_format_code(code: str) -> dict:
    """Format a 1C (BSL) code snippet with BSL Language Server's formatter.

    Applies canonical indentation and spacing. Handy for cleaning up
    AI-generated code before committing it.

    Args:
        code: BSL source code to format.

    Returns:
        ``{"status", "formatted"}`` with the reformatted source, or an
        ``{"status": "error", "error"}`` report on failure.
    """
    try:
        formatted = format_code(code)
    except BslAnalyzeError as exc:
        return {"status": "error", "error": str(exc), "formatted": code}
    return {"status": "ok", "formatted": formatted}
