$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

$BslVersion = "0.24.2"
foreach ($line in Get-Content ".env" -ErrorAction SilentlyContinue) {
    if ($line -match '^\s*BSL_VERSION\s*=\s*(.+)\s*$') {
        $BslVersion = $Matches[1].Trim()
        break
    }
}

$VendorDir = Join-Path $Root "vendor"
$JarPath = Join-Path $VendorDir "bsl-language-server.jar"
$JarUrl = "https://github.com/1c-syntax/bsl-language-server/releases/download/v$BslVersion/bsl-language-server-$BslVersion-exec.jar"

if (-not (Test-Path $VendorDir)) {
    New-Item -ItemType Directory -Path $VendorDir | Out-Null
}

$NeedDownload = $true
if (Test-Path $JarPath) {
    $sizeMb = (Get-Item $JarPath).Length / 1MB
    if ($sizeMb -gt 50) {
        Write-Host "BSL jar already present: $JarPath ($([math]::Round($sizeMb, 1)) MB)" -ForegroundColor Green
        $NeedDownload = $false
    }
    else {
        Write-Host "Removing incomplete jar ($([math]::Round($sizeMb, 1)) MB)..." -ForegroundColor Yellow
        Remove-Item $JarPath -Force
    }
}

if (-not $NeedDownload) {
    return
}

Write-Host "Downloading BSL Language Server $BslVersion (~100 MB)..." -ForegroundColor Cyan
Write-Host $JarUrl

$ProgressPreference = "SilentlyContinue"
try {
    Invoke-WebRequest -Uri $JarUrl -OutFile $JarPath -MaximumRedirection 5 -TimeoutSec 900
}
catch {
    throw "Download failed: $($_.Exception.Message)`nURL: $JarUrl"
}

$sizeMb = (Get-Item $JarPath).Length / 1MB
if ($sizeMb -lt 50) {
    Remove-Item $JarPath -Force -ErrorAction SilentlyContinue
    throw "Downloaded file is too small ($([math]::Round($sizeMb, 1)) MB). Check network or BSL_VERSION in .env."
}

Write-Host "Saved: $JarPath ($([math]::Round($sizeMb, 1)) MB)" -ForegroundColor Green
