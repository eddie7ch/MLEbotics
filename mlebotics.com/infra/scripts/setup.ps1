# setup.ps1 — first-time project setup (Windows)

Write-Host "🔧 MLEbotics monorepo setup" -ForegroundColor Cyan

function Get-PnpmCommand {
    $pnpmCmd = Get-Command pnpm.cmd -ErrorAction SilentlyContinue
    if ($pnpmCmd) { return "& '$($pnpmCmd.Source)'" }

    $pnpm = Get-Command pnpm -ErrorAction SilentlyContinue
    if ($pnpm) { return "& '$($pnpm.Source)'" }

    $corepackCmd = Get-Command corepack.cmd -ErrorAction SilentlyContinue
    if ($corepackCmd) { return "& '$($corepackCmd.Source)' pnpm" }

    $corepack = Get-Command corepack -ErrorAction SilentlyContinue
    if ($corepack) { return "& '$($corepack.Source)' pnpm" }

    return $null
}

# Check required tools
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Node.js not found. Install v20+" -ForegroundColor Red; exit 1
}
$pnpm = Get-PnpmCommand
if (-not $pnpm) {
    Write-Host "❌ pnpm not found. Enable Corepack or run: npm install -g pnpm" -ForegroundColor Red; exit 1
}

# Install dependencies
Write-Host "📦 Installing dependencies..."
Invoke-Expression "$pnpm install"

# Copy env if missing
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "✅ Created .env from .env.example" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "✅ Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "  pnpm dev              — start all apps"
Write-Host "  pnpm dev:web          — start dashboard only (localhost:3001)"
Write-Host "  pnpm dev:marketing    — start marketing site only (localhost:4321)"
