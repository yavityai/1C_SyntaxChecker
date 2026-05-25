param(
    [Parameter(Mandatory = $true)]
    [int]$Port
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_env.ps1")

Set-SyntaxCheckPort -Port $Port

Write-Host "SYNTAXCHECK_PORT=$Port saved to .env" -ForegroundColor Green
Write-Host "MCP URL: $(Get-McpUrl -Port $Port)" -ForegroundColor Cyan
Write-Host ""
Write-Host "If the container is already running, restart it:" -ForegroundColor Yellow
Write-Host "  docker compose down" -ForegroundColor Yellow
Write-Host "  .\scripts\start.ps1" -ForegroundColor Yellow
Write-Host ""
Write-Host "Cursor .cursor/mcp.json — snippet:" -ForegroundColor Yellow
Write-Host "  .\scripts\show-mcp-snippet.ps1" -ForegroundColor Yellow
