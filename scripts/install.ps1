$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "_cli.ps1") install @args
