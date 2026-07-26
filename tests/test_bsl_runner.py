import subprocess

import pytest

from syntaxcheck_mcp import bsl_runner
from syntaxcheck_mcp.bsl_runner import (
    AnalyzeResult,
    BslAnalyzeError,
    analyze_code,
    analyze_file,
    analyze_files,
    read_source_file,
)
from syntaxcheck_mcp.bsl_runner import _safe_relpath


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


# --- path safety -----------------------------------------------------------

def test_safe_relpath_strips_drive_and_anchor():
    assert _safe_relpath("C:\\proj\\CommonModules\\Util\\Module.bsl").as_posix() == (
        "proj/CommonModules/Util/Module.bsl"
    )
    assert _safe_relpath("/abs/Module.bsl").as_posix() == "abs/Module.bsl"
    assert _safe_relpath("a\\b/c.bsl").as_posix() == "a/b/c.bsl"


def test_safe_relpath_rejects_traversal():
    with pytest.raises(BslAnalyzeError, match=r"\.\."):
        _safe_relpath("../../etc/passwd")


def test_safe_relpath_rejects_empty():
    with pytest.raises(BslAnalyzeError):
        _safe_relpath("   ")


# --- read_source_file ------------------------------------------------------

def test_read_source_file_strips_bom(tmp_path):
    f = tmp_path / "Module.bsl"
    f.write_bytes(b"\xef\xbb\xbf\xd0\x9f\xd1\x80\xd0\xbe")  # BOM + "Про"
    assert read_source_file(str(f)) == "Про"


def test_read_source_file_missing_raises():
    with pytest.raises(BslAnalyzeError, match="not found on the server"):
        read_source_file("definitely/missing/Module.bsl")


# --- analyze_file / analyze_files (subprocess mocked) ----------------------

def test_analyze_file_coerces_extension(monkeypatch):
    captured = {}

    def fake_tree(files):
        captured["files"] = files
        return AnalyzeResult(summary={}, returncode=0, stderr="")

    monkeypatch.setattr(bsl_runner, "_analyze_tree", fake_tree)
    analyze_file("CommonModules/Util/Module", "Процедура Т() КонецПроцедуры")
    assert list(captured["files"]) == ["CommonModules/Util/Module.bsl"]


def test_analyze_file_keeps_bsl_extension(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        bsl_runner,
        "_analyze_tree",
        lambda files: captured.setdefault("files", files) or AnalyzeResult({}, 0, ""),
    )
    analyze_file("Catalogs/Товар/Ext/ObjectModule.bsl", "Процедура Т() КонецПроцедуры")
    assert list(captured["files"]) == ["Catalogs/Товар/Ext/ObjectModule.bsl"]


def test_analyze_file_empty_raises():
    with pytest.raises(BslAnalyzeError):
        analyze_file("Module.bsl", "   ")


def test_analyze_files_drops_empty(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        bsl_runner,
        "_analyze_tree",
        lambda files: captured.setdefault("files", files) or AnalyzeResult({}, 0, ""),
    )
    analyze_files({"a.bsl": "Процедура А() КонецПроцедуры", "b.bsl": "  ", "c.bsl": None})
    assert list(captured["files"]) == ["a.bsl"]


def test_analyze_files_all_empty_raises():
    with pytest.raises(BslAnalyzeError, match="empty"):
        analyze_files({"a.bsl": "", "b.bsl": "   "})


def test_analyze_files_none_raises():
    with pytest.raises(BslAnalyzeError):
        analyze_files({})
