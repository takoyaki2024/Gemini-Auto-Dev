$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$python = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    $python = 'py'
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $python = 'python'
} else {
    throw 'Python が見つかりません。Python をインストールしてから再実行してください。'
}

if (-not (Test-Path '.venv\Scripts\python.exe')) {
    & $python -m venv .venv
}

& '.\.venv\Scripts\python.exe' -m pip install --upgrade pip
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt

if (-not $env:GEMINI_API_KEY) {
    $secure = Read-Host 'Gemini API key を入力してください' -AsSecureString
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

& '.\.venv\Scripts\python.exe' -m pytest -q
Write-Host 'Setup complete.'
Write-Host '起動例: .\run.ps1 -Workspace D:\GitHub\YourProject -Task "このプロジェクトを完成させて"'
