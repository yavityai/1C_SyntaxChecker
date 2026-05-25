$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Install-ProjectPackage {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        throw "Python not found. Install Python 3.10+ and add it to PATH."
    }

    # pip пишет notices в stderr — не прерываем скрипт при $ErrorActionPreference Stop
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    try {
        & python -m pip install -e . -q 2>&1 | Out-Null
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }

    if ($LASTEXITCODE -ne 0) {
        throw "pip install failed with exit code $LASTEXITCODE"
    }
}

Install-ProjectPackage

& python -m syntaxcheck_mcp.cli @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
