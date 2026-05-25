function Read-DotEnv {
    param(
        [string]$Path = (Join-Path (Split-Path -Parent $PSScriptRoot) ".env")
    )

    $values = @{}
    if (-not (Test-Path $Path)) {
        return $values
    }

    Get-Content $Path -Encoding UTF8 | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            return
        }
        $eq = $line.IndexOf("=")
        if ($eq -lt 1) {
            return
        }
        $key = $line.Substring(0, $eq).Trim()
        $value = $line.Substring($eq + 1).Trim()
        if ($value.StartsWith('"') -and $value.EndsWith('"')) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        $values[$key] = $value
    }

    return $values
}

function Get-SyntaxCheckPort {
    param(
        [int]$Override = 0,
        [string]$EnvPath
    )

    if ($Override -gt 0) {
        return $Override
    }

    if ($env:SYNTAXCHECK_PORT) {
        return [int]$env:SYNTAXCHECK_PORT
    }

    $root = Split-Path -Parent $PSScriptRoot
    if (-not $EnvPath) {
        $EnvPath = Join-Path $root ".env"
    }

    $values = Read-DotEnv -Path $EnvPath
    if ($values.ContainsKey("SYNTAXCHECK_PORT") -and $values["SYNTAXCHECK_PORT"]) {
        return [int]$values["SYNTAXCHECK_PORT"]
    }

    return 8010
}

function Set-SyntaxCheckPort {
    param(
        [Parameter(Mandatory = $true)]
        [int]$Port,
        [string]$EnvPath
    )

    if ($Port -lt 1024 -or $Port -gt 65535) {
        throw "Port must be between 1024 and 65535, got $Port"
    }

    $root = Split-Path -Parent $PSScriptRoot
    if (-not $EnvPath) {
        $EnvPath = Join-Path $root ".env"
    }

    if (-not (Test-Path $EnvPath)) {
        Copy-Item (Join-Path $root ".env.example") $EnvPath
    }

    $lines = Get-Content $EnvPath -Encoding UTF8
    $updated = $false
    $result = foreach ($line in $lines) {
        if ($line -match '^\s*SYNTAXCHECK_PORT\s*=') {
            $updated = $true
            "SYNTAXCHECK_PORT=$Port"
        }
        else {
            $line
        }
    }

    if (-not $updated) {
        $result += "SYNTAXCHECK_PORT=$Port"
    }

    Set-Content -Path $EnvPath -Value $result -Encoding UTF8
}

function Get-McpUrl {
    param([int]$Port = 0)

    $resolved = Get-SyntaxCheckPort -Override $Port
    return "http://localhost:$resolved/mcp"
}
