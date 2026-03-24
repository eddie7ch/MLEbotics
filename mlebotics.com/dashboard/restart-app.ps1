# restart-app.ps1 — Kill and restart an app, capturing stdout/stderr to a log file
# Dot-source this from dashboard.ps1 to load Restart-App

function Restart-App {
    param(
        [pscustomobject]$AppStatus,   # from Get-AppStatus
        [pscustomobject]$AppConfig,   # from $APP_LIST (has .Cmd, .LogFile)
        [string]$Root                 # path to mlebotics.com root
    )

    $devServerScript = Join-Path $Root "dev-server.ps1"
    $logFile         = $AppConfig.LogFile
    $logDir          = Split-Path $logFile -Parent

    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }

    # Kill the existing process
    if ($AppStatus.PID) {
        Stop-Process -Id $AppStatus.PID -Force -ErrorAction SilentlyContinue
    }

    # Belt-and-suspenders: also clear the port in case the PID was stale
    $conn = Get-NetTCPConnection -LocalPort $AppConfig.Port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -First 1
    if ($conn) {
        Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
    }

    Start-Sleep -Milliseconds 600

    # Build the launch command as a Base64-encoded string to avoid quoting hell.
    # This wraps dev-server.ps1 (which handles crash-restart) and tees all output
    # to the log file so the dashboard can tail it with [L].
    $innerCmd = "& '$devServerScript' -Title '$($AppConfig.Name)' -Cmd '$($AppConfig.Cmd)' *>&1 | Tee-Object -FilePath '$logFile' -Append"
    $encoded  = [Convert]::ToBase64String([System.Text.Encoding]::Unicode.GetBytes($innerCmd))

    Start-Process powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -NoExit -EncodedCommand $encoded"

    return "Restarted $($AppConfig.Name) on :$($AppConfig.Port)"
}
