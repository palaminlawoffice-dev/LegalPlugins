$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
if (!(Test-Path .venv)) { py -3.12 -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install -U pip
& .\.venv\Scripts\python.exe -m pip install -e .
if (!(Test-Path .env)) { Copy-Item .env.example .env }
Write-Host "Set MCP_AUTH_TOKEN in .env, then run:" -ForegroundColor Yellow
Write-Host '$env:MCP_TRANSPORT="http"; $env:MCP_AUTH_TOKEN="YOUR_TOKEN"; .\.venv\Scripts\python.exe -m thai_legal_mcp.server'
