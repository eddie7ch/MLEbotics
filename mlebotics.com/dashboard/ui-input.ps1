# ui-input.ps1 — Non-blocking keyboard input
# Dot-source this from dashboard.ps1 to load Wait-ForInput

function Wait-ForInput {
    param([double]$TimeoutSeconds = 1.0)

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if ([Console]::KeyAvailable) {
            return [Console]::ReadKey($true)
        }
        Start-Sleep -Milliseconds 50
    }
    return $null
}
