@echo off
powershell.exe -NoProfile -Command "$t=Get-ScheduledTask -TaskName 'CodexResetNotifier' -ErrorAction SilentlyContinue; if(-not $t){Write-Host 'NOT INSTALLED' -ForegroundColor Red; exit}; $i=Get-ScheduledTaskInfo -TaskName 'CodexResetNotifier'; Write-Host ('State: '+$t.State); Write-Host ('Last run: '+$i.LastRunTime); Write-Host ('Last result: '+$i.LastTaskResult); if($t.State -eq 'Running'){Write-Host 'BACKGROUND WATCHER IS RUNNING' -ForegroundColor Green}"
pause
