import json
from pathlib import Path
from typing import Any


SEVERITY_ORDER = {"ERROR": 0, "WARNING": 1, "INFORMATION": 2, "HINT": 3, "INFO": 2}


def _normalize_severity(value: Any) -> str:
    if value is None:
        return "INFORMATION"
    text = str(value).upper()
    if text in {"WARN", "WARNING"}:
        return "WARNING"
    if text in {"INFO", "INFORMATION"}:
        return "INFORMATION"
    if text in {"ERROR", "HINT"}:
        return text
    return text


def _extract_diagnostics(node: Any, file_hint: str | None, out: list[dict[str, Any]]) -> None:
    if isinstance(node, dict):
        if "message" in node and any(k in node for k in ("line", "range", "severity", "code")):
            line = node.get("line")
            character = node.get("character")
            range_obj = node.get("range")
            if range_obj and isinstance(range_obj, dict):
                start = range_obj.get("start") or {}
                line = start.get("line", line)
                character = start.get("character", character)
            out.append(
                {
                    "file": node.get("file") or node.get("path") or file_hint or "Module.bsl",
                    "line": (int(line) + 1) if isinstance(line, int) else line,
                    "character": (int(character) + 1) if isinstance(character, int) else character,
                    "severity": _normalize_severity(node.get("severity")),
                    "code": node.get("code") or node.get("rule") or node.get("source"),
                    "message": str(node.get("message", "")),
                }
            )
        for key, value in node.items():
            hint = file_hint
            if key in {"file", "path", "filename"} and isinstance(value, str):
                hint = value
            _extract_diagnostics(value, hint, out)
    elif isinstance(node, list):
        for item in node:
            _extract_diagnostics(item, file_hint, out)


def _dedupe(diagnostics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    unique: list[dict[str, Any]] = []
    for item in diagnostics:
        key = (
            item.get("file"),
            item.get("line"),
            item.get("character"),
            item.get("severity"),
            item.get("code"),
            item.get("message"),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def load_reports(output_dir: Path) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    if not output_dir.exists():
        return diagnostics

    for json_file in sorted(output_dir.rglob("*.json")):
        try:
            payload = json.loads(json_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        _extract_diagnostics(payload, json_file.name, diagnostics)

    return _dedupe(diagnostics)


def build_summary(diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {"ERROR": 0, "WARNING": 0, "INFORMATION": 0, "HINT": 0}
    for item in diagnostics:
        severity = _normalize_severity(item.get("severity"))
        counts[severity] = counts.get(severity, 0) + 1

    sorted_items = sorted(
        diagnostics,
        key=lambda d: (
            SEVERITY_ORDER.get(_normalize_severity(d.get("severity")), 99),
            d.get("line") or 0,
            d.get("character") or 0,
        ),
    )

    return {
        "status": "error" if counts["ERROR"] > 0 else "success",
        "summary": counts,
        "diagnostics": sorted_items,
    }


def filter_diagnostics(summary: dict[str, Any], min_severity: str = "HINT") -> dict[str, Any]:
    """Return a copy of the summary keeping only diagnostics at or above min_severity.

    Severity threshold order: ERROR < WARNING < INFORMATION < HINT. The default
    ("HINT") keeps everything; pass "WARNING" or "ERROR" to suppress noise.
    Per-severity counts in ``summary`` are preserved (they reflect the full set).
    """
    threshold = SEVERITY_ORDER.get(_normalize_severity(min_severity), 3)
    filtered = [
        item
        for item in summary.get("diagnostics", [])
        if SEVERITY_ORDER.get(_normalize_severity(item.get("severity")), 99) <= threshold
    ]
    result = dict(summary)
    result["min_severity"] = _normalize_severity(min_severity)
    result["diagnostics"] = filtered
    return result


def format_response(summary: dict[str, Any], include_json: bool = True) -> str:
    lines = [
        f"Status: {summary['status']}",
        (
            "Counts: "
            f"errors={summary['summary']['ERROR']}, "
            f"warnings={summary['summary']['WARNING']}, "
            f"info={summary['summary']['INFORMATION']}, "
            f"hints={summary['summary']['HINT']}"
        ),
    ]

    for item in summary["diagnostics"][:50]:
        line = item.get("line")
        col = item.get("character")
        location = f"{item.get('file')}:{line}:{col}" if line is not None else str(item.get("file"))
        lines.append(
            f"[{item.get('severity')}] {location} {item.get('code') or ''} {item.get('message')}".rstrip()
        )

    if len(summary["diagnostics"]) > 50:
        lines.append(f"... and {len(summary['diagnostics']) - 50} more diagnostics")

    if include_json:
        lines.append("")
        lines.append(json.dumps(summary, ensure_ascii=False, indent=2))
    return "\n".join(lines)
