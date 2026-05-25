param(
    [Parameter(Mandatory = $true)]
    [int]$Port
)

$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "_cli.ps1") set-port $Port @args
