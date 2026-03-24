# dashboard.ps1 — MLEbotics Dev Dashboard
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File ".\dashboard\dashboard.ps1"
# Or from the mlebotics.com root:  .\dev-dashboard.ps1

Set-StrictMode -Off
$ErrorActionPreference = "SilentlyContinue"

$ROOT       = "D:\MLEbotics\mlebotics.com"
$SCRIPT_DIR = $PSScriptRoot
$LOG_DIR    = Join-Path $SCRIPT_DIR "logs"

# ── App configuration ─────────────────────────────────────────────────────────
# Ports match the definitions in dev-restart.ps1 and the individual app package.json files:
#   Marketing → Astro  :54321
#   Console   → Next.js :3001
#   Studio    → Next.js :3002
#   Docs      → Next.js :3003

$APP_LIST = @(
    [pscustomobject]@{ Name="Marketing"; Port=54321; Cmd="pnpm run dev:marketing" },
    [pscustomobject]@{ Name="Console";   Port=3001;  Cmd="pnpm run dev:console"   },
    [pscustomobject]@{ Name="Studio";    Port=3002;  Cmd="pnpm run dev:studio"    },
    [pscustomobject]@{ Name="Docs";      Port=3003;  Cmd="pnpm run dev:docs"      }
)

# Attach log-file path to each app entry
foreach ($a in $APP_LIST) {
    $a | Add-Member -MemberType NoteProperty -Name LogFile `
         -Value (Join-Path $LOG_DIR "$($a.Name).log") -Force
}

# ── Load modules (dot-source so functions live in this scope) ─────────────────
. (Join-Path $SCRIPT_DIR "get-status.ps1")
. (Join-Path $SCRIPT_DIR "get-logs.ps1")
. (Join-Path $SCRIPT_DIR "restart-app.ps1")
. (Join-Path $SCRIPT_DIR "kill-app.ps1")
. (Join-Path $SCRIPT_DIR "ui-render.ps1")
. (Join-Path $SCRIPT_DIR "ui-input.ps1")

# Ensure log directory exists
if (-not (Test-Path $LOG_DIR)) {
    New-Item -ItemType Directory -Path $LOG_DIR -Force | Out-Null
}

# ── Dashboard state ───────────────────────────────────────────────────────────
$selectedIndex = 0
$statusMessage = ""
$msgClearAt    = $null
$cpuCache      = @{}    # pid → @{ CpuTime; Timestamp }  used for CPU% calculation
$appStatus     = @()
$running       = $true

# ── Main loop ─────────────────────────────────────────────────────────────────
try {
    while ($running) {

        # ── Refresh status ────────────────────────────────────────────────────
        $appStatus = Get-AppStatus -AppList $APP_LIST -PrevCpuSamples $cpuCache `
                                   -NumCores ([Environment]::ProcessorCount)

        # Update CPU cache for next frame's delta calculation
        foreach ($s in $appStatus) {
            if ($s.PID -and $null -ne $s.CpuRaw) {
                $cpuCache[$s.PID] = @{ CpuTime = $s.CpuRaw; Timestamp = $s.SampleTime }
            }
        }

        # Auto-clear status message after 4 seconds
        if ($msgClearAt -and (Get-Date) -gt $msgClearAt) {
            $statusMessage = ""
            $msgClearAt    = $null
        }

        # ── Render ────────────────────────────────────────────────────────────
        Render-Dashboard -AppStatus $appStatus -SelectedIndex $selectedIndex `
                         -StatusMessage $statusMessage

        # ── Input (non-blocking, polls up to 1 s before next status refresh) ─
        $key = Wait-ForInput -TimeoutSeconds 1.0
        if ($null -eq $key) { continue }

        switch ($key.Key) {

            ([ConsoleKey]::UpArrow) {
                $selectedIndex = [math]::Max(0, $selectedIndex - 1)
            }

            ([ConsoleKey]::DownArrow) {
                $selectedIndex = [math]::Min($APP_LIST.Count - 1, $selectedIndex + 1)
            }

            ([ConsoleKey]::Home) { $selectedIndex = 0 }
            ([ConsoleKey]::End)  { $selectedIndex = $APP_LIST.Count - 1 }

            # ── [R] Restart selected app ──────────────────────────────────────
            ([ConsoleKey]::R) {
                $cfg    = $APP_LIST[$selectedIndex]
                $status = $appStatus[$selectedIndex]
                $msg    = Restart-App -AppStatus $status -AppConfig $cfg -Root $ROOT
                $statusMessage = "[R] $msg"
                $msgClearAt    = (Get-Date).AddSeconds(4)
            }

            # ── [K] Kill selected app ─────────────────────────────────────────
            ([ConsoleKey]::K) {
                $status        = $appStatus[$selectedIndex]
                $msg           = Stop-App -AppStatus $status
                $statusMessage = "[K] $msg"
                $msgClearAt    = (Get-Date).AddSeconds(4)
            }

            # ── [L] View logs for selected app ────────────────────────────────
            ([ConsoleKey]::L) {
                Show-AppLogs -AppStatus $appStatus[$selectedIndex]
                # Force a full Clear() on the next render to erase the log view
                $script:dashboardFirstRender = $true
            }

            # ── [A] Start all stopped apps ────────────────────────────────────
            ([ConsoleKey]::A) {
                $started = 0
                for ($i = 0; $i -lt $APP_LIST.Count; $i++) {
                    if ($appStatus[$i].Status -eq "STOPPED") {
                        Restart-App -AppStatus $appStatus[$i] -AppConfig $APP_LIST[$i] `
                                    -Root $ROOT | Out-Null
                        $started++
                        Start-Sleep -Milliseconds 400
                    }
                }
                $statusMessage = if ($started -eq 0) {
                    "[A] All apps are already running"
                } else {
                    "[A] Started $started stopped app(s)"
                }
                $msgClearAt = (Get-Date).AddSeconds(4)
            }

            # ── [Q] / ESC — exit dashboard ────────────────────────────────────
            ([ConsoleKey]::Q)      { $running = $false }
            ([ConsoleKey]::Escape) { $running = $false }
        }
    }

} finally {
    [Console]::CursorVisible = $true
    [Console]::Clear()
    Write-Host "MLEbotics Dev Dashboard closed." -ForegroundColor DarkGray
}
