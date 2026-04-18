# get-status.ps1 — App status detection
# Dot-source this from dashboard.ps1 to load Get-AppStatus

function Get-AppStatus {
    param(
        [array]     $AppList,
        [hashtable] $PrevCpuSamples = @{},
        [int]       $NumCores = 1
    )

    $now     = Get-Date
    $results = [System.Collections.Generic.List[pscustomobject]]::new()

    foreach ($app in $AppList) {
        # Check if anything is listening on this app's port
        $conn = Get-NetTCPConnection -LocalPort $app.Port -State Listen -ErrorAction SilentlyContinue |
                Select-Object -First 1

        if (-not $conn) {
            $results.Add([pscustomobject]@{
                Name       = $app.Name
                Port       = $app.Port
                Status     = "STOPPED"
                PID        = $null
                CPU        = $null
                CpuRaw     = $null
                Memory     = $null
                Uptime     = "-"
                ErrCount   = 0
                LogFile    = $app.LogFile
                LastSeen   = "-"
                SampleTime = $now
            })
            continue
        }

        $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue

        if (-not $proc) {
            # Port is open but the owning process isn't visible to Get-Process
            $results.Add([pscustomobject]@{
                Name       = $app.Name
                Port       = $app.Port
                Status     = "PORT OPEN"
                PID        = $conn.OwningProcess
                CPU        = $null
                CpuRaw     = $null
                Memory     = $null
                Uptime     = "-"
                ErrCount   = 0
                LogFile    = $app.LogFile
                LastSeen   = "-"
                SampleTime = $now
            })
            continue
        }

        # CPU% — delta from previous sample, normalised by core count
        $cpuPct = $null
        $cpuRaw = try { $proc.CPU } catch { $null }   # TotalProcessorTime in seconds

        if ($null -ne $cpuRaw -and $PrevCpuSamples.ContainsKey($proc.Id)) {
            $prev      = $PrevCpuSamples[$proc.Id]
            $cpuDelta  = $cpuRaw - $prev.CpuTime
            $timeDelta = ($now - $prev.Timestamp).TotalSeconds
            if ($timeDelta -gt 0 -and $cpuDelta -ge 0) {
                $raw    = ($cpuDelta / $timeDelta / [math]::Max(1, $NumCores)) * 100
                $cpuPct = [math]::Round([math]::Min($raw, 100.0), 1)
            }
        }

        $memMB = [math]::Round($proc.WorkingSet64 / 1MB, 0)

        # Uptime — how long the process has been alive
        $uptime = "-"
        try {
            $span = $now - $proc.StartTime
            if     ($span.TotalHours  -ge 1) { $uptime = "{0}h {1:D2}m" -f [int]$span.TotalHours, $span.Minutes }
            elseif ($span.TotalMinutes -ge 1) { $uptime = "{0}m {1:D2}s" -f [int]$span.TotalMinutes, $span.Seconds }
            else                              { $uptime = "{0}s"         -f $span.Seconds }
        } catch {}

        # Error count — scan last 300 lines of log for "error" (case-insensitive)
        $errCount = 0
        if ($app.LogFile -and (Test-Path $app.LogFile)) {
            try {
                $lines    = Get-Content $app.LogFile -Tail 300 -ErrorAction SilentlyContinue
                $errCount = ($lines | Where-Object { $_ -match '(?i)\berror\b' }).Count
            } catch {}
        }

        # Last activity indicator: log file write time (only exists after a dashboard-restart)
        $lastSeen = "-"
        if ($app.LogFile -and (Test-Path $app.LogFile)) {
            $lastSeen = (Get-Item $app.LogFile).LastWriteTime.ToString('HH:mm:ss')
        }

        $results.Add([pscustomobject]@{
            Name       = $app.Name
            Port       = $app.Port
            Status     = "RUNNING"
            PID        = $proc.Id
            CPU        = $cpuPct
            CpuRaw     = $cpuRaw
            Memory     = $memMB
            Uptime     = $uptime
            ErrCount   = $errCount
            LogFile    = $app.LogFile
            LastSeen   = $lastSeen
            SampleTime = $now
        })
    }

    return $results
}
