$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$python = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    $python = 'py'
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $python = 'python'
} else {
    throw 'Python was not found. Install Python and run setup.ps1 again.'
}

if (-not (Test-Path '.venv\Scripts\python.exe')) {
    Write-Host 'Creating virtual environment...'
    & $python -m venv .venv
}

Write-Host 'Installing dependencies...'
& '.\.venv\Scripts\python.exe' -m pip install --upgrade pip
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt

if (-not $env:GEMINI_API_KEY) {
    $secure = Read-Host 'Enter Gemini API key' -AsSecureString
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
        [Environment]::SetEnvironmentVariable('GEMINI_API_KEY', $plain, 'User')
        $env:GEMINI_API_KEY = $plain
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
        $plain = $null
    }
}

Write-Host 'Running tests...'
& '.\.venv\Scripts\python.exe' -m pytest -q
if ($LASTEXITCODE -ne 0) {
    throw 'Tests failed.'
}

Write-Host 'Setup complete.'
Write-Host 'Example:'
Write-Host '.\run.ps1 -Workspace D:\GitHub\YourProject -Task "Complete this project and run tests"'
