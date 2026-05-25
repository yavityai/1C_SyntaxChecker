$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "_cli.ps1") start @args
