$ErrorActionPreference = 'Stop'

$inputTime = Read-Host 'Start time (H:mm or HH:mm)'
$parsed = [DateTime]::MinValue
$formats = @('H:mm', 'HH:mm')

if (-not [DateTime]::TryParseExact(
    $inputTime.Trim(),
    $formats,
    [System.Globalization.CultureInfo]::InvariantCulture,
    [System.Globalization.DateTimeStyles]::None,
    [ref]$parsed
)) {
    Write-Host 'Invalid time. Example: 0:59 or 20:30' -ForegroundColor Red
    exit 1
}

$now = Get-Date
$start = Get-Date -Year $now.Year -Month $now.Month -Day $now.Day -Hour $parsed.Hour -Minute $parsed.Minute -Second 0

# The entered time is treated as the most recent occurrence of that clock time.
if ($start -gt $now) {
    $start = $start.AddDays(-1)
}

$target = $start.AddHours(5)

Write-Host ''
Write-Host ('Start : ' + $start.ToString('yyyy-MM-dd HH:mm'))
Write-Host ('Notify: ' + $target.ToString('yyyy-MM-dd HH:mm')) -ForegroundColor Green
Write-Host ''

if ($target -gt $now) {
    while ((Get-Date) -lt $target) {
        $remaining = $target - (Get-Date)
        $seconds = [Math]::Min([Math]::Max([int]$remaining.TotalSeconds, 1), 30)
        Start-Sleep -Seconds $seconds
    }
} else {
    Write-Host 'Five hours have already passed. Notifying now.' -ForegroundColor Yellow
}

Add-Type -AssemblyName PresentationFramework
[System.Media.SystemSounds]::Exclamation.Play()
[System.Windows.MessageBox]::Show(
    '5 hours have passed since the entered start time.',
    'Codex 5-Hour Timer',
    [System.Windows.MessageBoxButton]::OK,
    [System.Windows.MessageBoxImage]::Information
) | Out-Null
