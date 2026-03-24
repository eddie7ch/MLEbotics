#!/usr/bin/env pwsh
# start-session.ps1 — Run this before starting work on any machine.
# Fetches latest changes and pulls with rebase to keep history linear.

Set-Location $PSScriptRoot
$branch = (git rev-parse --abbrev-ref HEAD 2>&1).Trim()

Write-Host ""
Write-Host "=== MLEbotics Session Start ===" -ForegroundColor Cyan
Write-Host "Branch : $branch" -ForegroundColor Gray
Write-Host "Machine: $env:COMPUTERNAME" -ForegroundColor Gray
Write-Host ""

# Warn if there are uncommitted local changes
$status = git status --porcelain 2>&1
if ($status) {
    Write-Host "WARNING: You have uncommitted changes:" -ForegroundColor Yellow
    git status --short
    Write-Host ""
    $answer = Read-Host "Stash them before pulling? (y/N)"
    if ($answer -match "^[Yy]$") {
        git stash push -m "auto-stash before session pull $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
        Write-Host "Stashed. Run 'git stash pop' to restore after pulling." -ForegroundColor Green
        Write-Host ""
    }
}

# Fetch + pull with rebase (safe for solo dev — keeps history clean)
Write-Host "Fetching from origin..." -ForegroundColor DarkCyan
git fetch origin

$behind = (git rev-list HEAD..origin/$branch --count 2>&1).Trim()
if ($behind -eq "0") {
    Write-Host "Already up to date. Nothing to pull." -ForegroundColor Green
} else {
    Write-Host "Pulling $behind new commit(s) from origin/$branch..." -ForegroundColor Cyan
    git pull --rebase origin $branch
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "CONFLICT during rebase. Fix conflicts, then run:" -ForegroundColor Red
        Write-Host "  git add <file>"  -ForegroundColor Yellow
        Write-Host "  git rebase --continue" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host ""
Write-Host "You're up to date. Happy coding!" -ForegroundColor Green
Write-Host ""
