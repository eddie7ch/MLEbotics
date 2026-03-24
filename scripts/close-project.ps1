# close-project.ps1 — commit, push, then close VS Code
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host "  Saving & closing project..." -ForegroundColor White
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host ""

# Run end-session (commit + push) with auto-generated message
& "C:\Users\Eddie\scripts\end-session.ps1" -AutoCommit

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Push failed — NOT closing VS Code." -ForegroundColor Red
    Write-Host "Fix the issue and try again." -ForegroundColor Red
    Read-Host "Press Enter to close this window"
    exit 1
}

Write-Host ""
Write-Host "Push successful. Closing VS Code in 3 seconds..." -ForegroundColor Green
Start-Sleep 3

# Close VS Code
Get-Process -Name Code -ErrorAction SilentlyContinue | Stop-Process -Force
