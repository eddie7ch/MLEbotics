#!/usr/bin/env pwsh
# end-session.ps1 — Run this before switching machines or ending work.
# Commits everything and pushes. Handles conflicts automatically.

Set-Location $PSScriptRoot
$branch = (git rev-parse --abbrev-ref HEAD 2>&1).Trim()

Write-Host ""
Write-Host "=== MLEbotics Safe Switch ===" -ForegroundColor Cyan
Write-Host "Branch : $branch" -ForegroundColor Gray
Write-Host "Machine: $env:COMPUTERNAME" -ForegroundColor Gray
Write-Host ""

# Check for anything to commit
$status = git status --porcelain 2>&1
if (-not $status) {
    Write-Host "Nothing to commit. Checking if push is needed..." -ForegroundColor Gray
} else {
    Write-Host "Changed files:" -ForegroundColor Yellow
    git status --short
    Write-Host ""

    # Prompt for commit message
    $default = "wip: session save $(Get-Date -Format 'yyyy-MM-dd HH:mm') [$env:COMPUTERNAME]"
    $msg = Read-Host "Commit message (Enter for default)"
    if ([string]::IsNullOrWhiteSpace($msg)) { $msg = $default }

    git add --all
    git commit -m $msg
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Commit failed. Check git status." -ForegroundColor Red
        exit 1
    }
    Write-Host ""
}

# Push — if rejected (another machine pushed), rebase then push
Write-Host "Pushing to origin/$branch..." -ForegroundColor Cyan
git push origin $branch 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Push rejected. Fetching and rebasing..." -ForegroundColor Yellow
    git fetch origin
    git rebase origin/$branch
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "CONFLICT during rebase. Resolve the conflicts, then run:" -ForegroundColor Red
        Write-Host "  git add <conflicted-file>" -ForegroundColor Yellow
        Write-Host "  git rebase --continue" -ForegroundColor Yellow
        Write-Host "  git push origin $branch" -ForegroundColor Yellow
        exit 1
    }
    # Retry push after successful rebase
    git push origin $branch
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Push still failed. Check your connection or remote access." -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "Pushed! Safe to switch machines." -ForegroundColor Green

# Show last 3 commits for confirmation
Write-Host ""
Write-Host "Latest commits:" -ForegroundColor DarkCyan
git log --oneline -3
Write-Host ""
