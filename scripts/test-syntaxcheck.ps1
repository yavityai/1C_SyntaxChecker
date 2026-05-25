param(
    [int]$Port = 0
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
. (Join-Path $PSScriptRoot "_env.ps1")

if ($Port -gt 0) {
    $env:SYNTAXCHECK_PORT = "$Port"
}

$Uri = Get-McpUrl
Write-Host "Calling syntaxcheck on $Uri ..." -ForegroundColor Cyan

$Body = @{
    jsonrpc = "2.0"
    id = 1
    method = "tools/call"
    params = @{
        name = "syntaxcheck"
        arguments = @{
            code = @"
Процедура Тест()
    а = ;
КонецПроцедуры
"@
        }
    }
} | ConvertTo-Json -Depth 6

try {
    $Response = Invoke-RestMethod -Uri $Uri -Method Post -Body $Body -ContentType "application/json" -Headers @{ Accept = "application/json" }
    $Response | ConvertTo-Json -Depth 10
}
catch {
    Write-Host "Request failed. Is the container running on the configured port? Run .\scripts\start.ps1 first." -ForegroundColor Red
    throw
}
