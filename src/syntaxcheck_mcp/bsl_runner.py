import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .config import (
    BSL_ANALYZE_TIMEOUT_SEC,
    BSL_CONFIG,
    BSL_JAR,
    BSL_MEMORY_MB,
)
from .report_parser import build_summary, format_response, load_reports


PROGRESS_BAR_RE = re.compile(r"(\x1b\[[0-9;]*m)?[█░▓▒]+")


@dataclass
class AnalyzeResult:
    summary: dict
    returncode: int
    stderr: str


class BslAnalyzeError(RuntimeError):
    pass


def _write_bsl_source(code: str, target: Path) -> None:
    # 1C modules are commonly stored as UTF-8 with BOM.
    target.write_bytes(b"\xef\xbb\xbf" + code.encode("utf-8"))


def _filter_stderr(stderr: str) -> str:
    lines = []
    for line in stderr.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if PROGRESS_BAR_RE.search(stripped):
            continue
        if stripped.startswith("Analyzing") and "%" in stripped:
            continue
        lines.append(line)
    return "\n".join(lines)


def analyze_code(code: str) -> AnalyzeResult:
    if not code or not code.strip():
        raise BslAnalyzeError("Parameter 'code' must not be empty")

    if not BSL_JAR.exists():
        raise BslAnalyzeError(f"BSL Language Server JAR not found: {BSL_JAR}")

    if not BSL_CONFIG.exists():
        raise BslAnalyzeError(f"BSL configuration file not found: {BSL_CONFIG}")

    with tempfile.TemporaryDirectory(prefix="syntaxcheck_") as tmp:
        tmp_path = Path(tmp)
        src_dir = tmp_path / "src"
        out_dir = tmp_path / "out"
        src_dir.mkdir()
        out_dir.mkdir()

        _write_bsl_source(code, src_dir / "Module.bsl")

        cmd = [
            "java",
            f"-Xmx{BSL_MEMORY_MB}m",
            "-jar",
            str(BSL_JAR),
            "analyze",
            "-s",
            str(src_dir),
            "-o",
            str(out_dir),
            "-r",
            "json",
            "-c",
            str(BSL_CONFIG),
            "-q",
        ]

        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=BSL_ANALYZE_TIMEOUT_SEC,
                check=False,
            )
        except FileNotFoundError as exc:
            raise BslAnalyzeError(
                "Java runtime not found. Install a JRE/JDK and ensure 'java' is on PATH."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise BslAnalyzeError(
                f"BSL analysis timed out after {BSL_ANALYZE_TIMEOUT_SEC}s. "
                "Increase BSL_ANALYZE_TIMEOUT_SEC or reduce the code size."
            ) from exc
        except OSError as exc:
            raise BslAnalyzeError(f"Failed to start BSL Language Server: {exc}") from exc

        stderr = _filter_stderr(completed.stderr)
        diagnostics = load_reports(out_dir)
        summary = build_summary(diagnostics)

        if not diagnostics and completed.returncode != 0 and stderr:
            raise BslAnalyzeError(f"BSL analysis failed: {stderr}")

        return AnalyzeResult(summary=summary, returncode=completed.returncode, stderr=stderr)


def analyze_code_text(code: str) -> str:
    result = analyze_code(code)
    response = format_response(result.summary)
    if result.stderr:
        response = f"{response}\n\nstderr:\n{result.stderr}"
    return response
