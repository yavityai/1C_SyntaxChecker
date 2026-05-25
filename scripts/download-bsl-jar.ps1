$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "_cli.ps1") download-jar @args
