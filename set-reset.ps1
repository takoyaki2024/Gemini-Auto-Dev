param(
    [string]$ResetTime
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$timeFile = Join-Path $root '.codex-reset-time.txt'
$pidFile = Join-Path $root '.codex-reset-watcher.pid'
$watcher = Join-Path $root 'watch-reset.ps1'

function Stop-OldWatcher {
    if (-not (Test-Path $pidFile)) { return }
    try {
        $oldPid = [int](Get-Content $pidFile -Raw)
        $process = Get-Process -Id $oldPid -ErrorAction SilentlyContinue
        if ($process) { Stop-Process -Id $oldPid -Force }
    } catch { }
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

if (-not $ResetTime) {
    $ResetTime = Read-Host 'Codex 5時間枠のリセット時刻を入力してください (HH:mm または yyyy-MM-dd HH:mm)'
}

$ResetTime = $ResetTime.Trim()
$culture = [System.Globalization.CultureInfo]::InvariantCulture
$styles = [System.Globalization.DateTimeStyles]::AssumeLocal
$target = $null

if ([DateTime]::TryParseExact($ResetTime, 'yyyy-MM-dd HH:mm', $culture, $styles, [ref]$target)) {
    # exact local date/time
} else {
    $timeOnly = [DateTime]::MinValue
    if (-not [DateTime]::TryParseExact($ResetTime, 'HH:mm', $culture, $styles, [ref]$timeOnly)) {
        Write-Host '形式が正しくありません。例: 23:40 または 2026-09-01 23:40' -ForegroundColor Red
        exit 1
    }
    $now = Get-Date
    $target = Get-Date -Year $now.Year -Month $now.Month -Day $now.Day -Hour $timeOnly.Hour -Minute $timeOnly.Minute -Second 0
    if ($target -le $now) { $target = $target.AddDays(1) }
}

if ($target -le (Get-Date)) {
    Write-Host '指定時刻はすでに過ぎています。' -ForegroundColor Red
    exit 1
}

Stop-OldWatcher
$target.ToString('o') | Set-Content $timeFile -Encoding UTF8

$process = Start-Process powershell.exe -WindowStyle Hidden -PassThru -ArgumentList @(
    '-NoProfile',
    '-ExecutionPolicy', 'Bypass',
    '-File', ('"' + $watcher + '"')
)
$process.Id | Set-Content $pidFile -Encoding ASCII

Write-Host ''
Write-Host ('通知を予約しました: ' + $target.ToString('yyyy-MM-dd HH:mm')) -ForegroundColor Green
Write-Host 'この画面は閉じて大丈夫です。'
