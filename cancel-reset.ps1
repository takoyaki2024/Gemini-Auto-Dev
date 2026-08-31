$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$timeFile = Join-Path $root '.codex-reset-time.txt'
$pidFile = Join-Path $root '.codex-reset-watcher.pid'

if (Test-Path $pidFile) {
    try {
        $watcherPid = [int](Get-Content $pidFile -Raw)
        $process = Get-Process -Id $watcherPid -ErrorAction SilentlyContinue
        if ($process) { Stop-Process -Id $watcherPid -Force }
    } catch { }
}

Remove-Item $timeFile -Force -ErrorAction SilentlyContinue
Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
Write-Host 'Codexリセット通知を取り消しました。'
