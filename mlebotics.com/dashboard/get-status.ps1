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
            LogFile    = $app.LogFile
            LastSeen   = $lastSeen
            SampleTime = $now
        })
    }

    return $results
}
