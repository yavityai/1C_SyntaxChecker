import subprocess
import zipfile

import pytest

from syntaxcheck_mcp import bsl_runner
from syntaxcheck_mcp.bsl_runner import (
    AnalyzeResult,
    BslAnalyzeError,
    analyze_code,
    analyze_file,
    analyze_files,
    format_code,
    list_rules,
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


# --- list_rules ------------------------------------------------------------

def _fake_rules_jar(tmp_path):
    """Build a minimal jar mirroring BSL LS's diagnostic .properties layout."""
    jar = tmp_path / "bsl.jar"
    prefix = bsl_runner._DIAG_RES_PREFIX
    with zipfile.ZipFile(jar, "w") as z:
        z.writestr(
            prefix + "CanonicalSpellingKeywordsDiagnostic_en.properties",
            "diagnosticName=Canonical keyword writing\n"
            'diagnosticMessage=Keyword "%s" is not written canonically\n',
        )
        # ru values carry \uXXXX escapes, exactly like the real resources.
        z.writestr(
            prefix + "CanonicalSpellingKeywordsDiagnostic_ru.properties",
            "diagnosticName=\\u041a\\u0430\\u043d\\u043e\\u043d\\u0438\\u0447\n",
        )
        z.writestr(
            prefix + "BadWordsDiagnostic_en.properties",
            "diagnosticName=Prohibited words\n",
        )
        # non-diagnostic resource must be ignored
        z.writestr(prefix + "SomeHelper_en.properties", "x=y\n")
        z.writestr("BOOT-INF/classes/other/Thing.class", "junk")
    return jar


@pytest.fixture(autouse=True)
def _clear_rules_cache():
    bsl_runner._rules_cache.clear()
    yield
    bsl_runner._rules_cache.clear()


def test_list_rules_reads_jar(monkeypatch, tmp_path):
    monkeypatch.setattr(bsl_runner, "BSL_JAR", _fake_rules_jar(tmp_path))
    rules = list_rules()
    codes = [r["code"] for r in rules]
    assert codes == ["BadWords", "CanonicalSpellingKeywords"]  # sorted, helper dropped
    canonical = next(r for r in rules if r["code"] == "CanonicalSpellingKeywords")
    assert canonical["name"] == "Canonical keyword writing"
    assert "%s" in canonical["message"]


def test_list_rules_decodes_unicode_escapes(monkeypatch, tmp_path):
    monkeypatch.setattr(bsl_runner, "BSL_JAR", _fake_rules_jar(tmp_path))
    rules = list_rules(language="ru")
    canonical = next(r for r in rules if r["code"] == "CanonicalSpellingKeywords")
    assert canonical["name"] == "Канонич"


def test_list_rules_filter(monkeypatch, tmp_path):
    monkeypatch.setattr(bsl_runner, "BSL_JAR", _fake_rules_jar(tmp_path))
    rules = list_rules(filter="bad")
    assert [r["code"] for r in rules] == ["BadWords"]


def test_list_rules_missing_jar_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(bsl_runner, "BSL_JAR", tmp_path / "nope.jar")
    with pytest.raises(BslAnalyzeError, match="JAR not found"):
        list_rules()


# --- format_code -----------------------------------------------------------

def test_format_code_empty_raises():
    with pytest.raises(BslAnalyzeError):
        format_code("   ")


def test_format_code_missing_jar_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(bsl_runner, "BSL_JAR", tmp_path / "nope.jar")
    with pytest.raises(BslAnalyzeError, match="JAR not found"):
        format_code("Процедура Т() КонецПроцедуры")


def test_format_code_reads_back_formatted(monkeypatch, tmp_path):
    jar = tmp_path / "bsl.jar"
    jar.write_text("x", encoding="utf-8")
    monkeypatch.setattr(bsl_runner, "BSL_JAR", jar)

    from pathlib import Path

    def fake_run(cmd, **kwargs):
        src_dir = Path(cmd[cmd.index("-s") + 1])
        target = src_dir / "Module.bsl"
        # Simulate the in-place formatter (BOM + tidied source).
        target.write_bytes(b"\xef\xbb\xbf" + "Процедура Т()\n    КонецПроцедуры".encode("utf-8"))
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = format_code("Процедура Т() КонецПроцедуры")
    assert out == "Процедура Т()\n    КонецПроцедуры"


def test_format_code_failure_raises(monkeypatch, tmp_path):
    jar = tmp_path / "bsl.jar"
    jar.write_text("x", encoding="utf-8")
    monkeypatch.setattr(bsl_runner, "BSL_JAR", jar)

    def fake_run(cmd, **kwargs):
        # Formatter errored and left the file untouched.
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="boom")

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(BslAnalyzeError, match="formatting failed"):
        format_code("Процедура Т() КонецПроцедуры")


@pytest.mark.parametrize("returncode", [0, 1])
def test_analysis_without_report_fails_even_without_stderr(monkeypatch, tmp_path, returncode):
    _prepare(monkeypatch, tmp_path)
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw:
                        subprocess.CompletedProcess(a[0], returncode, stdout="", stderr=""))
    with pytest.raises(BslAnalyzeError, match="no JSON report"):
        analyze_code("Процедура Тест()\nКонецПроцедуры")


def test_analysis_runs_in_source_directory(monkeypatch, tmp_path):
    """BSL LS не должен вычислять относительный путь между разными дисками."""
    import json
    from pathlib import Path
    _prepare(monkeypatch, tmp_path)
    def fake_run(cmd, **kwargs):
        assert Path(kwargs["cwd"]) == Path(cmd[cmd.index("-s") + 1])
        report = Path(cmd[cmd.index("-o") + 1]) / "bsl-json.json"
        report.write_text(json.dumps({"fileinfos": []}), encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
    monkeypatch.setattr(subprocess, "run", fake_run)
    assert analyze_code("Процедура Тест()\nКонецПроцедуры").summary["status"] == "success"


def test_formatter_failure_without_stderr(monkeypatch, tmp_path):
    _prepare(monkeypatch, tmp_path)
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw:
                        subprocess.CompletedProcess(a[0], 1, stdout="failed", stderr=""))
    with pytest.raises(BslAnalyzeError, match="failed"):
        format_code("Процедура Тест()\nКонецПроцедуры")
