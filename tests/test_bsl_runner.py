import subprocess

import pytest

from syntaxcheck_mcp import bsl_runner
from syntaxcheck_mcp.bsl_runner import BslAnalyzeError, analyze_code


def _prepare(monkeypatch, tmp_path):
    jar = tmp_path / "bsl.jar"
    jar.write_text("x", encoding="utf-8")
    cfg = tmp_path / "cfg.json"
    cfg.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(bsl_runner, "BSL_JAR", jar)
    monkeypatch.setattr(bsl_runner, "BSL_CONFIG", cfg)


def test_empty_code_raises():
    with pytest.raises(BslAnalyzeError):
        analyze_code("   ")


def test_missing_jar_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(bsl_runner, "BSL_JAR", tmp_path / "nope.jar")
    with pytest.raises(BslAnalyzeError, match="JAR not found"):
        analyze_code("Процедура Тест() КонецПроцедуры")


def test_java_not_found_wrapped(monkeypatch, tmp_path):
    _prepare(monkeypatch, tmp_path)

    def boom(*args, **kwargs):
        raise FileNotFoundError("java")

    monkeypatch.setattr(subprocess, "run", boom)
    with pytest.raises(BslAnalyzeError, match="Java runtime not found"):
        analyze_code("Процедура Тест() КонецПроцедуры")


def test_timeout_wrapped(monkeypatch, tmp_path):
    _prepare(monkeypatch, tmp_path)

    def boom(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="java", timeout=1)

    monkeypatch.setattr(subprocess, "run", boom)
    with pytest.raises(BslAnalyzeError, match="timed out"):
        analyze_code("Процедура Тест() КонецПроцедуры")
