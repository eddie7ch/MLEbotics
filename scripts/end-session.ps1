param(
    [switch]$AutoCommit
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

    git add -A
    $staged = git diff --cached --name-only
    $machine = $env:COMPUTERNAME
    $date = (Get-Date).ToString('yyyy-MM-dd_HH-mm-ss')
    $default = "wip: session save $date [$machine]"
    if ($AutoCommit) {
        $msg = $default
        Write-Host "Auto commit message: $msg"
    } else {
        $msg = Read-Host "Commit message (default: $default)"
        if ($msg -eq '') { $msg = $default }
    }

    if ($staged) {
        # VS Code's git extension holds COMMIT_EDITMSG open — rename it away so git can create a fresh one
        $gitDir = (git rev-parse --absolute-git-dir)
        Remove-Item "$gitDir\COMMIT_EDITMSG.old" -ErrorAction SilentlyContinue
        Rename-Item "$gitDir\COMMIT_EDITMSG" "$gitDir\COMMIT_EDITMSG.old" -ErrorAction SilentlyContinue
        git commit -m "$msg"
        if ($LASTEXITCODE -ne 0) { Write-Host 'Commit failed or nothing to commit.' }
    } else {
        Write-Host 'No staged changes to commit.'
    }

    git fetch --no-write-fetch-head origin
    git rebase origin/main
    if ($LASTEXITCODE -ne 0) { Write-Host 'Rebase failed. Resolve conflicts, then run `git rebase --continue`.'; exit 2 }

    git push origin main
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'Push rejected; fetching + rebasing and retrying...'
        git fetch --no-write-fetch-head origin
        git rebase origin/main
        git push origin main
    }

    Write-Host 'Push complete. Last 3 commits:'
    git --no-pager log -n 3 --oneline
} catch {
    Write-Host "Error: $_"; exit 1
}
