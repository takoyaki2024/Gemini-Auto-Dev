$ErrorActionPreference = 'SilentlyContinue'

$codexRoot = Join-Path $HOME '.codex'
$stateFile = Join-Path $PSScriptRoot '.codex-auto-last-reset.txt'
$pollSeconds = 30

function Parse-ResetTime([string]$text) {
    if ([string]::IsNullOrWhiteSpace($text)) { return $null }

    $patterns = @(
        '(?i)try again at\s+([A-Za-z]{3}\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}[, ]+\d{1,2}:\d{2}\s*(?:AM|PM))',
        '(?i)try again at\s+(\d{1,2}:\d{2}\s*(?:AM|PM))',
        '(?i)5h limit:.*?resets\s+(\d{1,2}:\d{2})'
    )

    foreach ($pattern in $patterns) {
        $m = [regex]::Match($text, $pattern)
        if (-not $m.Success) { continue }

        $raw = $m.Groups[1].Value.Trim()
        $raw = $raw -replace '(\d)(st|nd|rd|th)', '$1'
        $target = [DateTime]::MinValue

        if ([DateTime]::TryParse($raw, [System.Globalization.CultureInfo]::InvariantCulture, [System.Globalization.DateTimeStyles]::AssumeLocal, [ref]$target)) {
            if ($raw -notmatch '\d{4}') {
                $now = Get-Date
                $target = Get-Date -Year $now.Year -Month $now.Month -Day $now.Day -Hour $target.Hour -Minute $target.Minute -Second 0
                if ($target -le $now) { $target = $target.AddDays(1) }
            }
            return $target
        }
    }

    return $null
}

function Find-LatestResetTime {
    if (-not (Test-Path $codexRoot)) { return $null }

    $files = Get-ChildItem $codexRoot -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Length -le 10MB -and
            $_.Name -notin @('auth.json', 'config.toml') -and
            $_.Extension -in @('.jsonl', '.log', '.txt')
        } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 40

    foreach ($file in $files) {
        try {
            $tail = Get-Content $file.FullName -Tail 250 -ErrorAction Stop | Out-String
            $target = Parse-ResetTime $tail
            if ($target -and $target -gt (Get-Date)) { return $target }
        } catch { }
    }

    return $null
}

function Show-ResetNotification([DateTime]$target) {
    try {
        Add-Type -AssemblyName PresentationFramework
        [System.Media.SystemSounds]::Exclamation.Play()
        $message = 'Codex 5-hour usage window should now be reset. You can resume Codex.'
        $title = 'Codex Reset Notifier'
        [System.Windows.MessageBox]::Show(
            $message,
            $title,
            [System.Windows.MessageBoxButton]::OK,
            [System.Windows.MessageBoxImage]::Information
        ) | Out-Null
    } catch {
        Write-Host 'Codex reset time reached.'
    }
}

Write-Host 'Watching local Codex history for a 5-hour reset time. Press Ctrl+C to stop.'

while ($true) {
    $target = Find-LatestResetTime

    if ($target) {
        $key = $target.ToString('o')
        if (Test-Path $stateFile) {
            $last = (Get-Content $stateFile -Raw).Trim()
        } else {
            $last = ''
        }

        if ($key -ne $last) {
            Write-Host ('Detected reset time: ' + $target.ToString('yyyy-MM-dd HH:mm'))
            $key | Set-Content $stateFile -Encoding UTF8

            while ((Get-Date) -lt $target) {
                $remaining = $target - (Get-Date)
                $seconds = [Math]::Min([Math]::Max([int]$remaining.TotalSeconds, 1), 30)
                Start-Sleep -Seconds $seconds
            }

            Show-ResetNotification $target
        }
    }

    Start-Sleep -Seconds $pollSeconds
}
