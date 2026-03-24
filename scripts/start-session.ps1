param(
    [switch]$SkipStash
)
try {
    $repo = (git rev-parse --show-toplevel 2>$null)
    if (-not $repo) {
        $candidates = @(
            'D:\\MLEbotics',
            'C:\\MLEbotics',
            "C:\\Users\\$env:USERNAME\\MLEbotics",
            "C:\\Users\\$env:USERNAME\\Documents\\MLEbotics"
        )
        foreach ($p in $candidates) { if (Test-Path $p) { $repo = $p; break } }
    }
    if (-not $repo) { Write-Host 'Not inside a git repository.'; exit 1 }
    Set-Location -Path $repo
    Write-Host "Repository: $repo"

    $status = git status --porcelain
    if ($status) {
        if ($SkipStash) {
            Write-Host 'Uncommitted changes detected - skipping stash, pulling anyway.'
        } else {
            Write-Host 'Uncommitted changes detected.'
            $resp = Read-Host 'Stash changes before pulling? (Y/n)'
            if ($resp -match '^[Yy]$' -or $resp -eq '') {
                git stash push -m "auto-stash start-session $(Get-Date -Format u)"
                Write-Host 'Changes stashed.'
            } else {
                Write-Host 'Skipping stash, pulling anyway.'
            }
        }
    }

    git fetch --no-write-fetch-head origin
    if ($LASTEXITCODE -ne 0) { Write-Host 'Fetch failed.'; exit 3 }
    git checkout main
    if ($LASTEXITCODE -ne 0) { Write-Host 'Failed to checkout main.'; exit 3 }
    git rebase origin/main
    if ($LASTEXITCODE -ne 0) { Write-Host 'Rebase failed. Resolve conflicts, then run `git rebase --continue`.'; exit 4 }
    Write-Host 'Repository is up-to-date on main.'
} catch {
    Write-Host "Error: $_"; exit 1
}
