import json
from pathlib import Path
from unittest.mock import patch

import pytest

from syntaxcheck_mcp.bsl_release import (
    compare_versions,
    jar_download_url,
    normalize_version,
    read_pinned_version,
    set_pinned_version,
)
from syntaxcheck_mcp.env_file import get_syntaxcheck_port, read_dotenv, write_dotenv_key


def test_normalize_version():
    assert normalize_version("v0.29.0") == "0.29.0"
    assert normalize_version("0.29.0") == "0.29.0"


def test_compare_versions():
    assert compare_versions("0.24.2", "0.29.0") < 0
    assert compare_versions("0.29.0", "0.29.0") == 0
    assert compare_versions("0.30.0", "0.29.0") > 0


def test_jar_download_url():
    url = jar_download_url("0.29.0")
    assert url.endswith("bsl-language-server-0.29.0-exec.jar")


def test_read_and_set_pinned_version(tmp_path: Path):
    (tmp_path / "bsl.version").write_text("0.24.2\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    assert read_pinned_version(tmp_path) == "0.24.2"
    set_pinned_version("0.29.0", tmp_path)
    assert read_pinned_version(tmp_path) == "0.29.0"
    assert (tmp_path / "bsl.version").read_text(encoding="utf-8").strip() == "0.29.0"


def test_fetch_latest_release_tag_mock():
    payload = {"tag_name": "v0.29.0"}
    with patch("syntaxcheck_mcp.bsl_release._github_request", return_value=payload):
        from syntaxcheck_mcp.bsl_release import fetch_latest_release_tag

        assert fetch_latest_release_tag() == "0.29.0"


def test_env_read_write(tmp_path: Path):
    env_path = tmp_path / ".env"
    env_path.write_text("SYNTAXCHECK_PORT=8010\n", encoding="utf-8")
    values = read_dotenv(env_path)
    assert values["SYNTAXCHECK_PORT"] == "8010"
    write_dotenv_key(env_path, "SYNTAXCHECK_PORT", "9000")
    assert read_dotenv(env_path)["SYNTAXCHECK_PORT"] == "9000"


def test_get_syntaxcheck_port_from_env_file(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (tmp_path / ".env").write_text("SYNTAXCHECK_PORT=8123\n", encoding="utf-8")
    assert get_syntaxcheck_port(tmp_path) == 8123


def test_cli_update_check_exit_code(tmp_path: Path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (tmp_path / "bsl.version").write_text("0.24.2\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    from syntaxcheck_mcp.cli import main

    with patch("syntaxcheck_mcp.cli.fetch_latest_release_tag", return_value="0.29.0"):
        assert main(["update-bsl", "--check"]) == 1
    with patch("syntaxcheck_mcp.cli.fetch_latest_release_tag", return_value="0.24.2"):
        assert main(["update-bsl", "--check"]) == 0


def test_mcp_snippet_json(tmp_path: Path, monkeypatch, capsys):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (tmp_path / ".env").write_text("SYNTAXCHECK_PORT=8010\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    from syntaxcheck_mcp.cli import main

    assert main(["mcp-snippet"]) == 0
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert payload["mcpServers"]["1c-syntax-checker-mcp"]["url"] == "http://localhost:8010/mcp"
