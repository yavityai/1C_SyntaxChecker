$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "_cli.ps1") stop @args
