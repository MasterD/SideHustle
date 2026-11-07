param(
    [int]$Port = 8787
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

# Prefer the bundled Codex runtime when present. A Windows python alias can
# open the Store, so only try installed commands after this known runtime.
$candidatePaths = @()
$bundledPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if (Test-Path -LiteralPath $bundledPython) { $candidatePaths += $bundledPython }
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCommand) { $candidatePaths += $pythonCommand.Source }

foreach ($candidatePath in $candidatePaths | Select-Object -Unique) {
    try {
        & $candidatePath -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Using Python: $candidatePath"
            & $candidatePath -u (Join-Path $PSScriptRoot "server.py") --port $Port
            exit $LASTEXITCODE
        }
    } catch {
        # Try the next runtime; no package or Python installation is attempted.
    }
}

$pythonLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($pythonLauncher) {
    & $pythonLauncher.Source -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Using Python launcher: $($pythonLauncher.Source) -3"
        & $pythonLauncher.Source -3 -u (Join-Path $PSScriptRoot "server.py") --port $Port
        exit $LASTEXITCODE
    }
}

throw "Python 3.10 or newer is required. No installation or spending was attempted."
