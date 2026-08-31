$ErrorActionPreference = 'Stop'

$taskName = 'CodexResetNotifier'
$confirmScript = Join-Path $PSScriptRoot 'startup-confirm.ps1'

if (-not (Test-Path $confirmScript)) {
    Write-Host 'startup-confirm.ps1 was not found.' -ForegroundColor Red
    exit 1
}

$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -ExecutionPolicy Bypass -File "' + $confirmScript + '"')
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description 'Ask whether to start Codex Reset Notifier when signing in to Windows.' -Force | Out-Null

Write-Host ''
Write-Host 'Startup confirmation installed.' -ForegroundColor Green
Write-Host ('Task: ' + $taskName)
Write-Host ''
Write-Host 'At Windows sign-in, you will be asked whether to start Codex Reset Notifier.'
Write-Host 'Yes = start background watcher'
Write-Host 'No  = do nothing'
