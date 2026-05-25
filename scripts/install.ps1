$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
. (Join-Path $PSScriptRoot "_docker.ps1")
Assert-DockerReady

Write-Host "Building syntaxcheck-mcp Docker image..." -ForegroundColor Cyan

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example"
}

& (Join-Path $PSScriptRoot "download-bsl-jar.ps1")

docker compose build

if ($LASTEXITCODE -ne 0) {
    throw "Docker build failed with exit code $LASTEXITCODE"
}

Write-Host "Done. Run .\scripts\start.ps1 to start the MCP server." -ForegroundColor Green
