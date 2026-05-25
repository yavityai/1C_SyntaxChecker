param(
    [int]$Port = 0
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_env.ps1")

$resolved = Get-SyntaxCheckPort -Override $Port
$mcpUrl = Get-McpUrl -Port $resolved

@{
    mcpServers = @{
        "1c-syntax-checker-mcp" = @{
            url = $mcpUrl
            connection_id = "1c_lsp_service_001"
            description = "BSL syntax validation via BSL Language Server (open-source)"
        }
    }
} | ConvertTo-Json -Depth 5
