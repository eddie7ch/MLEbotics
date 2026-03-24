# dev-restart.ps1 — restart one or all MLEbotics dev servers
$root = "D:\MLEbotics\mlebotics.com"

$apps = @(
    @{ num=1; title="MARKETING"; cmd="pnpm run dev:marketing" },
    @{ num=2; title="CONSOLE";   cmd="pnpm run dev:console"   },
    @{ num=3; title="STUDIO";    cmd="pnpm run dev:studio"    },
    @{ num=4; title="DOCS";      cmd="pnpm run dev:docs"      }
)

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host "  MLEbotics — Restart Dev Server" -ForegroundColor White
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host ""
foreach ($app in $apps) {
    Write-Host "  [$($app.num)] $($app.title)" -ForegroundColor Cyan
}
Write-Host "  [A] All servers" -ForegroundColor Green
Write-Host ""

$choice = Read-Host "Enter choice"

function Start-Server($app) {
    Write-Host "  Launching $($app.title)..." -ForegroundColor Cyan
    Start-Process powershell -ArgumentList @(
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-NoExit",
        "-File", "`"$root\dev-server.ps1`"",
        "-Title", "`"$($app.title)`"",
        "-Cmd", "`"$($app.cmd)`""
    )
}

if ($choice -match '^[Aa]$') {
    foreach ($app in $apps) {
        Start-Server $app
        Start-Sleep -Milliseconds 500
    }
    Write-Host ""
    Write-Host "All servers restarted." -ForegroundColor Green
} else {
    $num = [int]$choice
    $selected = $apps | Where-Object { $_.num -eq $num }
    if ($selected) {
        Start-Server $selected
        Write-Host ""
        Write-Host "$($selected.title) restarted." -ForegroundColor Green
    } else {
        Write-Host "Invalid choice." -ForegroundColor Red
    }
}

Start-Sleep 2
