# dev-server.ps1 — runs a single MLEbotics dev server with auto-restart on crash
param(
    [Parameter(Mandatory)][string]$Title,
    [Parameter(Mandatory)][string]$Cmd
)

$root = "D:\MLEbotics\mlebotics.com"
Set-Location $root
[System.Console]::Title = $Title

# Background timer — resets title every 2s because Next.js overrides it on startup
$callback = [System.Threading.TimerCallback]{ param($t) try { [System.Console]::Title = $t } catch {} }
$timer = New-Object System.Threading.Timer($callback, $Title, 2000, 2000)

while ($true) {
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
    Write-Host "  [$Title] Starting..." -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
    Write-Host ""

    Invoke-Expression $Cmd
    $exitCode = $LASTEXITCODE

    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray

    if ($exitCode -eq 0) {
        Write-Host "  [$Title] Server stopped cleanly (exit: 0)." -ForegroundColor Green
        Write-Host "  Not restarting. Close this window or press Enter." -ForegroundColor DarkGray
        Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
        Read-Host
        break
    } else {
        Write-Host "  [$Title] Server crashed (exit: $exitCode)" -ForegroundColor Yellow
        Write-Host "  Restarting in 3 seconds..." -ForegroundColor DarkGray
        Write-Host "  Close this window to stop permanently." -ForegroundColor DarkGray
        Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
        Start-Sleep 3
    }
}
