$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "_cli.ps1") update-bsl @args
