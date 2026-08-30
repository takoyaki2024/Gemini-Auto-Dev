param(
    [Parameter(Mandatory=$true)]
    [string]$Workspace,
    [string]$Task = ''
)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

if (-not (Test-Path '.venv\Scripts\python.exe')) {
    throw 'Run .\setup.ps1 first.'
}

if (-not $env:GEMINI_API_KEY) {
    $env:GEMINI_API_KEY = [Environment]::GetEnvironmentVariable('GEMINI_API_KEY', 'User')
}

if (-not $env:GEMINI_API_KEY) {
    throw 'GEMINI_API_KEY is not configured. Run .\setup.ps1 first.'
}

if ($Task) {
    & '.\.venv\Scripts\python.exe' app.py $Workspace --task $Task
} else {
    & '.\.venv\Scripts\python.exe' app.py $Workspace
}

exit $LASTEXITCODE
