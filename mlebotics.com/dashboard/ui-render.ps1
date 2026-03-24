# ui-render.ps1 — Dashboard rendering
# Dot-source this from dashboard.ps1 to load Render-Dashboard

# Tracks whether the next render should do a full Clear() instead of in-place overwrite
$script:dashboardFirstRender = $true

function Render-Dashboard {
    param(
        [array] $AppStatus,
        [int]   $SelectedIndex,
        [string]$StatusMessage = ""
    )

    $W   = [math]::Max(78, [Console]::WindowWidth - 1)
    $now = Get-Date -Format "HH:mm:ss"
    $sep = "-" * $W

    # Ln — writes a full-width padded line (no partial overwrites from previous frames)
    function Ln {
        param(
            [string]$Text = "",
            [string]$Fg   = "Gray",
            [string]$Bg   = ""
        )
        # Pad or truncate to exact width so stale characters from previous renders are erased
        $padded = $Text.PadRight($W)
        if ($padded.Length -gt $W) { $padded = $padded.Substring(0, $W) }
        if ($Bg) {
            Write-Host $padded -ForegroundColor $Fg -BackgroundColor $Bg
        } else {
            Write-Host $padded -ForegroundColor $Fg
        }
    }

    # First render: full clear to remove any shell prompt residue
    if ($script:dashboardFirstRender) {
        [Console]::Clear()
        $script:dashboardFirstRender = $false
    }

    # Move cursor to top-left — overwrite in place to avoid flicker
    [Console]::SetCursorPosition(0, 0)
    [Console]::CursorVisible = $false

    # ── Header ───────────────────────────────────────────────────────────────
    Ln $sep                                                   DarkGray
    Ln "  MLEbotics Dev Dashboard -- $now"                    White
    Ln $sep                                                   DarkGray
    Ln ("  {0,-16} {1,-10} {2,-8} {3,-8} {4}" -f "App", "Status", "Port", "CPU %", "Memory")  DarkGray
    Ln $sep                                                   DarkGray

    # ── App rows ─────────────────────────────────────────────────────────────
    for ($i = 0; $i -lt $AppStatus.Count; $i++) {
        $s   = $AppStatus[$i]
        $sel = ($i -eq $SelectedIndex)

        $portStr = if ($s.Port)             { "$($s.Port)"      } else { "-" }
        $cpuStr  = if ($null -ne $s.CPU)    { "$($s.CPU)%"      } else { "-" }
        $memStr  = if ($null -ne $s.Memory) { "$($s.Memory) MB" } else { "-" }
        $marker  = if ($sel)                { "> " }             else { "  " }

        $row = "  {0,-16} {1,-10} {2,-8} {3,-8} {4}" -f ($marker + $s.Name), $s.Status, $portStr, $cpuStr, $memStr

        if ($sel) {
            Ln $row White DarkBlue
        } else {
            $clr = switch ($s.Status) {
                "RUNNING"   { "Green"  }
                "STOPPED"   { "Red"    }
                "PORT OPEN" { "Yellow" }
                default     { "Yellow" }
            }
            Ln $row $clr
        }
    }

    # ── Footer ───────────────────────────────────────────────────────────────
    Ln $sep DarkGray
    Ln "  [Up/Dn] Navigate   [R] Restart   [K] Kill   [L] Logs   [A] Start All   [Q] Quit"  DarkGray
    Ln $sep DarkGray

    if ($StatusMessage) {
        Ln "  $StatusMessage" Yellow
    } else {
        Ln "  Refreshed $now  |  Select with Up/Dn, then press R / K / L" DarkGray
    }
}
