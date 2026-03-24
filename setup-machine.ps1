# setup-machine.ps1
# Run this once on a new machine after cloning the MLEbotics repo.
# It installs the 3 session scripts, sets execution policy, adds aliases,
# and creates desktop shortcuts.

param(
    [string]$RepoRoot = $PSScriptRoot
)

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "  MLEbotics Machine Setup" -ForegroundColor White
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "  Repo root: $RepoRoot"
Write-Host ""

# ── 1. Execution policy ───────────────────────────────────────────────────────
Write-Host "[1/4] Setting execution policy to RemoteSigned..." -ForegroundColor Yellow
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
Write-Host "  OK" -ForegroundColor Green

# ── 2. Copy scripts ───────────────────────────────────────────────────────────
Write-Host "[2/4] Copying session scripts to C:\Users\$env:USERNAME\scripts\..." -ForegroundColor Yellow
$scriptsDir = "C:\Users\$env:USERNAME\scripts"
New-Item -ItemType Directory -Path $scriptsDir -Force | Out-Null

$src = Join-Path $RepoRoot "scripts"
Copy-Item "$src\start-session.ps1"  $scriptsDir -Force
Copy-Item "$src\end-session.ps1"    $scriptsDir -Force
Copy-Item "$src\close-project.ps1"  $scriptsDir -Force
Write-Host "  Copied: start-session.ps1, end-session.ps1, close-project.ps1" -ForegroundColor Green

# ── 3. PowerShell profile aliases ─────────────────────────────────────────────
Write-Host "[3/4] Adding aliases to PowerShell profile..." -ForegroundColor Yellow
$profilePath = $PROFILE.CurrentUserAllHosts
$profileDir  = Split-Path $profilePath -Parent
New-Item -ItemType Directory -Path $profileDir -Force | Out-Null

$aliases = @"

# ── MLEbotics session scripts ─────────────────────────────────────────────────
function Start-Session  { & "C:\Users\`$env:USERNAME\scripts\start-session.ps1"  @args }
function End-Session    { & "C:\Users\`$env:USERNAME\scripts\end-session.ps1"    @args }
function Close-Project  { & "C:\Users\`$env:USERNAME\scripts\close-project.ps1" @args }
Set-Alias start-session Start-Session
Set-Alias end-session   End-Session
Set-Alias close-project Close-Project
"@

$existing = if (Test-Path $profilePath) { Get-Content $profilePath -Raw } else { "" }
if ($existing -notmatch "MLEbotics session scripts") {
    Add-Content -Path $profilePath -Value $aliases
    Write-Host "  Aliases added to $profilePath" -ForegroundColor Green
} else {
    Write-Host "  Aliases already present — skipping." -ForegroundColor DarkGray
}

# ── 4. Desktop shortcuts ──────────────────────────────────────────────────────
Write-Host "[4/4] Creating desktop shortcuts..." -ForegroundColor Yellow
$desktop = [System.Environment]::GetFolderPath('Desktop')
$wsh     = New-Object -ComObject WScript.Shell

function New-Shortcut {
    param($Name, $Target, $Args, $Desc, $Icon)
    $lnk = $wsh.CreateShortcut("$desktop\$Name.lnk")
    $lnk.TargetPath       = $Target
    $lnk.Arguments        = $Args
    $lnk.Description      = $Desc
    if ($Icon) { $lnk.IconLocation = $Icon }
    $lnk.WindowStyle      = 1
    $lnk.Save()
    Write-Host "  Created: $Name.lnk" -ForegroundColor Green
}

# START SESSION — git pull & open dev servers
New-Shortcut `
    -Name "START SESSION" `
    -Target "powershell.exe" `
    -Args "-NoProfile -ExecutionPolicy Bypass -File `"$RepoRoot\mlebotics.com\dev-all.ps1`"" `
    -Desc "Pull latest and start all MLEbotics dev servers" `
    -Icon "%SystemRoot%\System32\shell32.dll,162"

# MLEbotics Project Starter — VS Code workspace
New-Shortcut `
    -Name "MLEbotics Project Starter" `
    -Target "code" `
    -Args "`"D:\MLEbotics\MLEbotics.code-workspace`"" `
    -Desc "Open MLEbotics workspace in VS Code" `
    -Icon "%SystemRoot%\System32\shell32.dll,21"

# Close Project — commit, push, close VS Code
New-Shortcut `
    -Name "Close Project" `
    -Target "powershell.exe" `
    -Args "-NoProfile -ExecutionPolicy Bypass -File `"C:\Users\$env:USERNAME\scripts\close-project.ps1`"" `
    -Desc "Commit, push and close VS Code" `
    -Icon "%SystemRoot%\System32\shell32.dll,131"

# ── Done ──────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "  Setup complete! Restart your terminal to pick up aliases." -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""
