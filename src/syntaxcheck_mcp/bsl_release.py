from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from pathlib import Path

from .env_file import ensure_env_file, read_dotenv, write_dotenv_key
from .project_paths import (
    DEFAULT_BSL_VERSION,
    bsl_version_file,
    env_example_file,
    env_file,
    find_project_root,
    vendor_jar_path,
)

GITHUB_REPO = "1c-syntax/bsl-language-server"
GITHUB_API_LATEST = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
MIN_JAR_SIZE_BYTES = 50 * 1024 * 1024


def normalize_version(tag: str) -> str:
    text = tag.strip()
    if text.startswith("v"):
        text = text[1:]
    return text


def compare_versions(left: str, right: str) -> int:
    def parts(value: str) -> list[int]:
        return [int(part) for part in re.split(r"[.-]", normalize_version(value)) if part.isdigit()]

    left_parts = parts(left)
    right_parts = parts(right)
    length = max(len(left_parts), len(right_parts))
    left_parts.extend([0] * (length - len(left_parts)))
    right_parts.extend([0] * (length - len(right_parts)))
    for left_part, right_part in zip(left_parts, right_parts):
        if left_part < right_part:
            return -1
        if left_part > right_part:
            return 1
    return 0


def jar_download_url(version: str) -> str:
    normalized = normalize_version(version)
    return (
        f"https://github.com/{GITHUB_REPO}/releases/download/"
        f"v{normalized}/bsl-language-server-{normalized}-exec.jar"
    )


def release_page_url(version: str) -> str:
    normalized = normalize_version(version)
    return f"https://github.com/{GITHUB_REPO}/releases/tag/v{normalized}"


def _github_request(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "syntaxcheck-mcp",
        },
    )
    token = __import__("os").environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_latest_release_tag() -> str:
    payload = _github_request(GITHUB_API_LATEST)
    tag = payload.get("tag_name")
    if not tag:
        raise RuntimeError("GitHub API did not return tag_name")
    return normalize_version(tag)


def fetch_release_notes(version: str) -> str:
    normalized = normalize_version(version)
    url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/tags/v{normalized}"
    try:
        payload = _github_request(url)
    except urllib.error.HTTPError:
        return ""
    return str(payload.get("body") or "")


def read_pinned_version(root: Path | None = None) -> str:
    project_root = find_project_root(root)
    version_path = bsl_version_file(project_root)
    if version_path.exists():
        value = version_path.read_text(encoding="utf-8").strip()
        if value:
            return normalize_version(value)
    ensure_env_file(project_root)
    env_values = read_dotenv(env_file(project_root))
    if env_values.get("BSL_VERSION"):
        return normalize_version(env_values["BSL_VERSION"])
    return DEFAULT_BSL_VERSION


def set_pinned_version(version: str, root: Path | None = None) -> None:
    normalized = normalize_version(version)
    project_root = find_project_root(root)
    bsl_version_file(project_root).write_text(normalized + "\n", encoding="utf-8")
    ensure_env_file(project_root)
    write_dotenv_key(
        env_file(project_root),
        "BSL_VERSION",
        normalized,
        create_from_example=env_example_file(project_root),
    )
    example = env_example_file(project_root)
    if example.exists():
        write_dotenv_key(example, "BSL_VERSION", normalized)


def jar_is_valid(path: Path) -> bool:
    return path.exists() and path.stat().st_size >= MIN_JAR_SIZE_BYTES


def download_exec_jar(version: str, dest: Path | None = None, *, force: bool = False) -> Path:
    project_root = find_project_root()
    target = dest or vendor_jar_path(project_root)
    target.parent.mkdir(parents=True, exist_ok=True)

    if not force and jar_is_valid(target):
        pinned = read_pinned_version(project_root)
        if compare_versions(pinned, version) == 0:
            return target

    url = jar_download_url(version)
    temp_path = target.with_suffix(".jar.part")
    request = urllib.request.Request(url, headers={"User-Agent": "syntaxcheck-mcp"})
    try:
        with urllib.request.urlopen(request, timeout=900) as response, temp_path.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise

    if temp_path.stat().st_size < MIN_JAR_SIZE_BYTES:
        temp_path.unlink(missing_ok=True)
        raise RuntimeError(f"Downloaded jar is too small for version {version}: {url}")

    temp_path.replace(target)
    return target


def is_update_available(root: Path | None = None) -> tuple[str, str, bool]:
    pinned = read_pinned_version(root)
    latest = fetch_latest_release_tag()
    return pinned, latest, compare_versions(pinned, latest) < 0
