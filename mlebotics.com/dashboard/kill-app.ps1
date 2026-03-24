# kill-app.ps1 — Stop a running app by killing its process
# Dot-source this from dashboard.ps1 to load Stop-App

function Stop-App {
    param([pscustomobject]$AppStatus)

    if ($AppStatus.Status -eq "STOPPED") {
        return "$($AppStatus.Name) is already stopped"
    }

    # Kill by PID if known
    if ($AppStatus.PID) {
        Stop-Process -Id $AppStatus.PID -Force -ErrorAction SilentlyContinue
        return "Killed $($AppStatus.Name) (PID $($AppStatus.PID))"
    }

    # Fallback: kill whatever is holding the port
    $conn = Get-NetTCPConnection -LocalPort $AppStatus.Port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -First 1
    if ($conn) {
        Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
        return "Killed process on port $($AppStatus.Port)"
    }

    return "Nothing to kill for $($AppStatus.Name)"
}
