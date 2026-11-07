param([string]$Label = "manual")

$ErrorActionPreference = "Stop"
$businessHubCheckpointTool = Join-Path $PSScriptRoot "tools\checkpoint.py"
$businessHubBundledPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$businessHubPythonCandidates = @()
if (Test-Path -LiteralPath $businessHubBundledPython) {
    $businessHubPythonCandidates += $businessHubBundledPython
}
$businessHubPythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($businessHubPythonCommand) { $businessHubPythonCandidates += $businessHubPythonCommand.Source }

foreach ($businessHubPythonPath in $businessHubPythonCandidates | Select-Object -Unique) {
    try {
        & $businessHubPythonPath -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" 2>$null
        if ($LASTEXITCODE -ne 0) { continue }
    } catch { continue }
    & $businessHubPythonPath $businessHubCheckpointTool --label $Label
    if ($LASTEXITCODE -ne 0) { throw "The restore point could not be saved. Check the error above." }
    exit 0
}

$businessHubPythonLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($businessHubPythonLauncher) {
    & $businessHubPythonLauncher.Source -3 $businessHubCheckpointTool --label $Label
    if ($LASTEXITCODE -eq 0) { exit 0 }
}
throw "A working Python 3.10+ runtime is required. No installation or purchase was attempted."
