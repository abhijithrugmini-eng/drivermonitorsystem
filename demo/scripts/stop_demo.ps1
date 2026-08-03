<#
.SYNOPSIS
    Stops the backend and UI processes started by demo/start_demo.ps1.
#>

$PidFile = Join-Path $PSScriptRoot ".demo_pids.json"

if (-not (Test-Path $PidFile)) {
    Write-Host "No record of a running demo (missing demo/.demo_pids.json). Nothing to stop." -ForegroundColor Yellow
    exit 0
}

$pids = Get-Content $PidFile -Raw | ConvertFrom-Json

foreach ($entry in @(@{name="backend"; id=$pids.backend}, @{name="ui"; id=$pids.ui})) {
    $proc = Get-Process -Id $entry.id -ErrorAction SilentlyContinue
    if ($proc) {
        Stop-Process -Id $entry.id -Force
        Write-Host "Stopped $($entry.name) (PID $($entry.id))" -ForegroundColor Green
    } else {
        Write-Host "$($entry.name) (PID $($entry.id)) was not running" -ForegroundColor Yellow
    }
}

Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
Write-Host "Done." -ForegroundColor Cyan
