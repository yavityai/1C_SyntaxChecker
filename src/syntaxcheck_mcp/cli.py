from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from .bsl_release import (
    compare_versions,
    download_exec_jar,
    fetch_latest_release_tag,
    jar_is_valid,
    read_pinned_version,
    release_page_url,
    set_pinned_version,
)
from .docker_util import assert_docker_ready, docker_engine_ready, run_compose
from .env_file import ensure_env_file, get_mcp_url, get_syntaxcheck_port, write_dotenv_key
from .project_paths import env_example_file, find_project_root, vendor_jar_path


def _project_root() -> Path:
    return find_project_root()


def cmd_download_jar(_: argparse.Namespace) -> int:
    root = _project_root()
    ensure_env_file(root)
    version = read_pinned_version(root)
    print(f"Downloading BSL Language Server {version}...")
    jar_path = download_exec_jar(version, force=True)
    print(f"Saved: {jar_path} ({jar_path.stat().st_size // (1024 * 1024)} MB)")
    return 0


def cmd_install(_: argparse.Namespace) -> int:
    root = _project_root()
    assert_docker_ready()
    ensure_env_file(root)
    version = read_pinned_version(root)
    print(f"Downloading BSL Language Server {version}...")
    jar_path = download_exec_jar(version)
    print(f"Saved: {jar_path} ({jar_path.stat().st_size // (1024 * 1024)} MB)")
    print("Building Docker image...")
    run_compose(["build"], cwd=str(root))
    print("Done. Run: python -m syntaxcheck_mcp.cli start")
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    import os

    root = _project_root()
    assert_docker_ready()
    ensure_env_file(root)
    if args.port:
        os.environ["SYNTAXCHECK_PORT"] = str(args.port)
    port = get_syntaxcheck_port(root, override=args.port or 0)
    if not _docker_image_exists():
        print("Docker image not found. Run install first.")
        return 1
    print(f"Starting syntaxcheck-mcp on port {port}...")
    run_compose(["up", "-d"], cwd=str(root))
    run_compose(["ps"], cwd=str(root))
    print(f"MCP endpoint: {get_mcp_url(root, port_override=args.port or 0)}")
    return 0


def cmd_stop(_: argparse.Namespace) -> int:
    run_compose(["down"], cwd=str(_project_root()))
    return 0


def cmd_set_port(args: argparse.Namespace) -> int:
    root = _project_root()
    port = args.port
    if port < 1024 or port > 65535:
        print("Port must be between 1024 and 65535", file=sys.stderr)
        return 1
    ensure_env_file(root)
    write_dotenv_key(
        root / ".env",
        "SYNTAXCHECK_PORT",
        str(port),
        create_from_example=env_example_file(root),
    )
    print(f"SYNTAXCHECK_PORT={port} saved to .env")
    print(f"MCP URL: {get_mcp_url(root, port_override=port)}")
    return 0


def cmd_mcp_snippet(args: argparse.Namespace) -> int:
    payload = {
        "mcpServers": {
            "1c-syntax-checker-mcp": {
                "url": get_mcp_url(_project_root(), port_override=args.port or 0),
                "connection_id": "1c_lsp_service_001",
                "description": "BSL syntax validation via BSL Language Server (open-source)",
            }
        }
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_test(args: argparse.Namespace) -> int:
    uri = get_mcp_url(_project_root(), port_override=args.port or 0)
    body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "syntaxcheck",
            "arguments": {
                "code": "Процедура Тест()\n    а = ;\nКонецПроцедуры",
            },
        },
    }
    request = urllib.request.Request(
        uri,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
        method="POST",
    )
    print(f"Calling syntaxcheck on {uri} ...")
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            payload = json.loads(response.read().decode("utf-8"))
            print(json.dumps(payload, ensure_ascii=False))
            result = payload.get("result", {})
            report = result.get("structuredContent")
            if report is None:
                report = next((json.loads(item["text"]) for item in result.get("content", [])
                               if item.get("type") == "text"), {})
            if result.get("isError") or not any(
                d.get("code") == "ParseError" for d in report.get("diagnostics", [])
            ):
                print("Smoke test failed: expected ParseError was not returned.", file=sys.stderr)
                return 1
    except urllib.error.URLError as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        return 1
    except (ValueError, TypeError, AttributeError, KeyError) as exc:
        print(f"Invalid MCP response: {exc}", file=sys.stderr)
        return 1
    return 0


def cmd_update_bsl(args: argparse.Namespace) -> int:
    root = _project_root()
    pinned = read_pinned_version(root)
    jar_path = vendor_jar_path(root)

    if args.offline:
        latest = pinned
        target = args.version or pinned
    elif args.version:
        target = args.version
        latest = target
    else:
        try:
            latest = fetch_latest_release_tag(fallback=pinned if args.yes else None)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            print(
                "Tip: use --offline to refresh jar for pinned bsl.version without GitHub API.",
                file=sys.stderr,
            )
            return 1
        if latest == pinned and args.yes and not args.version:
            print(
                "GitHub API unavailable; using pinned version from bsl.version.",
                file=sys.stderr,
            )
        target = latest

    version_changed = compare_versions(pinned, target) != 0
    needs_jar = args.refresh or not jar_is_valid(jar_path)
    needs_update = version_changed or (args.yes and needs_jar)

    print(f"Pinned: {pinned} | Target: {target}")

    if args.check:
        if args.offline:
            return 1 if needs_jar else 0
        if args.version:
            return 1 if version_changed else 0
        try:
            remote_latest = fetch_latest_release_tag()
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        return 1 if compare_versions(pinned, remote_latest) < 0 else 0

    if not needs_update:
        print("Already up to date.")
        return 0

    if not args.yes and not args.version and not args.offline:
        answer = input(f"Download {target} and update bsl.version? [y/N] ").strip().lower()
        if answer not in {"y", "yes"}:
            print("Cancelled.")
            return 0

    if version_changed:
        set_pinned_version(target, root)
        print(f"Updated pinned version to {target}")
    print(f"Release: {release_page_url(target)}")
    download_exec_jar(target, force=True)
    print(f"Saved jar: {jar_path}")
    if docker_engine_ready():
        print("Rebuilding Docker image...")
        run_compose(["build"], cwd=str(root))
    else:
        print("Docker is not running. Rebuild later with: python -m syntaxcheck_mcp.cli install")
    return 0


def _docker_image_exists() -> bool:
    root = _project_root()
    result = subprocess.run(
        ["docker", "images", "--format", "{{.Repository}}"],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(root),
    )
    if result.returncode != 0:
        return False
    return any(
        "syntax-checker-syntaxcheck-mcp" in name or "syntaxcheck-mcp" in name
        for name in result.stdout.splitlines()
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="syntaxcheck", description="Syntax-Checker MCP tooling")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("download-jar", help="Download BSL jar only")
    subparsers.add_parser("install", help="Download BSL jar and build Docker image")

    start_parser = subparsers.add_parser("start", help="Start MCP server container")
    start_parser.add_argument("--port", type=int, default=0)

    subparsers.add_parser("stop", help="Stop MCP server container")

    port_parser = subparsers.add_parser("set-port", help="Set SYNTAXCHECK_PORT in .env")
    port_parser.add_argument("port", type=int)

    snippet_parser = subparsers.add_parser("mcp-snippet", help="Print Cursor mcp.json snippet")
    snippet_parser.add_argument("--port", type=int, default=0)

    test_parser = subparsers.add_parser("test", help="Smoke test syntaxcheck endpoint")
    test_parser.add_argument("--port", type=int, default=0)

    update_parser = subparsers.add_parser("update-bsl", help="Check or update BSL Language Server")
    update_parser.add_argument("--check", action="store_true", help="Exit 1 if update available")
    update_parser.add_argument("--yes", action="store_true", help="Apply update without prompt")
    update_parser.add_argument("--offline", action="store_true", help="Skip GitHub API; use pinned bsl.version")
    update_parser.add_argument("--refresh", action="store_true", help="Re-download jar even if version unchanged")
    update_parser.add_argument("--version", help="Pin specific BSL version")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handlers = {
        "download-jar": cmd_download_jar,
        "install": cmd_install,
        "start": cmd_start,
        "stop": cmd_stop,
        "set-port": cmd_set_port,
        "mcp-snippet": cmd_mcp_snippet,
        "test": cmd_test,
        "update-bsl": cmd_update_bsl,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
