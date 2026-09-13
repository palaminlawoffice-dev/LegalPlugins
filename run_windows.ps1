$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
if (!(Test-Path .venv)) {
  py -3.12 -m venv .venv
}
& .\.venv\Scripts\python.exe -m pip install -U pip
& .\.venv\Scripts\python.exe -m pip install -e .
& .\.venv\Scripts\python.exe -m pytest -q
Write-Host "Thai Legal MCP is installed and tests passed."
Write-Host "Run Inspector: .\.venv\Scripts\python.exe -m mcp dev src\thai_legal_mcp\server.py"
