import argparse
import io
import json

import pytest

from syntaxcheck_mcp import cli


@pytest.mark.parametrize("report, expected", [
    ({"diagnostics": [{"code": "ParseError"}]}, 0),
    ({"status": "success", "diagnostics": []}, 1),
    ({"status": "error", "error": "Java not found", "diagnostics": []}, 1),
])
def test_smoke_test_checks_analysis_result(monkeypatch, report, expected):
    payload = json.dumps({"result": {"structuredContent": report}}).encode()
    monkeypatch.setattr(cli.urllib.request, "urlopen", lambda *a, **kw: io.BytesIO(payload))
    assert cli.cmd_test(argparse.Namespace(port=8010)) == expected


def test_smoke_test_rejects_jsonrpc_error(monkeypatch):
    payload = b'{"error": {"code": -32603, "message": "Internal error"}}'
    monkeypatch.setattr(cli.urllib.request, "urlopen", lambda *a, **kw: io.BytesIO(payload))
    assert cli.cmd_test(argparse.Namespace(port=8010)) == 1
