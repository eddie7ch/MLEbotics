# dev-server.ps1 — runs a single MLEbotics dev server with auto-restart on crash
param(
    [Parameter(Mandatory)][string]$Title,
    [Parameter(Mandatory)][string]$Cmd
)

$root = "D:\MLEbotics\mlebotics.com"
Set-Location $root
[System.Console]::Title = $Title

function Add-NodeToPath {
    $nodeDirs = @(
        "C:\Program Files\nodejs",
        "$env:LOCALAPPDATA\Programs\nodejs"
    )

    foreach ($dir in $nodeDirs) {
        if ((Test-Path $dir) -and ($env:Path -notlike "*$dir*")) {
            $env:Path += ";$dir"
        }
    }
}

function Get-PnpmCommand {
    $pnpmCmd = Get-Command pnpm.cmd -ErrorAction SilentlyContinue
    if ($pnpmCmd) { return "& '$($pnpmCmd.Source)'" }

    $pnpm = Get-Command pnpm -ErrorAction SilentlyContinue
    if ($pnpm) { return "& '$($pnpm.Source)'" }

    $corepackCmd = Get-Command corepack.cmd -ErrorAction SilentlyContinue
    if ($corepackCmd) { return "& '$($corepackCmd.Source)' pnpm" }

    $corepack = Get-Command corepack -ErrorAction SilentlyContinue
    if ($corepack) { return "& '$($corepack.Source)' pnpm" }

    throw 'pnpm/corepack not found. Install Node.js LTS or enable Corepack first.'
}

Add-NodeToPath
$pnpm = Get-PnpmCommand
if ($Cmd -match '^pnpm(?:\.cmd)?\s+') {
    $Cmd = $Cmd -replace '^(?:[^\s]+\\)?pnpm(?:\.cmd)?', $pnpm
}

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
        Write-Host "  [$Title] Server stopped. Restarting in 3 seconds..." -ForegroundColor Yellow
        Write-Host "  Close this window to stop permanently." -ForegroundColor DarkGray
    } else {
        Write-Host "  [$Title] Server crashed (exit: $exitCode). Restarting in 3 seconds..." -ForegroundColor Red
        Write-Host "  Close this window to stop permanently." -ForegroundColor DarkGray
    }
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
    Start-Sleep 3
}
