"""Проверки настоящей Java/BSL LS: задайте BSL_JAR и BSL_CONFIG явно."""
import os
import shutil

import pytest

from syntaxcheck_mcp.server import syntaxcheck, syntaxcheck_project, bsl_format_code, bsl_list_rules

pytestmark = pytest.mark.skipif(
    not os.environ.get("BSL_JAR") or not shutil.which("java"),
    reason="Для интеграционных тестов нужны Java в PATH и BSL_JAR",
)


def test_real_parser_detects_error_and_accepts_valid_code():
    valid = syntaxcheck('Процедура Тест()\nСообщить("Тест");\nКонецПроцедуры')
    assert "error" not in valid
    assert not any(d["code"] == "ParseError" for d in valid["diagnostics"])
    invalid = syntaxcheck('Процедура Тест()\nА = ;\nКонецПроцедуры')
    assert any(d["code"] == "ParseError" for d in invalid["diagnostics"])


def test_real_project_preserves_both_source_paths():
    paths = ["CommonModules/Первый/Ext/Module.bsl", "CommonModules/Второй/Ext/Module.bsl"]
    result = syntaxcheck_project({p: 'Процедура Тест()\nА = ;\nКонецПроцедуры' for p in paths})
    errors = [d for d in result["diagnostics"] if d["code"] == "ParseError"]
    assert {d["file"] for d in errors} == set(paths)
    assert all(d["line"] == 2 for d in errors)


def test_real_formatter_and_rules():
    result = bsl_format_code('Процедура Тест()\nА=1;\nКонецПроцедуры')
    assert result["status"] == "ok"
    assert "А = 1;" in result["formatted"]
    rules = bsl_list_rules("ru", "ParseError")
    assert rules["status"] == "ok"
    rule = next(r for r in rules["rules"] if r["code"] == "ParseError")
    assert rule["name"]
