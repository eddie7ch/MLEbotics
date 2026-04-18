$root = "D:\MLEbotics\mlebotics.com"
Set-Location $root

$apps = @(
    @{ title="Marketing"; cmd="npm.cmd run start:marketing"; port=54321 },
    @{ title="Console";   cmd="npm.cmd run start:console";   port=3001  },
    @{ title="Studio";    cmd="npm.cmd run start:studio";    port=3002  },
    @{ title="Docs";      cmd="npm.cmd run start:docs";      port=3003  }
)

Write-Host "Launching all production servers..." -ForegroundColor White

foreach ($app in $apps) {
    $conn = Get-NetTCPConnection -LocalPort $app.port -ErrorAction SilentlyContinue
    if ($conn) {
        Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
        Write-Host "  [~] Cleared old process on port $($app.port)" -ForegroundColor DarkYellow
    }
}

foreach ($app in $apps) {
    Start-Process powershell -ArgumentList @(
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-NoExit",
        "-File", "`"$root\dev-server.ps1`"",
        "-Title", "`"$($app.title)`"",
        "-Cmd", "`"$($app.cmd)`""
    )
    Write-Host "  [+] $($app.title)" -ForegroundColor Cyan
    Start-Sleep -Milliseconds 500
}

Write-Host "`nAll production servers launched in separate windows." -ForegroundColor Green