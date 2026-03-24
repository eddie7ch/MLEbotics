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
    @{ title="Marketing"; cmd="pnpm run dev:marketing" },
    @{ title="Console";   cmd="pnpm run dev:console"   },
    @{ title="Studio";    cmd="pnpm run dev:studio"    },
    @{ title="Docs";      cmd="pnpm run dev:docs"      }
)

Write-Host "Launching all MLEbotics dev servers..." -ForegroundColor White

# Kill any leftover node processes on our ports before launching
$ports = @(3001, 3002, 3003, 54321)
foreach ($port in $ports) {
    $conn = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($conn) {
        Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
        Write-Host "  [~] Cleared old process on port $port" -ForegroundColor DarkYellow
    }
}

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
