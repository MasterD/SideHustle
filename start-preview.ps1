$ErrorActionPreference = 'Stop'
$PreviewPythonPath = 'C:/Users/tiaan.botha/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$PreviewScriptPath = Join-Path $PSScriptRoot 'website/preview.py'
if (-not (Test-Path -LiteralPath $PreviewPythonPath)) {
    throw 'The existing bundled Python runtime is unavailable. Open this project in Codex and locate its workspace runtime before starting the preview.'
}
& $PreviewPythonPath $PreviewScriptPath
