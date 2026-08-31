$ErrorActionPreference = 'Stop'

$taskName = 'CodexResetNotifier'
$watcher = Join-Path $PSScriptRoot 'auto-watch.ps1'

if (-not (Test-Path $watcher)) {
    Write-Host 'auto-watch.ps1 was not found.' -ForegroundColor Red
    exit 1
}

$escapedWatcher = $watcher.Replace('"', '""')
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $escapedWatcher + '"')
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description 'Automatically watches Codex local history and notifies when the 5-hour reset time arrives.' -Force | Out-Null
Start-ScheduledTask -TaskName $taskName
Start-Sleep -Seconds 2

$task = Get-ScheduledTask -TaskName $taskName
$info = Get-ScheduledTaskInfo -TaskName $taskName

Write-Host ''
Write-Host 'Codex Reset Notifier autostart installed.' -ForegroundColor Green
Write-Host ('Task: ' + $taskName)
Write-Host ('State: ' + $task.State)
Write-Host ('Last result: ' + $info.LastTaskResult)
Write-Host ''
Write-Host 'It will start automatically when you sign in to Windows.'
Write-Host 'The watcher runs hidden in the background.'
