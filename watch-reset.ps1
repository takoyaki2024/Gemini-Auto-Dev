$ErrorActionPreference = 'SilentlyContinue'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$timeFile = Join-Path $root '.codex-reset-time.txt'
$pidFile = Join-Path $root '.codex-reset-watcher.pid'

if (-not (Test-Path $timeFile)) { exit 1 }

try {
    $target = [DateTime]::Parse((Get-Content $timeFile -Raw).Trim(), [System.Globalization.CultureInfo]::InvariantCulture, [System.Globalization.DateTimeStyles]::RoundtripKind)
} catch {
    exit 1
}

while ($true) {
    $remaining = $target - (Get-Date)
    if ($remaining.TotalSeconds -le 0) { break }
    $sleep = [Math]::Min([Math]::Max([int]$remaining.TotalSeconds, 1), 60)
    Start-Sleep -Seconds $sleep
}

try {
    Add-Type -AssemblyName PresentationFramework
    [System.Media.SystemSounds]::Exclamation.Play()
    [System.Windows.MessageBox]::Show(
        'Codex の5時間利用枠がリセット時刻になりました。Codexを再開できます。',
        'Codex Reset Notifier',
        [System.Windows.MessageBoxButton]::OK,
        [System.Windows.MessageBoxImage]::Information
    ) | Out-Null
} finally {
    Remove-Item $timeFile -Force -ErrorAction SilentlyContinue
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}
