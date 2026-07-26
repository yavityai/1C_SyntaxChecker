import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .config import (
    BSL_ANALYZE_TIMEOUT_SEC,
    BSL_CONFIG,
    BSL_JAR,
    BSL_MEMORY_MB,
)
from .report_parser import build_summary, format_response, load_reports


PROGRESS_BAR_RE = re.compile(r"(\x1b\[[0-9;]*m)?[█░▓▒]+")

BOM = b"\xef\xbb\xbf"

# BSL Language Server only analyzes these source extensions.
BSL_SUFFIXES = (".bsl", ".os")


@dataclass
class AnalyzeResult:
    summary: dict
    returncode: int
    stderr: str


class BslAnalyzeError(RuntimeError):
    pass


def _safe_relpath(path: str) -> PurePosixPath:
    """Normalize a user-supplied path into a safe, relative POSIX path.

    Strips drive letters and anchors, rejects parent traversal (``..``) so a
    caller can never write outside the temporary analysis directory.
    """
    raw = str(path).replace("\\", "/").strip()
    if not raw:
        raise BslAnalyzeError("File path must not be empty")

    parts: list[str] = []
    for part in PurePosixPath(raw).parts:
        if part in ("", ".", "/"):
            continue
        if part == "..":
            raise BslAnalyzeError(f"File path must not contain '..': {path}")
        if part.endswith(":"):  # drive letter such as 'C:'
            continue
        parts.append(part)

    if not parts:
        raise BslAnalyzeError(f"Invalid file path: {path}")
    return PurePosixPath(*parts)


def _write_bsl_source(code: str, target: Path) -> None:
    # 1C modules are commonly stored as UTF-8 with BOM.
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(BOM + code.encode("utf-8"))


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


def _relativize(diagnostics: list[dict], src_dir: Path) -> list[dict]:
    """Rewrite absolute temp paths in diagnostics back to project-relative paths."""
    src_resolved = src_dir.resolve()
    for item in diagnostics:
        file = item.get("file")
        if not file:
            continue
        try:
            fp = Path(file)
        except (TypeError, ValueError):
            continue
        if not fp.is_absolute():
            continue
        try:
            item["file"] = fp.resolve().relative_to(src_resolved).as_posix()
        except (ValueError, OSError):
            pass
    return diagnostics


def _require_toolchain() -> None:
    if not BSL_JAR.exists():
        raise BslAnalyzeError(f"BSL Language Server JAR not found: {BSL_JAR}")
    if not BSL_CONFIG.exists():
        raise BslAnalyzeError(f"BSL configuration file not found: {BSL_CONFIG}")


def _analyze_tree(files: dict[str, str]) -> AnalyzeResult:
    """Write ``files`` (relative path -> code) into a temp tree and analyze it."""
    _require_toolchain()

    with tempfile.TemporaryDirectory(prefix="syntaxcheck_") as tmp:
        tmp_path = Path(tmp)
        src_dir = tmp_path / "src"
        out_dir = tmp_path / "out"
        src_dir.mkdir()
        out_dir.mkdir()

        for rel, code in files.items():
            rel_path = _safe_relpath(rel)
            _write_bsl_source(code, src_dir / Path(rel_path))

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
        diagnostics = _relativize(load_reports(out_dir), src_dir)
        summary = build_summary(diagnostics)

        if not diagnostics and completed.returncode != 0 and stderr:
            raise BslAnalyzeError(f"BSL analysis failed: {stderr}")

        return AnalyzeResult(summary=summary, returncode=completed.returncode, stderr=stderr)


def read_source_file(path: str) -> str:
    """Read a BSL source file from the server filesystem, stripping any BOM.

    Used when a caller passes a path but no content (local installs / mounted
    volumes). Raises :class:`BslAnalyzeError` with actionable guidance when the
    server cannot see the file (the common case when running inside Docker).
    """
    p = Path(path)
    if not p.exists():
        raise BslAnalyzeError(
            f"File not found on the server: {path}. Pass 'content' explicitly "
            "if the server cannot see this path (e.g. it runs inside Docker)."
        )
    if not p.is_file():
        raise BslAnalyzeError(f"Not a file: {path}")

    data = p.read_bytes()
    if data.startswith(BOM):
        data = data[len(BOM):]
    return data.decode("utf-8", errors="replace")


def analyze_code(code: str) -> AnalyzeResult:
    if not code or not code.strip():
        raise BslAnalyzeError("Parameter 'code' must not be empty")
    return _analyze_tree({"Module.bsl": code})


def analyze_file(path: str, code: str) -> AnalyzeResult:
    """Analyze a single file, preserving its path so module-type-aware rules fire."""
    if not code or not code.strip():
        raise BslAnalyzeError("Parameter 'code' must not be empty")
    rel = _safe_relpath(path)
    if rel.suffix.lower() not in BSL_SUFFIXES:
        rel = rel.with_name(rel.name + ".bsl")
    return _analyze_tree({str(rel): code})


def analyze_files(files: dict[str, str]) -> AnalyzeResult:
    """Analyze several files together so cross-module diagnostics can fire."""
    if not files:
        raise BslAnalyzeError("No files provided")
    cleaned = {
        path: code
        for path, code in files.items()
        if code is not None and str(code).strip()
    }
    if not cleaned:
        raise BslAnalyzeError("All provided files are empty")
    return _analyze_tree(cleaned)


def analyze_code_text(code: str) -> str:
    result = analyze_code(code)
    response = format_response(result.summary)
    if result.stderr:
        response = f"{response}\n\nstderr:\n{result.stderr}"
    return response
