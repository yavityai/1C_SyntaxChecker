param(
    [int]$Port = 0
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
. (Join-Path $PSScriptRoot "_docker.ps1")
. (Join-Path $PSScriptRoot "_env.ps1")
Assert-DockerReady

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

if ($Port -gt 0) {
    $env:SYNTAXCHECK_PORT = "$Port"
}

$resolvedPort = Get-SyntaxCheckPort
$mcpUrl = Get-McpUrl

$imageExists = docker images --format "{{.Repository}}" 2>$null | Select-String -Pattern "syntax-checker-syntaxcheck-mcp|syntaxcheck-mcp" -Quiet
if (-not $imageExists) {
    Write-Host "Образ не найден. Сначала выполните: .\scripts\install.ps1" -ForegroundColor Yellow
    throw "Docker image not built. Run .\scripts\install.ps1 first."
}

Write-Host "Starting syntaxcheck-mcp on port $resolvedPort (host)..." -ForegroundColor Cyan
docker compose up -d

if ($LASTEXITCODE -ne 0) {
    throw "docker compose up failed with exit code $LASTEXITCODE"
}

docker compose ps
Write-Host ""
Write-Host "MCP endpoint: $mcpUrl" -ForegroundColor Green
Write-Host "Port is set in .env (SYNTAXCHECK_PORT). Change: .\scripts\set-port.ps1 -Port 9000" -ForegroundColor Yellow
Write-Host "Cursor snippet: .\scripts\show-mcp-snippet.ps1" -ForegroundColor Yellow
