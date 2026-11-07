param([int]$Port = 8765)
$ErrorActionPreference = 'Stop'
$sideHustlePython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (-not (Test-Path -LiteralPath $sideHustlePython)) {
    throw 'The bundled Python runtime was not found. Run dashboard/server.py with an installed Python 3.10+ runtime.'
}
Write-Host "Open http://127.0.0.1:$Port in Codex or your browser. Close this process to stop the monitor."
& $sideHustlePython (Join-Path $PSScriptRoot 'dashboard\server.py') --port $Port

