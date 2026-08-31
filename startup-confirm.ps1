$ErrorActionPreference = 'SilentlyContinue'

$watcher = Join-Path $PSScriptRoot 'auto-watch.ps1'
if (-not (Test-Path $watcher)) { exit 1 }

Add-Type -AssemblyName PresentationFramework
$result = [System.Windows.MessageBox]::Show(
    'Start Codex Reset Notifier?',
    'Codex Reset Notifier',
    [System.Windows.MessageBoxButton]::YesNo,
    [System.Windows.MessageBoxImage]::Question
)

if ($result -ne [System.Windows.MessageBoxResult]::Yes) { exit 0 }

$existing = Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object {
    $_.CommandLine -and $_.CommandLine -like '*auto-watch.ps1*'
}
if ($existing) { exit 0 }

Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @(
    '-NoProfile',
    '-ExecutionPolicy', 'Bypass',
    '-File', ('"' + $watcher + '"')
)
