$root = "D:\MLEbotics\mlebotics.com"
Set-Location $root

# Pull latest from GitHub before starting servers
Write-Host "Running start-session..." -ForegroundColor White
& "C:\Users\Eddie\scripts\start-session.ps1" -SkipStash

# Install dependencies if node_modules is missing
if (-not (Test-Path "$root\node_modules")) {
    Write-Host "node_modules not found - running pnpm install..." -ForegroundColor Yellow
    pnpm install
    if ($LASTEXITCODE -ne 0) { Write-Host "pnpm install failed." -ForegroundColor Red; Read-Host "Press Enter to close"; exit 1 }
    Write-Host "Install complete." -ForegroundColor Green
}

$apps = @(
    @{ title="MARKETING"; cmd="pnpm run dev:marketing" },
    @{ title="CONSOLE";   cmd="pnpm run dev:console"   },
    @{ title="STUDIO";    cmd="pnpm run dev:studio"    },
    @{ title="DOCS";      cmd="pnpm run dev:docs"      }
)

Write-Host "Launching all MLEbotics dev servers..." -ForegroundColor White

foreach ($app in $apps) {
    $title = $app.title
    $cmd   = $app.cmd
    Start-Process powershell -ArgumentList @(
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-NoExit",
        "-File", "`"$root\dev-server.ps1`"",
        "-Title", "`"$title`"",
        "-Cmd", "`"$cmd`""
    )
    Write-Host "  [+] $title" -ForegroundColor Cyan
    Start-Sleep -Milliseconds 500
}

Write-Host "`nAll 4 servers launched in separate windows." -ForegroundColor Green
Write-Host "This window will close in 5 seconds..." -ForegroundColor DarkGray
Start-Sleep 5
