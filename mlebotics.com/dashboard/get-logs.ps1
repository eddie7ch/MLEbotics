# get-logs.ps1 — Live log tail for the selected app
# Dot-source this from dashboard.ps1 to load Show-AppLogs

function Show-AppLogs {
    param(
        [pscustomobject]$AppStatus,
        [int]$TailLines = 30
    )

    [Console]::CursorVisible = $true
    [Console]::Clear()

    $W   = [math]::Max(80, [Console]::WindowWidth - 1)
    $sep = "-" * $W

    Write-Host $sep -ForegroundColor DarkGray
    Write-Host "  Log View: $($AppStatus.Name) -- Q or ESC to return" -ForegroundColor Cyan
    Write-Host $sep -ForegroundColor DarkGray
    Write-Host ""

    if (-not $AppStatus.LogFile -or -not (Test-Path $AppStatus.LogFile)) {
        Write-Host "  No log file found for $($AppStatus.Name)." -ForegroundColor DarkYellow
        Write-Host ""
        Write-Host "  Log capture is enabled when you restart an app via [R] in the dashboard." -ForegroundColor DarkGray
        Write-Host "  Apps started by dev-all.ps1 outside the dashboard do not write log files." -ForegroundColor DarkGray
        Write-Host ""
        Write-Host "  Press any key to return..." -ForegroundColor DarkGray
        $null = [Console]::ReadKey($true)
        [Console]::CursorVisible = $false
        return
    }

    Write-Host "  $($AppStatus.LogFile)" -ForegroundColor DarkGray
    Write-Host $sep -ForegroundColor DarkGray
    Write-Host ""

    # Show last N lines as history
    $history = Get-Content $AppStatus.LogFile -Tail $TailLines -ErrorAction SilentlyContinue
    if ($history) {
        foreach ($line in $history) {
            Write-Host "  $line" -ForegroundColor DarkGray
        }
    }

    Write-Host ""
    Write-Host "  --- Live tail (new lines appear below) ---" -ForegroundColor DarkGray
    Write-Host ""

    # Open file with ReadWrite share so the writing process is not blocked
    $stream = $null
    $reader = $null
    try {
        $stream = [System.IO.File]::Open(
            $AppStatus.LogFile,
            [System.IO.FileMode]::Open,
            [System.IO.FileAccess]::Read,
            [System.IO.FileShare]::ReadWrite
        )
        $reader = New-Object System.IO.StreamReader($stream)
        # Seek to end — we already showed history above
        $reader.BaseStream.Seek(0, [System.IO.SeekOrigin]::End) | Out-Null

        while ($true) {
            # Print any new lines written since last poll
            $line = $reader.ReadLine()
            while ($null -ne $line) {
                Write-Host "  $line" -ForegroundColor Gray
                $line = $reader.ReadLine()
            }

            # Non-blocking key check
            if ([Console]::KeyAvailable) {
                $k = [Console]::ReadKey($true)
                if ($k.Key -in @([ConsoleKey]::Q, [ConsoleKey]::Escape, [ConsoleKey]::Backspace)) {
                    break
                }
            }

            Start-Sleep -Milliseconds 250
        }
    } finally {
        if ($reader) { try { $reader.Close() } catch {} }
        if ($stream) { try { $stream.Close() } catch {} }
        [Console]::CursorVisible = $false
    }
}
