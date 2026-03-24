# dev-server.ps1 — runs a single MLEbotics dev server with auto-restart on crash
param(
    [Parameter(Mandatory)][string]$Title,
    [Parameter(Mandatory)][string]$Cmd
)

$root = "D:\MLEbotics\mlebotics.com"
Set-Location $root
[System.Console]::Title = $Title

# Background runspace that keeps forcing the title back every 500ms
# (Node.js/Next.js overrides the title via ANSI escape sequences)
$rs = [System.Management.Automation.Runspaces.RunspaceFactory]::CreateRunspace()
$rs.Open()
$rs.SessionStateProxy.SetVariable('t', $Title)
$ps = [System.Management.Automation.PowerShell]::Create()
$ps.Runspace = $rs
$null = $ps.AddScript({ while ($true) { [System.Console]::Title = $t; Start-Sleep -Milliseconds 500 } }).BeginInvoke()

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
