import json
from pathlib import Path

from syntaxcheck_mcp.report_parser import build_summary, format_response, load_reports


def test_build_summary_error_status():
    summary = build_summary(
        [
            {
                "file": "Module.bsl",
                "line": 2,
                "character": 5,
                "severity": "ERROR",
                "code": "ParseError",
                "message": "Unexpected token",
            }
        ]
    )
    assert summary["status"] == "error"
    assert summary["summary"]["ERROR"] == 1


def test_build_summary_success_status():
    summary = build_summary([])
    assert summary["status"] == "success"


def test_load_reports_from_json_file(tmp_path: Path):
    payload = {
        "issues": [
            {
                "file": "Module.bsl",
                "line": 0,
                "character": 0,
                "severity": "Warning",
                "code": "CognitiveComplexity",
                "message": "High complexity",
            }
        ]
    }
    report_file = tmp_path / "report.json"
    report_file.write_text(json.dumps(payload), encoding="utf-8")

    diagnostics = load_reports(tmp_path)
    assert len(diagnostics) == 1
    assert diagnostics[0]["severity"] == "WARNING"
    assert diagnostics[0]["line"] == 1


def test_format_response_contains_json():
    summary = build_summary([])
    text = format_response(summary)
    assert "Status: success" in text
    assert '"status": "success"' in text
