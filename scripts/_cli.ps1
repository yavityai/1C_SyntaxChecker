$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
pip install -e . -q 2>$null | Out-Null
python -m syntaxcheck_mcp.cli @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
