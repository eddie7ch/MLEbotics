$root = "D:\MLEbotics\mlebotics.com"
Set-Location $root

function Add-NodeToPath {
    $nodeDirs = @(
        "C:\Program Files\nodejs",
        "$env:LOCALAPPDATA\Programs\nodejs"
    )

    foreach ($dir in $nodeDirs) {
        if ((Test-Path $dir) -and ($env:Path -notlike "*$dir*")) {
            $env:Path += ";$dir"
        }
    }
}

function Get-PnpmCommand {
    $pnpmCmd = Get-Command pnpm.cmd -ErrorAction SilentlyContinue
    if ($pnpmCmd) { return "& '$($pnpmCmd.Source)'" }

    $pnpm = Get-Command pnpm -ErrorAction SilentlyContinue
    if ($pnpm) { return "& '$($pnpm.Source)'" }

    $corepackCmd = Get-Command corepack.cmd -ErrorAction SilentlyContinue
    if ($corepackCmd) { return "& '$($corepackCmd.Source)' pnpm" }

    $corepack = Get-Command corepack -ErrorAction SilentlyContinue
    if ($corepack) { return "& '$($corepack.Source)' pnpm" }

    throw 'pnpm/corepack not found. Install Node.js LTS or enable Corepack first.'
}

Add-NodeToPath
$pnpm = Get-PnpmCommand
$workspaceRoot = Split-Path $root -Parent
$sessionScript = Join-Path $workspaceRoot "scripts\start-session.ps1"

if (-not (Test-Path $sessionScript)) {
    $sessionScript = Join-Path $workspaceRoot "start-session.ps1"
}

# Pull latest from GitHub before starting servers
Write-Host "Running start-session..." -ForegroundColor White
if (Test-Path $sessionScript) {
    $workspaceStatus = git -C $workspaceRoot status --porcelain 2>$null
    if ($workspaceStatus) {
        Write-Host "Workspace has uncommitted changes - skipping pull step." -ForegroundColor Yellow
    } else {
    & $sessionScript -SkipStash
    if ($LASTEXITCODE -ne 0) {
        Write-Host "start-session failed." -ForegroundColor Red
        Read-Host "Press Enter to close"
        exit 1
    }
    }
} else {
    Write-Host "start-session script not found - skipping pull step." -ForegroundColor Yellow
}

# Install dependencies if node_modules is missing
if (-not (Test-Path "$root\node_modules")) {
    Write-Host "node_modules not found - running pnpm install..." -ForegroundColor Yellow
    Invoke-Expression "$pnpm install"
    if ($LASTEXITCODE -ne 0) { Write-Host "pnpm install failed." -ForegroundColor Red; Read-Host "Press Enter to close"; exit 1 }
    Write-Host "Install complete." -ForegroundColor Green
}

# Read ports dynamically from each app's package.json so this script
# always stays in sync if a port is changed there.
function Get-AppPort($appFolder, $defaultPort) {
    $pkg = Get-Content "$root\apps\$appFolder\package.json" -Raw | ConvertFrom-Json
    $devScript = $pkg.scripts.dev
    if ($devScript -match '--port\s+(\d+)') { return [int]$Matches[1] }
    return $defaultPort
}

$apps = @(
    @{ title="Marketing"; cmd="$pnpm run dev:marketing"; folder="marketing"; defaultPort=54321 },
    @{ title="Console";   cmd="$pnpm run dev:console";   folder="console";   defaultPort=3001  },
    @{ title="Studio";    cmd="$pnpm run dev:studio";    folder="studio";    defaultPort=3002  },
    @{ title="Docs";      cmd="$pnpm run dev:docs";      folder="docs";      defaultPort=3003  }
)

# Resolve actual ports from package.json (falls back to defaultPort if not found)
foreach ($app in $apps) {
    $app.port = Get-AppPort $app.folder $app.defaultPort
}

Write-Host "Launching all MLEbotics dev servers..." -ForegroundColor White

# Kill any leftover node processes on our ports before launching
foreach ($app in $apps) {
    $conn = Get-NetTCPConnection -LocalPort $app.port -ErrorAction SilentlyContinue
    if ($conn) {
        Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
        Write-Host "  [~] Cleared old process on port $($app.port)" -ForegroundColor DarkYellow
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

# Open the MLEbotics workspace in VS Code
Write-Host "Opening VS Code workspace..." -ForegroundColor White
Start-Process "code" -ArgumentList "`"D:\MLEbotics\MLEbotics.code-workspace`""

# Wait for servers to be ready, then open all sites in Edge
Write-Host "Waiting for servers to be ready..." -ForegroundColor DarkGray
$edgePath = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
$timeout = 60
foreach ($site in $apps) {
    $ready = $false
    $elapsed = 0
    while (-not $ready -and $elapsed -lt $timeout) {
        try {
            $tcp = New-Object System.Net.Sockets.TcpClient
            $tcp.Connect("localhost", $site.port)
            $tcp.Close()
            $ready = $true
        } catch {
            Start-Sleep -Seconds 1
            $elapsed++
        }
    }
    if ($ready) {
        Write-Host "  [>] Opening $($site.title) at localhost:$($site.port)" -ForegroundColor Cyan
        Start-Process $edgePath -ArgumentList "http://localhost:$($site.port)"
        Start-Sleep -Milliseconds 400
    } else {
        Write-Host "  [!] $($site.title) did not respond after ${timeout}s — skipping" -ForegroundColor Yellow
    }
}

Write-Host "This window will close in 5 seconds..." -ForegroundColor DarkGray
Start-Sleep 5
